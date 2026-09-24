"""Translate familiar client keyword filters into typed public API requests."""

import math

from pkdb.schemas.data import DataQuery
from pkdb.schemas.filters import FilterSpec

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
NUMBERS = {"value", "mean", "median", "sd", "se", "cv", "minimum", "maximum", "time"}
INTEGERS = {
    "id",
    "count",
    "group_pk",
    "individual_pk",
    "intervention_pk",
    "raw_pk",
    "characteristica_pk",
    "group_count",
    "group_parent_pk",
    "individual_group_pk",
    "data_pk",
    "subset_pk",
    "data_point_pk",
}


def query_from_filters(entity: str, filters: dict) -> DataQuery:
    entity = "outputs" if entity == "measurements" else entity
    options = {key: value for key, value in filters.items() if value is not None}
    values = {
        "entity": entity,
        "page": options.pop("page", 1),
        "page_size": options.pop("page_size", 100),
        "sort": options.pop("sort", options.pop("ordering", "sid")),
        "search": options.pop("search", options.pop("search_multi_match", None)),
    }
    if options.pop("format", "json") != "json":
        raise ValueError("Only JSON query responses are supported")
    names = {
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
    predicates = []
    for key, raw in options.items():
        field, separator, operator = key.partition("__")
        operator = operator if separator else "eq"
        if entity in {"groups", "individuals"} and field in {
            "choice_sid",
            "measurement_type_sid",
        }:
            field = "characteristics." + (
                "measurement_type" if field == "measurement_type_sid" else field
            )
        else:
            field = field + "_name" if field in names else ALIASES.get(field, field)
        if entity == "studies" and field == "study_sid":
            field = "sid"
        if isinstance(raw, (list, tuple)) and not separator:
            operator = "in"

        def scalar(value):
            if operator == "isnull" or field in {"normed", "calculated"}:
                if isinstance(value, bool):
                    return value
                if str(value).lower() not in {"true", "false"}:
                    raise ValueError("Expected boolean filter")
                return str(value).lower() == "true"
            if field in INTEGERS:
                return int(value)
            if field in NUMBERS:
                number = float(value)
                if not math.isfinite(number):
                    raise ValueError("Expected finite number")
                return number
            return value

        if operator in {"in", "exclude"}:
            parts = raw if isinstance(raw, (list, tuple)) else str(raw).split("__")
            value = [scalar(item) for item in parts]
        else:
            value = scalar(raw)
        predicates.append({"field": field, "operator": operator, "value": value})
    return DataQuery.model_validate({**values, "predicates": predicates})


def export_from_filters(filters: dict) -> FilterSpec:
    options = {key: value for key, value in filters.items() if value is not None}
    concise = options.pop("concise", True)
    if isinstance(concise, str):
        if concise not in {"true", "false"}:
            raise ValueError("Expected boolean concise option")
        concise = concise == "true"
    if options.pop("format", "json") != "json":
        raise ValueError("Only JSON filter requests are supported")
    options.pop("download", None)
    entities = {}
    for key, value in options.items():
        entity, separator, field = key.partition("__")
        entity = "outputs" if entity == "measurements" else entity
        if not separator or entity not in {
            "studies",
            "groups",
            "individuals",
            "interventions",
            "outputs",
            "subsets",
        }:
            raise ValueError(
                "Dataset filters require an entity prefix, e.g. studies__sid"
            )
        entities.setdefault(entity, {})[field] = value
    return FilterSpec(
        queries={
            entity: query_from_filters(entity, values)
            for entity, values in entities.items()
        },
        concise=concise,
    )
