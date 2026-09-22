from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class StagedBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    study: dict[str, JsonValue]
    reference: dict[str, JsonValue]
    handles: list[UUID] = Field(default_factory=list, max_length=256)
