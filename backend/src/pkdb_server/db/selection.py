"""Relational legacy filter selections, evaluated with current visibility."""

from sqlalchemy import func, or_, select

from pkdb.schemas.queries import QuerySpec
from pkdb_server.db.dataset_arrays import dataset_type
from pkdb_server.db.models.interventions import Intervention
from pkdb_server.db.models.measurements import (
    Measurement,
    MeasurementIntervention,
    Subset,
)
from pkdb_server.db.models.studies import Study
from pkdb_server.db.models.subjects import Group, Individual
from pkdb_server.db.queries import conditions, visibility

MODELS = {
    "studies": Study,
    "groups": Group,
    "individuals": Individual,
    "interventions": Intervention,
    "outputs": Measurement,
    "subsets": Subset,
}


def selection(spec, principal):
    def matches(entity):
        model = MODELS[entity]
        stmt = select(model.id)
        if model is not Study:
            stmt = stmt.join(Study, Study.id == model.study_id)
        stmt = stmt.where(
            visibility(principal),
            conditions(spec.queries.get(entity, QuerySpec(entity=entity))),
        )
        if model is Measurement or model is Intervention:
            stmt = stmt.where(model.origin == "normalized")
        return stmt

    studies = matches("studies")
    output_constraints = []
    study_constraints = []
    if "groups" in spec.queries or "individuals" in spec.queries:
        groups, individuals = matches("groups"), matches("individuals")
        output_constraints.append(
            or_(
                Measurement.group_id.in_(groups),
                Measurement.individual_id.in_(individuals),
            )
        )
        study_constraints.append(
            or_(
                Study.id.in_(select(Group.study_id).where(Group.id.in_(groups))),
                Study.id.in_(
                    select(Individual.study_id).where(Individual.id.in_(individuals))
                ),
            )
        )
    if "interventions" in spec.queries:
        interventions = matches("interventions")
        output_constraints.append(
            Measurement.id.in_(
                select(MeasurementIntervention.measurement_id).where(
                    MeasurementIntervention.intervention_id.in_(interventions)
                )
            )
        )
        study_constraints.append(
            Study.id.in_(
                select(Intervention.study_id).where(Intervention.id.in_(interventions))
            )
        )
    if "outputs" in spec.queries:
        outputs = matches("outputs")
        output_constraints.append(Measurement.id.in_(outputs))
        study_constraints.append(
            Study.id.in_(
                select(Measurement.study_id).where(Measurement.id.in_(outputs))
            )
        )
    if "subsets" in spec.queries:
        subsets = matches("subsets")
        output_constraints.append(
            Measurement.id.in_(
                select(func.unnest(Subset.measurement_ids)).where(
                    Subset.id.in_(subsets)
                )
            )
        )
        study_constraints.append(
            Study.id.in_(select(Subset.study_id).where(Subset.id.in_(subsets)))
        )
    if not spec.concise:
        studies = studies.where(*study_constraints)
    outputs = select(
        Measurement.id.label("id"),
        Measurement.study_id.label("study_id"),
        Measurement.group_id.label("group_id"),
        Measurement.individual_id.label("individual_id"),
    ).where(Measurement.study_id.in_(studies), Measurement.origin == "normalized")
    if spec.concise:
        outputs = outputs.where(*output_constraints)
    outputs = outputs.cte()
    result = {"outputs": select(outputs.c.id)}
    if spec.concise:
        result.update(
            studies=select(outputs.c.study_id).distinct(),
            groups=select(outputs.c.group_id)
            .where(outputs.c.group_id.is_not(None))
            .distinct(),
            individuals=select(outputs.c.individual_id)
            .where(outputs.c.individual_id.is_not(None))
            .distinct(),
            interventions=select(MeasurementIntervention.intervention_id)
            .where(MeasurementIntervention.measurement_id.in_(result["outputs"]))
            .distinct(),
        )
        subsets = select(Subset.id).where(
            select(Measurement.id)
            .where(
                Measurement.id == Subset.measurement_ids.any_(),
                Measurement.id.in_(result["outputs"]),
            )
            .exists()
        )
    else:
        result["studies"] = studies
        for entity, model in (
            ("groups", Group),
            ("individuals", Individual),
            ("interventions", Intervention),
        ):
            stmt = select(model.id).where(model.study_id.in_(studies))
            if entity == "interventions":
                stmt = stmt.where(Intervention.origin == "normalized")
            result[entity] = stmt
        subsets = select(Subset.id).where(Subset.study_id.in_(studies))
    result["subsets"] = subsets
    for entity, kind in (("timecourses", "timecourse"), ("scatters", "scatter")):
        result[entity] = subsets.where(dataset_type() == kind)
    return result


def constraint(entity, spec, principal):
    selected = selection(spec, principal)
    if entity == "data":
        return Subset.id.in_(selected["subsets"])
    if entity in {"timecourses", "scatters"}:
        return Subset.id.in_(selected[entity])
    if entity == "references":
        return Study.id.in_(selected["studies"])
    if entity not in selected:
        raise ValueError("Entity does not support saved selections")
    return MODELS[entity].id.in_(selected[entity])
