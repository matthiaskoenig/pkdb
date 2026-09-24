"""Flat analysis rows, paginated after expanding scientific associations."""

from sqlalchemy import select
from sqlalchemy.orm import aliased

from pkdb_server.db.dataset_arrays import dataset_cells, dataset_type
from pkdb_server.db.models.interventions import Intervention
from pkdb_server.db.models.measurements import (
    Measurement,
    MeasurementIntervention,
    Scatter,
    Subset,
)
from pkdb_server.db.models.studies import Study
from pkdb_server.db.models.subjects import Characteristic, Group, Individual
from pkdb_server.db.queries import (
    comparison,
    conditions,
    fields_for,
    node_name,
    visibility,
)
from pkdb_server.db.search import search_condition
from pkdb_server.db.serialize import (
    VocabularyResponses,
    intervention_responses,
    output_responses,
    subset_responses,
)
from pkdb_server.db.study_responses import study_responses
from pkdb_server.db.subject_filters import effective_characteristics

ENTITIES = {
    "studies": "studies",
    "groups": "groups",
    "individuals": "individuals",
    "interventions": "interventions",
    "outputs": "outputs",
    "timecourses": "subsets",
    "data": "subsets",
}
VALUES = ("value", "mean", "median", "min", "max", "sd", "se", "cv", "unit")
NODES = ("measurement_type", "calculation_type", "choice", "substance")


def statement(entity, query, principal):
    if entity not in ENTITIES or query.entity != ENTITIES[entity]:
        raise ValueError("Unsupported analysis entity")
    fields = dict(fields_for(query.entity))
    extra = []
    if entity == "studies":
        stmt = select(Study)
        keys = [Study.id]
        fields["id"] = Study.id
    elif entity == "interventions":
        stmt = select(Intervention).join(Study, Study.id == Intervention.study_id)
        keys = [Intervention.id]
        fields.update(
            intervention_pk=Intervention.id, raw_pk=Intervention.derived_from_id
        )
    elif entity == "outputs":
        stmt = (
            select(Measurement, MeasurementIntervention.intervention_id)
            .join(
                MeasurementIntervention,
                MeasurementIntervention.measurement_id == Measurement.id,
            )
            .join(Study, Study.id == Measurement.study_id)
        )
        keys = [Measurement.id, MeasurementIntervention.position]
        fields.update(
            output_pk=Measurement.id,
            intervention_pk=MeasurementIntervention.intervention_id,
        )
    elif entity in {"groups", "individuals"}:
        model = Group if entity == "groups" else Individual
        effective = effective_characteristics(entity)
        stmt = (
            select(model, Characteristic)
            .select_from(model)
            .join(effective, effective.c.subject_id == model.id)
            .join(Characteristic, Characteristic.id == effective.c.id)
            .join(Study, Study.id == model.study_id)
        )
        keys = [model.id, Characteristic.id]
        fields.update(
            {
                name: node_name(getattr(Characteristic, name))
                for name in ("measurement_type", "calculation_type", "substance")
            }
        )
        fields.update(
            {
                name: getattr(Characteristic, name)
                for name in (
                    "value",
                    "mean",
                    "median",
                    "minimum",
                    "maximum",
                    "sd",
                    "se",
                    "cv",
                    "unit",
                    "choice",
                    "count",
                )
            }
        )
        fields.update(
            characteristica_pk=Characteristic.id,
            measurement_type_sid=Characteristic.measurement_type,
            substance_sid=Characteristic.substance,
        )
        if entity == "groups":
            fields.update(
                group_pk=Group.id,
                group_name=Group.name,
                group_count=Group.count,
                group_parent_pk=Group.parent_id,
            )
        else:
            fields.update(
                individual_pk=Individual.id,
                individual_name=Individual.name,
                individual_group_pk=Individual.group_id,
            )
    elif entity == "timecourses":
        stmt = select(Subset).join(Study, Study.id == Subset.study_id)
        extra.append(dataset_type() == "timecourse")
        keys = [Subset.id]
        fields.update(subset_pk=Subset.id, subset_name=Subset.name)
    else:
        cells = dataset_cells()
        dataset = aliased(Scatter)
        stmt = (
            select(
                Subset,
                dataset,
                cells.c.point_id,
                cells.c.measurement_id,
                cells.c.dimension,
            )
            .join(cells, cells.c.subset_id == Subset.id)
            .join(dataset, dataset.id == Subset.scatter_id)
            .join(Study, Study.id == Subset.study_id)
        )
        keys = [Subset.id, cells.c.position]
        fields.update(
            data_pk=dataset.id,
            data_name=dataset.name,
            subset_pk=Subset.id,
            subset_name=Subset.name,
            data_point_pk=cells.c.point_id,
            output_pk=cells.c.measurement_id,
        )
    related = []
    for predicate in query.predicates:
        if predicate.field in fields:
            extra.append(comparison(fields[predicate.field], predicate))
        elif entity == "studies":
            related.append(predicate)
        else:
            raise ValueError("Unknown analysis filter")
    if related:
        extra.append(
            conditions(query.model_copy(update={"predicates": related, "search": None}))
        )
    if query.search:
        for term in query.search.split():
            extra.append(search_condition(query.entity, term))
    name = query.sort.removeprefix("-")
    fields.setdefault("sid", Study.sid)
    if name not in fields:
        raise ValueError("Unknown analysis ordering")
    column = fields[name]
    order = (
        column.desc().nulls_last()
        if query.sort.startswith("-")
        else column.asc().nulls_last()
    )
    return stmt.where(visibility(principal), *extra), [order, *keys]


def science(record, *, labels, names=False, fields=NODES):
    result = {}
    for field in fields:
        node = record.get(field)
        result[field] = node["name" if names else "sid"] if node else None
        if labels:
            result[field + "_label"] = node["label"] if node else None
    result.update({name: record[name] for name in VALUES})
    return result


def serialize(session, entity, rows, principal):
    from pkdb.schemas.analysis import ANALYSIS_MODELS

    return [
        ANALYSIS_MODELS[entity].model_validate(row).model_dump()
        for row in _serialize(session, entity, rows, principal)
    ]


def _serialize(session, entity, rows, principal):
    if not rows:
        return []
    models = [row[0] for row in rows]
    if entity == "studies":
        result = []
        for row in study_responses(session, models, principal):
            result.append(
                {
                    **{
                        key: row[key]
                        for key in ("sid", "name", "licence", "access", "date")
                    },
                    "creator": row["creator"]["username"] if row["creator"] else None,
                    "curators": [user["username"] for user in row["curators"]],
                    "substances": [node["label"] for node in row["substances"]],
                    "reference_pmid": row["reference"]["pmid"]
                    if row["reference"]
                    else None,
                    "reference_title": row["reference"]["title"]
                    if row["reference"]
                    else None,
                    "reference_date": row["reference_date"],
                }
            )
        return result
    studies = {
        row.id: row
        for row in session.scalars(
            select(Study).where(Study.id.in_({r.study_id for r in models}))
        )
    }

    def study(model):
        root = studies[model.study_id]
        return {"study_sid": root.sid, "study_name": root.name}

    if entity == "outputs":
        public = {
            row["pk"]: row
            for row in output_responses(
                session, list({row.id: row for row in models}.values())
            )
        }
        result = []
        for model, intervention_id in rows:
            row = public[model.id]
            result.append(
                {
                    **study(model),
                    "output_pk": model.id,
                    "intervention_pk": intervention_id,
                    "group_pk": model.group_id,
                    "individual_pk": model.individual_id,
                    "normed": row["normed"],
                    "calculated": row["calculated"],
                    **science(row, labels=True, fields=("tissue", "method")),
                    "label": row["label"],
                    "output_type": row["output_type"],
                    "time": row["time"],
                    "time_unit": row["time_unit"],
                    **science(row, labels=True),
                }
            )
        return result
    if entity == "interventions":
        result = []
        for model, row in zip(
            models, intervention_responses(session, models), strict=True
        ):
            result.append(
                {
                    **study(model),
                    "intervention_pk": model.id,
                    "raw_pk": model.derived_from_id,
                    "normed": row["normed"],
                    "name": row["name"],
                    **science(
                        row, labels=True, fields=("route", "form", "application")
                    ),
                    "time": row["time"],
                    "time_end": row["time_end"],
                    "time_unit": row["time_unit"],
                    **science(row, labels=True),
                }
            )
        return result
    if entity in {"groups", "individuals"}:
        vocab = VocabularyResponses(session, [row[1] for row in rows])
        result = []
        for model, characteristic in rows:
            prefix = (
                {
                    "group_pk": model.id,
                    "group_name": model.name,
                    "group_count": model.count,
                    "group_parent_pk": model.parent_id,
                }
                if entity == "groups"
                else {
                    "individual_pk": model.id,
                    "individual_name": model.name,
                    "individual_group_pk": model.group_id,
                }
            )
            record = vocab.science(characteristic)
            result.append(
                {
                    **study(model),
                    **prefix,
                    "characteristica_pk": characteristic.id,
                    "count": characteristic.count,
                    **science(record, labels=False, names=True),
                }
            )
        return result
    if entity == "timecourses":
        result = []
        for model, row in zip(models, subset_responses(session, models), strict=True):
            points = [point[0] for point in row["array"]]
            first = points[0]
            data = {
                **study(model),
                "output_pk": [point["pk"] for point in points],
                "subset_pk": model.id,
                "subset_name": model.name,
                "intervention_pk": [item["pk"] for item in first["interventions"]],
                "group_pk": first["group"].get("pk"),
                "individual_pk": first["individual"].get("pk"),
                "normed": first["normed"],
                **science(
                    first,
                    labels=True,
                    fields=(
                        "tissue",
                        "method",
                        "measurement_type",
                        "choice",
                        "substance",
                    ),
                ),
                "label": first["label"],
                "time_unit": first["time_unit"],
            }
            for field in (*VALUES[:-1], "time"):
                values = [point[field] for point in points]
                data[field] = (
                    values if any(value is not None for value in values) else None
                )
            result.append(data)
        return result
    return [
        {
            **study(subset),
            "data_pk": dataset.id,
            "data_name": dataset.name,
            "data_type": dataset.data_type,
            "subset_pk": subset.id,
            "subset_name": subset.name,
            "data_point_pk": point_id,
            "output_pk": measurement_id,
            "dimension": dimension,
        }
        for subset, dataset, point_id, measurement_id, dimension in rows
    ]
