"""Parameterized SQL predicates with a single related-row scope per relation."""

import math
from collections import defaultdict

from sqlalchemy import and_, exists, or_, select, true

from pkdb.db.models.interventions import Intervention
from pkdb.db.models.measurements import Measurement
from pkdb.db.models.studies import Reference, Study, StudyUser
from pkdb.db.models.subjects import Group, Individual
from pkdb.schemas.queries import Predicate, QuerySpec
from pkdb.schemas.security import Principal
from pkdb.services.authorization import AuthorizationDenied

STUDY_FIELDS = {
    name: getattr(Study, name) for name in ("sid", "name", "access", "licence")
}
OUTPUT_FIELDS = {
    name: getattr(Measurement, name)
    for name in (
        "id",
        "substance",
        "measurement_type",
        "value",
        "mean",
        "median",
        "sd",
        "se",
        "cv",
        "count",
        "unit",
        "choice",
        "time",
        "time_unit",
        "tissue",
        "method",
        "calculated",
        "output_type",
    )
}
OUTPUT_FIELDS.update(
    normed=Measurement.origin == "normalized",
    minimum=Measurement.minimum,
    maximum=Measurement.maximum,
    group_pk=Measurement.group_id,
    individual_pk=Measurement.individual_id,
)


MODELS = {
    "studies": Study,
    "outputs": Measurement,
    "groups": Group,
    "individuals": Individual,
    "interventions": Intervention,
    "references": Reference,
}


def fields_for(entity):
    if entity == "studies":
        return STUDY_FIELDS
    fields = {"study_sid": Study.sid, "study_name": Study.name}
    if entity == "references":
        return {
            **fields,
            **{
                name: getattr(Reference, name)
                for name in (
                    "sid",
                    "name",
                    "pmid",
                    "doi",
                    "title",
                    "abstract",
                    "journal",
                )
            },
        }
    if entity == "outputs":
        return {**fields, **OUTPUT_FIELDS}
    if entity == "interventions":
        return {
            **fields,
            **{
                name: getattr(Intervention, name)
                for name in (
                    "id",
                    "name",
                    "substance",
                    "measurement_type",
                    "route",
                    "form",
                    "application",
                    "unit",
                    "value",
                )
            },
            "normed": Intervention.origin == "normalized",
        }
    model = Group if entity == "groups" else Individual
    return {**fields, "id": model.id, "name": model.name}


def visibility(principal: Principal):
    if principal.role not in {"admin", "curator", "reviewer", "user", "anonymous"}:
        raise AuthorizationDenied("Unknown role")
    authenticated = principal.user_id is not None and principal.role != "anonymous"
    if authenticated and principal.role in {"admin", "reviewer"}:
        return true()
    if not authenticated:
        return Study.access == "public"
    membership = exists(
        select(StudyUser.study_id).where(
            StudyUser.study_id == Study.id, StudyUser.user_id == principal.user_id
        )
    )
    return or_(
        Study.access == "public", Study.creator_id == principal.user_id, membership
    )


def comparison(column, predicate: Predicate):
    value, op = predicate.value, predicate.operator
    if op != "isnull":
        expected = column.type.python_type
        for item in value if isinstance(value, list) else [value]:
            if item is None:
                continue
            valid = type(item) is expected
            if expected is float:
                valid = (
                    isinstance(item, (float, int))
                    and not isinstance(item, bool)
                    and math.isfinite(item)
                )
            if not valid:
                raise ValueError("Filter value has the wrong type")
        if op == "contains" and expected is not str:
            raise ValueError("contains requires a text field")
    if op in {"in", "exclude"}:
        if not isinstance(value, list) or len(value) > 1000:
            raise ValueError("List predicate requires at most 1000 values")
        test = column.in_(value)
        return ~test if op == "exclude" else test
    if isinstance(value, list):
        raise ValueError("Scalar predicate requires a scalar value")
    if op == "isnull":
        if not isinstance(value, bool):
            raise ValueError("isnull requires a boolean")
        return column.is_(None) if value else column.is_not(None)
    if value is None and op not in {"eq", "ne"}:
        raise ValueError("Null only supports equality")
    if op == "eq":
        return column == value
    if op == "ne":
        return column != value
    if op == "contains":
        if not isinstance(value, str):
            raise ValueError("contains requires text")
        return column.icontains(value, autoescape=True)
    if op == "gte":
        return column >= value
    if op == "gt":
        return column > value
    if op == "lte":
        return column <= value
    if op == "lt":
        return column < value
    raise ValueError("Unsupported operator")


def conditions(query: QuerySpec):
    result = []
    related = defaultdict(list)
    for predicate in query.predicates:
        if query.entity == "studies":
            if predicate.field.startswith("outputs."):
                field = predicate.field.removeprefix("outputs.")
                if field not in OUTPUT_FIELDS:
                    raise ValueError("Unknown output filter")
                related["outputs"].append(comparison(OUTPUT_FIELDS[field], predicate))
            elif predicate.field in STUDY_FIELDS:
                result.append(comparison(STUDY_FIELDS[predicate.field], predicate))
            else:
                raise ValueError("Unknown study filter")
        else:
            fields = fields_for(query.entity)
            if predicate.field not in fields:
                raise ValueError("Unknown output filter")
            result.append(comparison(fields[predicate.field], predicate))
    if related["outputs"]:
        result.append(
            exists(
                select(Measurement.id).where(
                    Measurement.study_id == Study.id, *related["outputs"]
                )
            )
        )
    if query.search:
        # Terms are escaped as values. The FTS adapter is added after golden membership checks.
        for term in query.search.split():
            result.append(
                or_(
                    Study.sid.icontains(term, autoescape=True),
                    Study.name.icontains(term, autoescape=True),
                )
            )
    return and_(*result) if result else true()


def ordering(query: QuerySpec):
    descending = query.sort.startswith("-")
    name = query.sort.removeprefix("-")
    fields = {"sid": Study.sid, **fields_for(query.entity)}
    if name not in fields:
        raise ValueError("Unknown ordering field")
    column = fields[name]
    key = MODELS[query.entity].id
    return (
        column.desc().nulls_last() if descending else column.asc().nulls_last(),
        key.asc(),
    )
