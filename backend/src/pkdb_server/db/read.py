"""Assemble typed graphs inside one repeatable-read snapshot."""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from pkdb.schemas.security import Principal
from pkdb.schemas.study import CanonicalStudy
from pkdb_server.db.models import interventions as i
from pkdb_server.db.models import measurements as m
from pkdb_server.db.models import studies as s
from pkdb_server.db.models import subjects as g
from pkdb_server.db.models.files import StoredFile, StudyAttachment
from pkdb_server.db.models.users import User
from pkdb_server.db.models.vocabulary import VocabularyNode
from pkdb_server.files.store import study_access
from pkdb_server.services.authorization import AuthorizationDenied, authorize


def released_study(
    session: Session, identifier: str, principal: Principal
) -> s.Study | None:
    """The study released as `identifier` and stored under another sid.

    A PKDB identifier is also the study format 1 sid of a released study that
    is now stored as `<substance>/<name>`. Only readers of the study learn
    which study it is; for anyone else there is no such study.
    """
    root = session.scalar(
        select(s.Study).where(s.Study.pkdb_id == identifier, s.Study.sid != identifier)
    )
    if root is None:
        return None
    try:
        authorize(principal, "read", study_access(root, session))
    except AuthorizationDenied:
        return None
    return root


def read_study(
    sid: str,
    principal: Principal,
    session_factory: sessionmaker[Session],
    *,
    by_pkdb_id: bool = False,
) -> CanonicalStudy:
    """The study stored under `sid`; with `by_pkdb_id`, else the study released as `sid`."""
    with session_factory() as session:
        session.connection(execution_options={"isolation_level": "REPEATABLE READ"})
        root = session.scalar(select(s.Study).where(s.Study.sid == sid))
        if root is None and by_pkdb_id:
            root = released_study(session, sid, principal)
        if root is None:
            raise LookupError("Study not found")
        authorize(principal, "read", study_access(root, session))
        return assemble_study(root, session)


def moved_study(
    identifier: str, principal: Principal, session_factory: sessionmaker[Session]
) -> str | None:
    """The sid of the study released as `identifier` under another sid, if readable."""
    with session_factory() as session:
        root = released_study(session, identifier, principal)
        return root.sid if root is not None else None


def intervention_time(row: i.Intervention) -> float | list[float] | None:
    """Canonical intervention time: a list of times or one time."""
    return row.time_list if row.time_list is not None else row.time


def assemble_study(root: s.Study, session: Session) -> CanonicalStudy:
    def rows(model):
        return list(
            session.scalars(
                select(model).where(model.study_id == root.id).order_by(model.id)
            )
        )

    if root.creator_id is None:
        raise RuntimeError("Published study has no creator")
    members = list(
        session.scalars(
            select(s.StudyUser)
            .where(s.StudyUser.study_id == root.id)
            .order_by(s.StudyUser.user_id)
        )
    )
    note_rows = list(
        session.scalars(
            select(s.Note).where(s.Note.study_id == root.id).order_by(s.Note.position)
        )
    )
    user_ids = (
        {root.creator_id}
        | {row.user_id for row in members}
        | {row.user_id for row in note_rows}
    )
    users = {
        user.id: user.username
        for user in session.scalars(select(User).where(User.id.in_(user_ids)))
    }
    notes = defaultdict(lambda: {"descriptions": [], "comments": []})
    for note in note_rows:
        if note.kind == "description":
            notes[note.record_key]["descriptions"].append({"text": note.text})
        else:
            notes[note.record_key]["comments"].append(
                {"text": note.text, "user": users.get(note.user_id)}
            )
    subjects = rows(g.Subject)
    groups = [row for row in subjects if row.kind == "group"]
    individuals = [row for row in subjects if row.kind == "individual"]
    interventions = rows(i.Intervention)
    observations = rows(m.Observation)
    measurements = [row for row in observations if row.kind == "output"]
    characteristics = [row for row in observations if row.kind == "characteristic"]
    dataset_rows = rows(m.Dataset)
    courses = [row for row in dataset_rows if row.kind == "course"]
    node_ids = {
        getattr(row, field, None)
        for row in [*observations, *interventions]
        for field in (
            "measurement_type",
            "substance",
            "calculation_type",
            "tissue",
            "method",
            "route",
            "form",
            "application",
        )
    }
    vocab = {
        node.sid: node.name
        for node in session.scalars(
            select(VocabularyNode).where(VocabularyNode.sid.in_(node_ids))
        )
    }
    group_names = {row.id: row.name for row in groups}
    subject_names = {row.id: row.name for row in subjects}
    individual_names = {row.id: row.name for row in individuals}
    intervention_names = {row.id: row.name for row in interventions}
    characteristic_keys = {row.id: row.key for row in characteristics}
    intervention_keys = {row.id: row.key for row in interventions}
    measurement_keys = {row.id: row.key for row in measurements}
    course_keys = {row.id: row.key for row in courses}

    def science(row, derived_keys):
        return dict(
            **notes[row.key],
            key=row.key,
            source=row.source,
            measurement_type=vocab[row.measurement_type],
            substance=vocab.get(row.substance),
            calculation_type=vocab.get(row.calculation_type),
            choice=row.choice,
            unit=row.unit,
            origin=row.origin,
            calculated=row.calculated,
            derived_from=derived_keys.get(row.derived_from_id),
            statistics={
                **{
                    name: getattr(row, name)
                    for name in (
                        "mean",
                        "median",
                        "sd",
                        "se",
                        "cv",
                        "gmean",
                        "gsd",
                        "gcv",
                        "count",
                        "error_bar",
                        "error_type",
                    )
                },
                "min": row.minimum,
                "max": row.maximum,
            },
        )

    def context(row):
        """Where and when an observation was made, shared by characteristics and outputs."""
        return dict(
            tissue=vocab.get(row.tissue),
            method=vocab.get(row.method),
            time=row.time,
            time_unit=row.time_unit,
            time_not_reported=row.time_not_reported,
            time_unit_not_reported=row.time_unit_not_reported,
            image=row.image,
        )

    group_characteristics = defaultdict(list)
    individual_characteristics = defaultdict(list)
    for row in characteristics:
        target = (
            group_characteristics[row.group_id]
            if row.group_id
            else individual_characteristics[row.individual_id]
        )
        target.append(science(row, characteristic_keys) | context(row))
    measurement_interventions = defaultdict(list)
    for row in session.scalars(
        select(m.MeasurementIntervention)
        .where(m.MeasurementIntervention.study_id == root.id)
        .order_by(m.MeasurementIntervention.position)
    ):
        measurement_interventions[row.measurement_id].append(
            intervention_names[row.intervention_id]
        )
    outputs = []
    for row in measurements:
        record = science(row, measurement_keys)
        if row.derived_from_course_id:
            record["derived_from"] = course_keys[row.derived_from_course_id]
        record.update(
            context(row),
            group=group_names.get(row.group_id),
            individual=individual_names.get(row.individual_id),
            interventions=measurement_interventions[row.id],
            series_key=row.series_key,
            label=row.label,
            output_type=row.output_type,
        )
        outputs.append(record)
    by_key = {output["key"]: output for output in outputs}
    course_points = {
        course.id: [
            by_key[measurement_keys[identifier]]
            for identifier in course.measurement_ids
        ]
        for course in courses
    }
    datasets = [row for row in dataset_rows if row.kind == "dataset"]
    subset_rows = [row for row in dataset_rows if row.kind == "series"]
    dataset_subsets = defaultdict(list)
    for row in sorted(subset_rows, key=lambda item: item.position):
        width = len(row.dimension_labels)
        values = [measurement_keys[identifier] for identifier in row.measurement_ids]
        points = (
            [values[index : index + width] for index in range(0, len(values), width)]
            if width
            else []
        )
        dataset_subsets[row.scatter_id].append(
            dict(
                **notes[row.key],
                name=row.name,
                dimensions=row.dimension_labels,
                shared=row.shared_fields,
                points=points,
            )
        )
    reference = session.get(s.Reference, root.reference_id)
    if reference is None:
        raise RuntimeError("Published study has no reference")
    authors = list(
        session.scalars(
            select(s.Author)
            .where(s.Author.reference_id == reference.id)
            .order_by(s.Author.position)
        )
    )
    attachments = session.execute(
        select(StudyAttachment, StoredFile)
        .join(StoredFile)
        .where(StudyAttachment.study_id == root.id)
        .order_by(StudyAttachment.name.collate("C"))
    )
    return CanonicalStudy.model_validate(
        dict(
            **notes["study"],
            sid=root.sid,
            source_digest=root.source_digest,
            metadata=dict(
                **notes["metadata"],
                name=root.name,
                provenance=root.acquisition,
                date=root.date,
                issue=root.issue,
                release=dict(pkdb_id=root.pkdb_id, date=root.release_date)
                if root.pkdb_id is not None
                else None,
                review=dict(root.review, status=root.review_status)
                if root.review is not None
                else None,
                creator=users[root.creator_id],
                access=root.access,
                licence=root.licence,
                curators=[
                    dict(user=users[row.user_id], rating=row.rating)
                    for row in members
                    if row.role == "curator"
                ],
                collaborators=[
                    users[row.user_id] for row in members if row.role == "collaborator"
                ],
            ),
            reference=dict(
                **{
                    field: getattr(reference, field)
                    for field in (
                        "sid",
                        "name",
                        "publication_date",
                        "provenance",
                        "pmid",
                        "doi",
                        "url",
                        "title",
                        "abstract",
                        "journal",
                        "date",
                    )
                },
                authors=[
                    dict(
                        first_name=row.first_name,
                        last_name=row.last_name,
                        organization=row.organization,
                    )
                    for row in authors
                ],
            ),
            groups=[
                dict(
                    **notes[row.key],
                    key=row.key,
                    name=row.name,
                    count=row.count,
                    image=row.image,
                    parent=group_names.get(row.parent_id),
                    source=row.source,
                    characteristica=group_characteristics[row.id],
                )
                for row in groups
            ],
            individuals=[
                dict(
                    **notes[row.key],
                    key=row.key,
                    name=row.name,
                    group=group_names.get(row.group_id),
                    image=row.image,
                    source=row.source,
                    characteristica=individual_characteristics[row.id],
                )
                for row in individuals
            ],
            interventions=[
                dict(
                    **science(row, intervention_keys),
                    name=row.name,
                    time=intervention_time(row),
                    image=row.image,
                    time_end=row.time_end,
                    interval=row.interval,
                    doses=row.doses,
                    time_unit=row.time_unit,
                    time_not_reported=row.time_not_reported,
                    time_unit_not_reported=row.time_unit_not_reported,
                    tissue=vocab.get(row.tissue),
                    method=vocab.get(row.method),
                    subject=subject_names.get(row.subject_id),
                    route=vocab.get(row.route),
                    form=vocab.get(row.form),
                    application=vocab.get(row.application),
                )
                for row in interventions
            ],
            measurements=outputs,
            scatters=[
                dict(
                    **notes[row.key],
                    key=row.key,
                    name=row.name,
                    data_type=row.data_type,
                    image=row.image,
                    source=row.source,
                    subsets=dataset_subsets[row.id],
                )
                for row in datasets
            ],
            timecourses=[
                dict(key=row.key, points=course_points[row.id]) for row in courses
            ],
            attachments=[
                dict(name=association.name, sha256=file.digest, size=file.size)
                for association, file in attachments
            ],
            section_notes={
                key: notes["section:" + key]
                for key in root.source_manifest.get("sections", [])
            },
        )
    )


def publication_state(sid: str, principal: Principal, session_factory):
    from pkdb.domain.validation import PROCESSING_VERSION
    from pkdb.schemas.replacement import PublicationState
    from pkdb_server.db.models.vocabulary import VocabularyVersion

    with session_factory() as session:
        session.connection(execution_options={"isolation_level": "REPEATABLE READ"})
        root = session.scalar(select(s.Study).where(s.Study.sid == sid))
        if root is None:
            raise LookupError("Study not found")
        authorize(principal, "read", study_access(root, session))
        vocabulary = session.get(VocabularyVersion, 1)
        if vocabulary is None:
            raise RuntimeError("Vocabulary unavailable")
        return PublicationState(
            sid=root.sid,
            digest=root.source_digest,
            processing_version=root.processing_version,
            vocabulary_version=root.vocabulary_version,
            current_processing_version=PROCESSING_VERSION,
            current_vocabulary_version=vocabulary.version,
        )
