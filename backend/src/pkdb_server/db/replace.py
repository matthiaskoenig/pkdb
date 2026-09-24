"""Bulk insertion of a study-owned graph inside its caller's transaction."""

import hashlib
import json

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.orm import Session

from pkdb.schemas.study import CanonicalStudy, ScientificRecord
from pkdb_server.db.models import interventions as i
from pkdb_server.db.models import measurements as m
from pkdb_server.db.models import studies as s
from pkdb_server.db.models import subjects as g
from pkdb_server.db.models.files import StudyAttachment
from pkdb_server.db.models.users import User
from pkdb_server.db.models.vocabulary import VocabularyNode


def clear_children(session: Session, study_id: int) -> None:
    # Children with array memberships are removed before their referenced values.
    for model in (
        s.Note,
        s.StudyUser,
        StudyAttachment,
        m.Dataset,
        m.ObservationContext,
        m.MeasurementSource,
        i.Intervention,
        g.Subject,
    ):
        session.execute(delete(model).where(model.study_id == study_id))


class ReferenceConflict(ValueError):
    pass


def bulk(session: Session, model, rows: list[dict]) -> dict[str, int]:
    result = {}
    for start in range(0, len(rows), 1000):
        records = session.execute(
            insert(model).returning(model.key, model.id), rows[start : start + 1000]
        )
        result.update((key, identifier) for key, identifier in records)
    return result


def insert_graph(session: Session, root: s.Study, study: CanonicalStudy) -> None:
    sid = root.id
    users = {user.username: user.id for user in session.scalars(select(User))}
    vocab = {
        (node.kind, node.name): node.sid
        for node in session.scalars(select(VocabularyNode))
    }

    def node(kind, name):
        return vocab[(kind, name)] if name else None

    def owned(record):
        return dict(
            study_id=sid,
            key=record.key,
            source=record.source.model_dump(mode="json") if record.source else None,
        )

    def science(record: ScientificRecord):
        row = owned(record)
        row.update(record.statistics.model_dump(exclude={"min", "max"}))
        row.update(
            minimum=record.statistics.min,
            maximum=record.statistics.max,
            measurement_type=node("measurement", record.measurement_type),
            substance=node("substance", record.substance),
            calculation_type=node("calculation_type", record.calculation_type),
            choice=record.choice,
            unit=record.unit,
            origin=record.origin,
            calculated=record.calculated,
        )
        return row

    reference = session.scalar(
        select(s.Reference)
        .where(s.Reference.sid == study.reference.sid)
        .with_for_update()
    )
    if reference is None:
        reference = s.Reference(sid=study.reference.sid, name=study.reference.name)
        session.add(reference)
        session.flush()
    # Root association is unique; no published reference can be silently stolen.
    assigned = session.scalar(
        select(s.Study.id).where(
            s.Study.reference_id == reference.id, s.Study.id != sid
        )
    )
    if assigned is not None:
        raise ReferenceConflict("Reference belongs to another study")
    for name, value in study.reference.model_dump(exclude={"sid", "authors"}).items():
        setattr(reference, name, value)
    session.execute(delete(s.Author).where(s.Author.reference_id == reference.id))
    session.add_all(
        s.Author(reference_id=reference.id, position=index, **author.model_dump())
        for index, author in enumerate(study.reference.authors)
    )
    root.reference_id = reference.id
    session.add_all(
        s.StudyUser(
            study_id=sid,
            user_id=users[curator.user],
            role="curator",
            rating=curator.rating,
        )
        for curator in study.metadata.curators
    )
    session.add_all(
        s.StudyUser(study_id=sid, user_id=users[name], role="collaborator")
        for name in study.metadata.collaborators
    )
    groups = bulk(
        session,
        g.Group,
        [
            dict(**owned(group), name=group.name, count=group.count, image=group.image)
            for group in study.groups
        ],
    )
    group_names = {group.name: groups[group.key] for group in study.groups}
    for group in study.groups:
        if group.parent:
            session.execute(
                update(g.Group)
                .where(g.Group.id == groups[group.key])
                .values(parent_id=group_names[group.parent])
            )
    individuals = bulk(
        session,
        g.Individual,
        [
            dict(
                **owned(individual),
                name=individual.name,
                image=individual.image,
                parent_id=group_names.get(individual.group),
                count=1,
            )
            for individual in study.individuals
        ],
    )
    individual_names = {
        individual.name: individuals[individual.key] for individual in study.individuals
    }
    observation_records = []
    for kind, subjects, identifiers in (
        ("group", study.groups, groups),
        ("individual", study.individuals, individuals),
    ):
        for subject in subjects:
            observation_records.extend(
                ("characteristic", record, identifiers[subject.key])
                for record in subject.characteristica
            )
    intervention_rows = []
    for record in study.interventions:
        row = science(record)
        row.update(
            name=record.name,
            image=record.image,
            time=record.time if isinstance(record.time, (int, float)) else None,
            time_text=record.time if isinstance(record.time, str) else None,
            time_end=record.time_end,
            time_unit=record.time_unit,
            route=node("route", record.route),
            form=node("form", record.form),
            application=node("application", record.application),
        )
        intervention_rows.append(row)
    intervention_ids = bulk(session, i.Intervention, intervention_rows)
    intervention_names = {
        record.name: intervention_ids[record.key] for record in study.interventions
    }
    for record in study.interventions:
        if record.derived_from:
            session.execute(
                update(i.Intervention)
                .where(i.Intervention.id == intervention_ids[record.key])
                .values(derived_from_id=intervention_ids[record.derived_from])
            )
    source_records = {}
    measurement_source_keys = {}
    for record in study.measurements:
        if not record.calculated:
            key = record.series_key or record.derived_from or record.key
            source_records.setdefault(
                key,
                dict(
                    study_id=sid,
                    key=key,
                    source=record.source.model_dump(mode="json")
                    if record.source
                    else None,
                ),
            )
            measurement_source_keys[record.key] = key
    source_ids = bulk(session, m.MeasurementSource, list(source_records.values()))
    observation_records.extend(
        (
            "output",
            record,
            group_names.get(record.group) or individual_names.get(record.individual),
        )
        for record in study.measurements
    )
    contexts = {}
    value_rows = []
    record_contexts = {}
    value_fields = {
        "unit",
        "value",
        "mean",
        "median",
        "minimum",
        "maximum",
        "sd",
        "se",
        "cv",
        "count",
        "origin",
    }
    for kind, record, subject_id in observation_records:
        values = science(record)
        context = {
            key: value
            for key, value in values.items()
            if key not in value_fields | {"key"}
        }
        context.update(
            kind=kind,
            subject_id=subject_id,
            source_id=source_ids.get(measurement_source_keys.get(record.key))
            if kind == "output"
            else None,
            series_key=getattr(record, "series_key", None),
            label=getattr(record, "label", None),
            output_type=getattr(record, "output_type", "output"),
            time=getattr(record, "time", None),
            time_unit=getattr(record, "time_unit", None),
            time_not_reported=getattr(record, "time_not_reported", False),
            time_unit_not_reported=getattr(record, "time_unit_not_reported", False),
            tissue=node("tissue", getattr(record, "tissue", None)),
            method=node("method", getattr(record, "method", None)),
            image=getattr(record, "image", None),
        )
        # Only representations of the same observation with identical context share identity.
        identity = record.derived_from if record.origin == "normalized" else record.key
        key = hashlib.sha256(
            json.dumps(
                [kind, identity, context, getattr(record, "interventions", [])],
                sort_keys=True,
            ).encode()
        ).hexdigest()
        contexts.setdefault(key, dict(context, key=key))
        record_contexts[kind, record.key] = key
        value_rows.append(
            dict(
                study_id=sid,
                key=record.key,
                **{name: values[name] for name in value_fields},
            )
        )
    context_ids = bulk(session, m.ObservationContext, list(contexts.values()))
    for value_row, (kind, record, _) in zip(
        value_rows, observation_records, strict=True
    ):
        value_row["observation_id"] = context_ids[record_contexts[kind, record.key]]
    representation_ids = bulk(session, m.ObservationValue, value_rows)
    courses = bulk(
        session,
        m.Timecourse,
        [
            dict(
                study_id=sid,
                key=course.key,
                measurement_ids=[
                    representation_ids[point.key] for point in course.points
                ],
            )
            for course in study.timecourses
        ],
    )
    # Canonical validation guarantees scientific keys are study-unique.
    associations = {}
    derived_updates = []
    for kind, record, _ in observation_records:
        if record.derived_from:
            derived_updates.append(
                dict(
                    id=representation_ids[record.key],
                    derived_from_id=representation_ids.get(record.derived_from),
                    derived_from_course_id=courses.get(record.derived_from),
                )
            )
        observation_id = context_ids[record_contexts[kind, record.key]]
        for index, name in enumerate(getattr(record, "interventions", [])):
            intervention_id = intervention_names[name]
            associations[observation_id, intervention_id] = dict(
                study_id=sid,
                observation_id=observation_id,
                intervention_id=intervention_id,
                position=index,
            )
    if derived_updates:
        session.execute(update(m.ObservationValue), derived_updates)
    if associations:
        session.execute(insert(m.ObservationIntervention), list(associations.values()))
    measurement_ids = representation_ids
    datasets = bulk(
        session,
        m.Scatter,
        [
            dict(
                **owned(dataset),
                name=dataset.name,
                data_type=dataset.data_type,
                image=dataset.image,
            )
            for dataset in study.scatters
        ],
    )
    subset_records = [
        (dataset, index, subset, f"{dataset.key}:subset:{index}")
        for dataset in study.scatters
        for index, subset in enumerate(dataset.subsets)
    ]
    row_count = sum(len(subset.points) for _, _, subset, _ in subset_records)
    row_ids = (
        iter(
            session.scalars(
                select(func.nextval("dataset_row_id_seq")).select_from(
                    func.generate_series(1, row_count)
                )
            )
        )
        if row_count
        else iter(())
    )
    bulk(
        session,
        m.Subset,
        [
            dict(
                study_id=sid,
                key=key,
                parent_id=datasets[dataset.key],
                name=subset.name,
                position=index,
                shared_fields=subset.shared,
                dimension_labels=[
                    dimension.model_dump(mode="json") for dimension in subset.dimensions
                ],
                measurement_ids=[
                    measurement_ids[item] for point in subset.points for item in point
                ],
                point_ids=[next(row_ids) for _ in subset.points],
            )
            for dataset, index, subset, key in subset_records
        ],
    )
    notes = []
    records = [
        ("study", study),
        ("metadata", study.metadata),
        *[("section:" + key, value) for key, value in study.section_notes.items()],
    ]
    records.extend(
        (record.key, record)
        for record in [
            *study.groups,
            *study.individuals,
            *study.interventions,
            *study.measurements,
        ]
    )
    records.extend(
        (record.key, record)
        for subject in [*study.groups, *study.individuals]
        for record in subject.characteristica
    )
    records.extend((dataset.key, dataset) for dataset in study.scatters)
    records.extend((key, subset) for _, _, subset, key in subset_records)
    for key, record in records:
        notes.extend(
            dict(
                study_id=sid,
                record_key=key,
                kind="description",
                position=index,
                text=note.text,
            )
            for index, note in enumerate(record.descriptions)
        )
        notes.extend(
            dict(
                study_id=sid,
                record_key=key,
                kind="comment",
                position=index,
                text=note.text,
                user_id=users[note.user] if note.user is not None else None,
            )
            for index, note in enumerate(record.comments)
        )
    if notes:
        session.execute(insert(s.Note), notes)
