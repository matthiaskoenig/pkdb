"""Legacy HTTP read envelopes backed by the shared PostgreSQL query service."""

import math

from fastapi import APIRouter, Request
from pydantic import ValidationError
from starlette.exceptions import HTTPException

from pkdb.schemas.queries import Predicate, QuerySpec

router = APIRouter(prefix="/api/v1")
ALIASES = {
    "substance_sid": "substance",
    "measurement_type_sid": "measurement_type",
    "tissue_sid": "tissue",
    "method_sid": "method",
    "output_pk": "id",
    "pk": "id",
    "min": "minimum",
    "max": "maximum",
    "form_sid": "form",
    "route_sid": "route",
    "application_sid": "application",
}
BOOLEANS = {"normed", "calculated"}
NUMBERS = {"value", "mean", "median", "sd", "se", "cv", "minimum", "maximum", "time"}
INTEGERS = {"id", "count", "group_pk", "individual_pk"}


def query_spec(request: Request, entity: str) -> QuerySpec:
    predicates = []
    params = request.query_params
    try:
        for key, raw in params.multi_items():
            if key in {"page", "page_size", "ordering", "search"}:
                continue
            field, separator, operator = key.partition("__")
            name_fields = {
                "studies": {"substance"},
                "outputs": {"substance", "tissue"},
                "interventions": {
                    "substance",
                    "measurement_type",
                    "form",
                    "route",
                    "application",
                },
            }.get(entity, set())
            if entity in {"groups", "individuals"} and field in {
                "choice_sid",
                "measurement_type_sid",
            }:
                field = "characteristics." + (
                    "measurement_type" if field == "measurement_type_sid" else field
                )
            else:
                field = (
                    field + "_name"
                    if field in name_fields
                    else ALIASES.get(field, field)
                )
            operator = operator if separator else "eq"

            def scalar(value):
                if operator == "isnull" or field in BOOLEANS:
                    if value.lower() not in {"true", "false"}:
                        raise ValueError("Expected boolean")
                    return value.lower() == "true"
                if field in INTEGERS:
                    return int(value)
                if field in NUMBERS:
                    number = float(value)
                    if not math.isfinite(number):
                        raise ValueError("Expected finite number")
                    return number
                return value

            value = (
                [scalar(v) for v in raw.split("__")]
                if operator in {"in", "exclude"}
                else scalar(raw)
            )
            predicates.append(
                Predicate.model_validate(
                    dict(field=field, operator=operator, value=value)
                )
            )
        return QuerySpec.model_validate(
            dict(
                entity=entity,
                predicates=predicates,
                search=params.get("search"),
                sort=params.get("ordering", "sid"),
                page=int(params.get("page", "1")),
                page_size=int(params.get("page_size", "20")),
            )
        )
    except (ValidationError, ValueError):
        raise HTTPException(400, "Invalid query parameters") from None


def result_page(request: Request, query: QuerySpec):
    actor = request.app.state.principal(request, required=False)
    try:
        page = request.app.state.queries.search(query, actor)
    except ValueError:
        raise HTTPException(400, "Invalid query parameters") from None
    if query.page > 1 and not page.items:
        raise HTTPException(404, "Invalid page")

    def link(number):
        return str(request.url.include_query_params(page=number)) if number else None

    return {
        "current_page": query.page,
        "last_page": max(1, math.ceil(page.count / query.page_size)),
        "next_page_url": link(page.next),
        "prev_page_url": link(page.previous),
        "data": {"count": page.count, "data": page.items},
    }


@router.get("/outputs/")
def outputs(request: Request):
    return result_page(request, query_spec(request, "outputs"))


@router.get("/outputs/{output_id}/")
def output_detail(output_id: int, request: Request):
    actor = request.app.state.principal(request, required=False)
    page = request.app.state.queries.search(
        QuerySpec(
            entity="outputs", predicates=[Predicate(field="id", value=output_id)]
        ),
        actor,
    )
    if not page.items:
        raise HTTPException(404, "Not found")
    return page.items[0]


@router.get("/statistics/")
def statistics(request: Request):
    actor = request.app.state.principal(request, required=False)
    return {"version": "0.10.0", **request.app.state.queries.statistics(actor)}


@router.get("/groups/")
def groups(request: Request):
    return result_page(request, query_spec(request, "groups"))


@router.get("/individuals/")
def individuals(request: Request):
    return result_page(request, query_spec(request, "individuals"))


def subject_detail(entity, identifier, request):
    actor = request.app.state.principal(request, required=False)
    page = request.app.state.queries.search(
        QuerySpec.model_validate(
            {"entity": entity, "predicates": [{"field": "id", "value": identifier}]}
        ),
        actor,
    )
    if not page.items:
        raise HTTPException(404, "Not found")
    return page.items[0]


@router.get("/groups/{identifier}/")
def group_detail(identifier: int, request: Request):
    return subject_detail("groups", identifier, request)


@router.get("/individuals/{identifier}/")
def individual_detail(identifier: int, request: Request):
    return subject_detail("individuals", identifier, request)


@router.get("/interventions/")
def interventions(request: Request):
    return result_page(request, query_spec(request, "interventions"))


@router.get("/interventions/{identifier}/")
def intervention_detail(identifier: int, request: Request):
    return subject_detail("interventions", identifier, request)


@router.get("/references/")
def references(request: Request):
    return result_page(request, query_spec(request, "references"))


@router.get("/references/{sid}/")
def reference_detail(sid: str, request: Request):
    actor = request.app.state.principal(request, required=False)
    page = request.app.state.queries.search(
        QuerySpec(entity="references", predicates=[Predicate(field="sid", value=sid)]),
        actor,
    )
    if not page.items:
        raise HTTPException(404, "Not found")
    return page.items[0]


@router.get("/subsets/")
def subsets(request: Request):
    return result_page(request, query_spec(request, "subsets"))


@router.get("/subsets/{identifier}/")
def subset_detail(identifier: int, request: Request):
    return subject_detail("subsets", identifier, request)


@router.get("/studies/")
def studies(request: Request):
    return result_page(request, query_spec(request, "studies"))


@router.get("/studies/{sid}/")
def study_detail(sid: str, request: Request):
    actor = request.app.state.principal(request, required=False)
    page = request.app.state.queries.search(
        QuerySpec(entity="studies", predicates=[Predicate(field="sid", value=sid)]),
        actor,
    )
    if not page.items:
        raise HTTPException(404, "Not found")
    return page.items[0]


@router.get("/info_nodes/")
def info_nodes(request: Request):
    return result_page(request, query_spec(request, "info_nodes"))


@router.get("/info_nodes/{sid}/")
def info_node_detail(sid: str, request: Request):
    actor = request.app.state.principal(request, required=False)
    page = request.app.state.queries.search(
        QuerySpec(entity="info_nodes", predicates=[Predicate(field="sid", value=sid)]),
        actor,
    )
    if not page.items:
        raise HTTPException(404, "Not found")
    return page.items[0]
