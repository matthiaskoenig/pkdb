"""Source identity and coordinates carried through scientific transformations."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class SourceLocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    file: str
    sheet: str | None = None
    row: int | None = None
    column: str | None = None
    path: tuple[str | int, ...] = ()


class SourceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    study: dict[str, JsonValue]
    reference: dict[str, JsonValue]
    files: dict[str, Path] = Field(default_factory=dict)
