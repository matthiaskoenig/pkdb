"""Bounded, transport-independent query inputs; SQL fields are explicitly mapped."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Scalar = str | int | float | bool | None


class Predicate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    field: str = Field(min_length=1, max_length=100)
    operator: Literal[
        "eq", "ne", "in", "exclude", "gt", "gte", "lt", "lte", "isnull", "contains"
    ] = "eq"
    value: Scalar | list[Scalar]


class QuerySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity: Literal["studies", "outputs", "groups", "individuals", "interventions"]
    predicates: list[Predicate] = Field(default_factory=list, max_length=50)
    search: str | None = Field(default=None, max_length=500)
    sort: str = "sid"
    page: int = Field(default=1, ge=1, le=1000000)
    page_size: int = Field(default=100, ge=1, le=1000)


class Page(BaseModel):
    items: list[dict]
    count: int
    next: int | None = None
    previous: int | None = None
