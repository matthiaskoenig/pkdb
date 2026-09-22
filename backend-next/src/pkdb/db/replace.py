"""Bulk insertion of a study-owned graph inside its caller's transaction."""

from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import Session

from pkdb.db.models import interventions as i
from pkdb.db.models import measurements as m
from pkdb.db.models import studies as s
from pkdb.db.models import subjects as g
from pkdb.db.models.files import StudyAttachment
from pkdb.db.models.users import User
from pkdb.db.models.vocabulary import VocabularyNode
from pkdb.schemas.study import CanonicalStudy, ScientificRecord


def clear_children(session: Session, study_id: int) -> None:
    for model in (
        s.Note,
        s.StudyUser,
        StudyAttachment,
        m.Scatter,
        m.Measurement,
        m.MeasurementSource,
        m.Timecourse,
        g.Characteristic,
        i.Intervention,
        g.Individual,
        g.Group,
    ):
        session.execute(delete(model).where(model.study_id == study_id))


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
        raise ValueError("Reference belongs to another study")
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
            dict(**owned(group), name=group.name, count=group.count)
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
                group_id=group_names.get(individual.group),
            )
            for individual in study.individuals
        ],
    )
    individual_names = {
        individual.name: individuals[individual.key] for individual in study.individuals
    }
    characteristics = []
    for subject in [*study.groups, *study.individuals]:
        for record in subject.characteristica:
            row = science(record)
            row.update(
                group_id=groups.get(subject.key) if subject in study.groups else None,
                individual_id=individuals.get(subject.key)
                if subject in study.individuals
                else None,
            )
            characteristics.append((record, row))
    characteristics_map = bulk(
        session, g.Characteristic, [row for _, row in characteristics]
    )
    for record, _ in characteristics:
        if record.derived_from:
            session.execute(
                update(g.Characteristic)
                .where(g.Characteristic.id == characteristics_map[record.key])
                .values(derived_from_id=characteristics_map[record.derived_from])
            )
    intervention_rows = []
    for record in study.interventions:
        row = science(record)
        row.update(
            name=record.name,
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
    courses = bulk(
        session,
        m.Timecourse,
        [dict(study_id=sid, key=course.key) for course in study.timecourses],
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
    measurements = []
    for record in study.measurements:
        row = science(record)
        row.update(
            source_id=source_ids.get(measurement_source_keys.get(record.key)),
            group_id=group_names.get(record.group),
            individual_id=individual_names.get(record.individual),
            series_key=record.series_key,
            label=record.label,
            output_type=record.output_type,
            time=record.time,
            time_unit=record.time_unit,
            time_not_reported=record.time_not_reported,
            time_unit_not_reported=record.time_unit_not_reported,
            tissue=node("tissue", record.tissue),
            method=node("method", record.method),
            image=record.image,
        )
        measurements.append(row)
    measurement_ids = bulk(session, m.Measurement, measurements)
    derived_updates = []
    associations = []
    for record in study.measurements:
        if record.derived_from:
            derived_updates.append(
                dict(
                    id=measurement_ids[record.key],
                    derived_from_id=measurement_ids.get(record.derived_from),
                    derived_from_course_id=courses.get(record.derived_from),
                )
            )
        associations.extend(
            dict(
                study_id=sid,
                measurement_id=measurement_ids[record.key],
                intervention_id=intervention_names[name],
                position=index,
            )
            for index, name in enumerate(record.interventions)
        )
    if derived_updates:
        session.execute(update(m.Measurement), derived_updates)
    if associations:
        session.execute(insert(m.MeasurementIntervention), associations)
    points = [
        dict(
            study_id=sid,
            timecourse_id=courses[course.key],
            position=index,
            measurement_id=measurement_ids[point.key],
        )
        for course in study.timecourses
        for index, point in enumerate(course.points)
    ]
    if points:
        session.execute(insert(m.TimecoursePoint), points)
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
    subsets = bulk(
        session,
        m.Subset,
        [
            dict(
                study_id=sid,
                key=key,
                scatter_id=datasets[dataset.key],
                name=subset.name,
                position=index,
                shared_fields=subset.shared,
                dimension_labels=[
                    dimension.model_dump(mode="json") for dimension in subset.dimensions
                ],
            )
            for dataset, index, subset, key in subset_records
        ],
    )
    dimensions = [
        dict(
            study_id=sid,
            subset_id=subsets[key],
            position=point_index * len(subset.dimensions) + dimension,
            dimension=subset.dimensions[dimension].dimension,
            measurement_id=measurement_ids[measurement_key],
        )
        for _, _, subset, key in subset_records
        for point_index, point in enumerate(subset.points)
        for dimension, measurement_key in enumerate(point)
    ]
    if dimensions:
        session.execute(insert(m.SubsetDimension), dimensions)
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
