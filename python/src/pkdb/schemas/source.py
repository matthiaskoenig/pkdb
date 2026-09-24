"""Source identity and coordinates carried through scientific transformations."""

from pathlib import Path

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    PrivateAttr,
    model_serializer,
)


class SourceLocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    file: str
    sheet: str | None = None
    row: int | None = None
    column: str | None = None
    path: tuple[str | int, ...] = ()
    cell: str | None = None
    header: str | None = None
    _columns: dict[str, str] = PrivateAttr(default_factory=dict)
    _fields: dict[str, SourceLocation] = PrivateAttr(default_factory=dict)

    def __eq__(self, other):
        if not isinstance(other, SourceLocation):
            return NotImplemented
        return self.model_dump() == other.model_dump()

    def for_field(self, field: str) -> SourceLocation:
        return self._fields.get(field, self)

    def for_header(self, header: str) -> SourceLocation:
        column = self._columns.get(header)
        return SourceLocation.model_validate(
            {
                **self.model_dump(),
                "column": column,
                "cell": f"{column}{self.row}" if column and self.row else None,
                "header": header,
            }
        )

    @model_serializer(mode="wrap")
    def serialize(self, handler):
        result = handler(self)
        for field in ("cell", "header"):
            if result.get(field) is None:
                result.pop(field, None)
        return result

    def legacy_dict(self) -> dict:
        return self.model_dump(mode="json", exclude={"cell", "header"})


class SourceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    study: dict[str, JsonValue]
    reference: dict[str, JsonValue]
    files: dict[str, Path] = Field(default_factory=dict)
