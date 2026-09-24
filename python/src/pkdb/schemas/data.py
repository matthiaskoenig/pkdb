"""Public data discovery contracts with one pagination envelope."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pkdb.schemas.queries import Page, QuerySpec
from pkdb.schemas.responses import (
    GroupResponse,
    IndividualResponse,
    InterventionResponse,
    OutputResponse,
    ReferenceResponse,
    StudyResponse,
    SubsetResponse,
    VocabularyResponse,
)

ScientificRecord = (
    StudyResponse
    | OutputResponse
    | GroupResponse
    | IndividualResponse
    | InterventionResponse
    | ReferenceResponse
    | SubsetResponse
    | VocabularyResponse
)


class DataQuery(QuerySpec):
    """Query an entity; measurements is the public alias for legacy outputs."""

    model_config = ConfigDict(
        json_schema_extra=lambda schema: schema["properties"]["entity"]["enum"].append(
            "measurements"
        )
    )

    @model_validator(mode="before")
    @classmethod
    def measurement_alias(cls, value):
        if not isinstance(value, dict):
            return value
        value = dict(value)
        if value.get("entity") == "measurements":
            value["entity"] = "outputs"
        if value.get("entity") == "studies" and isinstance(
            value.get("predicates"), list
        ):
            value["predicates"] = [
                {**predicate, "field": "outputs." + predicate["field"][13:]}
                if isinstance(predicate, dict)
                and isinstance(predicate.get("field"), str)
                and predicate["field"].startswith("measurements.")
                else predicate
                for predicate in value.get("predicates", [])
            ]
        return value


class DataPage[Record](BaseModel):
    """Page numbers in next/previous apply equally to GET and POST requests."""

    model_config = ConfigDict(extra="forbid")
    items: list[Record]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=1000)
    next: int | None = None
    previous: int | None = None

    @classmethod
    def from_page(cls, result: Page, query: QuerySpec) -> Self:
        return cls(
            items=result.items,
            total=result.count,
            page=query.page,
            page_size=query.page_size,
            next=result.next,
            previous=result.previous,
        )
