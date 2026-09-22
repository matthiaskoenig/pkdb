"""Parameterized SQL predicates with a single related-row scope per relation."""

import math
from collections import defaultdict

from sqlalchemy import String, and_, case, exists, func, or_, select, true

from pkdb.db.models.interventions import Intervention
from pkdb.db.models.measurements import Measurement, Scatter, Subset
from pkdb.db.models.studies import Reference, Study, StudyGrant, StudyUser
from pkdb.db.models.subjects import Group, Individual
from pkdb.db.models.users import User
from pkdb.db.models.vocabulary import VocabularyEdge, VocabularyNode, VocabularyTerm
from pkdb.db.search import search_condition, vocabulary_match
from pkdb.db.subject_filters import characteristic_fields, effective_characteristics
from pkdb.db.textsearch import text_match
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
    "info_nodes": VocabularyNode,
    "outputs": Measurement,
    "groups": Group,
    "individuals": Individual,
    "interventions": Intervention,
    "references": Reference,
    "subsets": Subset,
}


def node_name(column):
    return (
        select(VocabularyNode.name)
        .where(VocabularyNode.sid == column)
        .scalar_subquery()
    )


def fields_for(entity):
    if entity == "info_nodes":
        dtype = (
            select(func.trim(VocabularyTerm.value, '"', type_=String))
            .where(
                VocabularyTerm.node_sid == VocabularyNode.sid,
                VocabularyTerm.kind == "dtype",
            )
            .scalar_subquery()
        )
        return {
            "sid": VocabularyNode.sid,
            "name": VocabularyNode.name,
            "ntype": case(
                (VocabularyNode.kind == "measurement", "measurement_type"),
                else_=VocabularyNode.kind,
            ),
            "dtype": func.coalesce(
                dtype, VocabularyNode.definition["dtype"].astext, "undefined"
            ),
        }
    if entity == "studies":
        return {
            **STUDY_FIELDS,
            "reference_name": select(Reference.name)
            .where(Reference.id == Study.reference_id)
            .scalar_subquery(),
            "creator": select(User.username)
            .where(User.id == Study.creator_id)
            .scalar_subquery(),
        }
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
        return {
            **fields,
            **OUTPUT_FIELDS,
            **{
                name + "_name": node_name(getattr(Measurement, name))
                for name in ("substance", "measurement_type", "tissue", "method")
            },
        }
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
            **{
                name + "_name": node_name(getattr(Intervention, name))
                for name in (
                    "substance",
                    "measurement_type",
                    "route",
                    "form",
                    "application",
                )
            },
            **{
                name: getattr(Intervention, name)
                for name in (
                    "mean",
                    "median",
                    "sd",
                    "se",
                    "cv",
                    "time",
                    "time_unit",
                    "choice",
                    "calculated",
                )
            },
            "minimum": Intervention.minimum,
            "maximum": Intervention.maximum,
        }
    if entity == "subsets":
        return {
            **fields,
            "id": Subset.id,
            "name": Subset.name,
            "data_type": Scatter.data_type,
        }
    model = Group if entity == "groups" else Individual
    return {**fields, "id": model.id, "name": model.name}


def visibility(principal: Principal):
    from pkdb.services.authorization import require_scope

    require_scope(principal, "read")
    if principal.role not in {"admin", "curator", "reviewer", "user", "anonymous"}:
        raise AuthorizationDenied("Unknown role")
    authenticated = principal.user_id is not None and principal.role != "anonymous"
    if authenticated and principal.role in {"admin", "reviewer"}:
        return true()
    if not authenticated:
        return Study.access == "public"
    membership = exists(
        select(StudyGrant.study_id).where(
            StudyGrant.study_id == Study.id, StudyGrant.user_id == principal.user_id
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
    subject_entity = query.entity in {"groups", "individuals"}
    effective = (
        effective_characteristics(query.entity)
        if subject_entity
        and (
            query.search
            or any(p.field.startswith("characteristics.") for p in query.predicates)
        )
        else None
    )
    for predicate in query.predicates:
        if effective is not None and predicate.field.startswith("characteristics."):
            fields = characteristic_fields(effective)
            field = predicate.field.removeprefix("characteristics.")
            if field not in fields:
                raise ValueError("Unknown characteristic filter")
            model = Group if query.entity == "groups" else Individual
            scope = effective.c.subject_id == model.id
            if predicate.operator in {"exclude", "ne"}:
                positive = predicate.model_copy(
                    update={
                        "operator": "in" if predicate.operator == "exclude" else "eq"
                    }
                )
                result.append(
                    ~exists(
                        select(effective.c.id).where(
                            scope, comparison(fields[field], positive)
                        )
                    )
                )
            else:
                related["characteristics"].append(comparison(fields[field], predicate))
        elif query.entity == "studies":
            if predicate.field.startswith("outputs."):
                field = predicate.field.removeprefix("outputs.")
                if field not in OUTPUT_FIELDS:
                    raise ValueError("Unknown output filter")
                related["outputs"].append(comparison(OUTPUT_FIELDS[field], predicate))
            elif predicate.field in {"curators", "collaborator"}:
                role = "curator" if predicate.field == "curators" else "collaborator"
                result.append(
                    exists(
                        select(StudyUser.user_id)
                        .join(User, User.id == StudyUser.user_id)
                        .where(
                            StudyUser.study_id == Study.id,
                            StudyUser.role == role,
                            comparison(User.username, predicate),
                        )
                    )
                )
            elif predicate.field == "substance_name":
                # Match immediate parent substances, as exposed in study details.
                source_ids = (
                    select(Measurement.substance)
                    .where(Measurement.study_id == Study.id)
                    .correlate(Study)
                    .union(
                        select(Intervention.substance)
                        .where(Intervention.study_id == Study.id)
                        .correlate(Study)
                    )
                )
                parent_ids = select(VocabularyEdge.parent).where(
                    VocabularyEdge.child.in_(source_ids)
                )
                direct_ids = select(VocabularyNode.sid).where(
                    VocabularyNode.sid.in_(source_ids),
                    ~exists(
                        select(VocabularyEdge.child).where(
                            VocabularyEdge.child == VocabularyNode.sid
                        )
                    ),
                )
                from sqlalchemy.orm import aliased

                substance = aliased(VocabularyNode)
                result.append(
                    exists(
                        select(substance.sid).where(
                            or_(
                                substance.sid.in_(parent_ids),
                                substance.sid.in_(direct_ids),
                            ),
                            comparison(substance.name, predicate),
                        )
                    )
                )
            elif predicate.field in fields_for("studies"):
                result.append(
                    comparison(fields_for("studies")[predicate.field], predicate)
                )
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
    if effective is not None and related["characteristics"]:
        model = Group if query.entity == "groups" else Individual
        result.append(
            exists(
                select(effective.c.id).where(
                    effective.c.subject_id == model.id, *related["characteristics"]
                )
            )
        )
    if query.search:
        for term in query.search.split():
            match = search_condition(query.entity, term)
            if effective is not None:
                model = Group if query.entity == "groups" else Individual
                match = or_(
                    match,
                    exists(
                        select(effective.c.id).where(
                            effective.c.subject_id == model.id,
                            or_(
                                vocabulary_match(
                                    [
                                        effective.c.measurement_type,
                                        effective.c.substance,
                                        characteristic_fields(effective)["choice_sid"],
                                    ],
                                    term,
                                ),
                                text_match([effective.c.choice], term),
                            ),
                        )
                    ),
                )
            result.append(match)
    return and_(*result) if result else true()


def ordering(query: QuerySpec):
    descending = query.sort.startswith("-")
    name = query.sort.removeprefix("-")
    fields = {"sid": Study.sid, **fields_for(query.entity)}
    if name not in fields:
        raise ValueError("Unknown ordering field")
    column = fields[name]
    model = MODELS[query.entity]
    key = model.sid if model is VocabularyNode else model.id
    return (
        column.desc().nulls_last() if descending else column.asc().nulls_last(),
        key.asc(),
    )
