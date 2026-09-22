"""Assemble typed graphs inside one repeatable-read snapshot."""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from pkdb.db.models import interventions as i
from pkdb.db.models import measurements as m
from pkdb.db.models import studies as s
from pkdb.db.models import subjects as g
from pkdb.db.models.files import StoredFile, StudyAttachment
from pkdb.db.models.users import User
from pkdb.db.models.vocabulary import VocabularyNode
from pkdb.files.store import study_access
from pkdb.schemas.security import Principal
from pkdb.schemas.study import CanonicalStudy
from pkdb.services.authorization import authorize


def read_study(
    sid: str, principal: Principal, session_factory: sessionmaker[Session]
) -> CanonicalStudy:
    with session_factory() as session:
        session.connection(execution_options={"isolation_level": "REPEATABLE READ"})
        root = session.scalar(select(s.Study).where(s.Study.sid == sid))
        if root is None:
            raise LookupError("Study not found")
        authorize(principal, "read", study_access(root, session))
        return assemble_study(root, session)


def assemble_study(root: s.Study, session: Session) -> CanonicalStudy:
    def rows(model):
        return list(
            session.scalars(
                select(model).where(model.study_id == root.id).order_by(model.id)
            )
        )

    if root.creator_id is None:
        raise RuntimeError("Published study has no creator")
    users = {user.id: user.username for user in session.scalars(select(User))}
    vocab = {node.sid: node.name for node in session.scalars(select(VocabularyNode))}
    notes = defaultdict(lambda: {"descriptions": [], "comments": []})
    for note in session.scalars(
        select(s.Note).where(s.Note.study_id == root.id).order_by(s.Note.position)
    ):
        if note.kind == "description":
            notes[note.record_key]["descriptions"].append({"text": note.text})
        else:
            notes[note.record_key]["comments"].append(
                {"text": note.text, "user": users.get(note.user_id)}
            )
    groups = rows(g.Group)
    individuals = rows(g.Individual)
    interventions = rows(i.Intervention)
    measurements = rows(m.Measurement)
    characteristics = rows(g.Characteristic)
    courses = rows(m.Timecourse)
    group_names = {row.id: row.name for row in groups}
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
                    for name in ("value", "mean", "median", "sd", "se", "cv", "count")
                },
                "min": row.minimum,
                "max": row.maximum,
            },
        )

    group_characteristics = defaultdict(list)
    individual_characteristics = defaultdict(list)
    for row in characteristics:
        target = (
            group_characteristics[row.group_id]
            if row.group_id
            else individual_characteristics[row.individual_id]
        )
        target.append(science(row, characteristic_keys))
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
            group=group_names.get(row.group_id),
            individual=individual_names.get(row.individual_id),
            interventions=measurement_interventions[row.id],
            tissue=vocab.get(row.tissue),
            method=vocab.get(row.method),
            **{
                name: getattr(row, name)
                for name in (
                    "series_key",
                    "label",
                    "output_type",
                    "time",
                    "time_unit",
                    "time_not_reported",
                    "time_unit_not_reported",
                    "image",
                )
            },
        )
        outputs.append(record)
    by_key = {output["key"]: output for output in outputs}
    course_points = defaultdict(list)
    for row in session.scalars(
        select(m.TimecoursePoint)
        .where(m.TimecoursePoint.study_id == root.id)
        .order_by(m.TimecoursePoint.position)
    ):
        course_points[row.timecourse_id].append(
            by_key[measurement_keys[row.measurement_id]]
        )
    datasets = rows(m.Scatter)
    subset_rows = rows(m.Subset)
    dimensions = defaultdict(list)
    for row in session.scalars(
        select(m.SubsetDimension)
        .where(m.SubsetDimension.study_id == root.id)
        .order_by(m.SubsetDimension.position)
    ):
        dimensions[row.subset_id].append(measurement_keys[row.measurement_id])
    dataset_subsets = defaultdict(list)
    for row in sorted(subset_rows, key=lambda item: item.position):
        width = len(row.dimension_labels)
        values = dimensions[row.id]
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
    members = list(
        session.scalars(
            select(s.StudyUser)
            .where(s.StudyUser.study_id == root.id)
            .order_by(s.StudyUser.user_id)
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
                date=root.date,
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
                        "pmid",
                        "doi",
                        "title",
                        "abstract",
                        "journal",
                        "date",
                    )
                },
                authors=[
                    dict(first_name=row.first_name, last_name=row.last_name)
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
                    time=row.time_text if row.time_text is not None else row.time,
                    image=row.image,
                    time_end=row.time_end,
                    time_unit=row.time_unit,
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
