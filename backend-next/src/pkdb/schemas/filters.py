"""Saved multi-entity criteria; permissions are never persisted as selected IDs."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from pkdb.schemas.queries import QuerySpec

FilterEntity = Literal[
    "studies", "groups", "individuals", "interventions", "outputs", "subsets"
]


class FilterSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    queries: dict[FilterEntity, QuerySpec] = {}
    concise: bool = True

    @model_validator(mode="after")
    def matching_entities(self):
        if any(entity != query.entity for entity, query in self.queries.items()):
            raise ValueError("Filter query entity must match its key")
        return self
