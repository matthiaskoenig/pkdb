"""Source identity and coordinates carried through scientific transformations."""

from copy import deepcopy
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
    # A name that identifies the place of an issue in a file without rows: the dataset of a
    # WebPlotDigitizer project or the review item of `review.json`.
    key: str | None = None
    # Pydantic copies these defaults per instance. Avoid inspecting a factory
    # signature for every source coordinate created during table expansion.
    _columns: dict[str, str] = PrivateAttr(default={})
    _fields: dict[str, SourceLocation] = PrivateAttr(default={})
    # Headers of the columns that hold record fields, for rows that map fields to
    # cells. for_field resolves them on demand, so a large table does not create
    # a location for every cell up front.
    _headers: dict[str, str] = PrivateAttr(default={})

    def __deepcopy__(self, memo=None):
        # Public coordinates contain only immutable scalars and a tuple of
        # scalars. Copy the two mutable lookup maps, not every coordinate value.
        # Subclasses may introduce mutable fields and use Pydantic's full copy.
        if type(self) is not SourceLocation:
            return super().__deepcopy__(memo)
        if memo is None:
            memo = {}
        location = self.__copy__()
        memo[id(self)] = location
        location._columns = deepcopy(self._columns, memo)
        location._fields = deepcopy(self._fields, memo)
        location._headers = deepcopy(self._headers, memo)
        return location

    def __eq__(self, other):
        if not isinstance(other, SourceLocation):
            return NotImplemented
        return self.model_dump() == other.model_dump()

    def for_field(self, field: str) -> SourceLocation:
        location = self._fields.get(field)
        if location is not None:
            return location
        header = self._headers.get(field)
        return self if header is None else self.for_header(header)

    def for_header(self, header: str) -> SourceLocation:
        column = self._columns.get(header)
        # These values come from this validated location and the reader's column
        # map. Avoid serializing and revalidating every field for every cell.
        location = self.model_copy(
            update={
                "column": column,
                "cell": f"{column}{self.row}" if column and self.row else None,
                "header": header,
            }
        )
        # A header location, like the former model_validate result, has no row
        # lookup maps. In particular, do not share mutable maps with its parent.
        location.model_fields_set.update(type(self).model_fields)
        location._columns = {}
        location._fields = {}
        location._headers = {}
        return location

    @model_serializer(mode="wrap")
    def serialize(self, handler):
        result = handler(self)
        for field in ("cell", "header", "key"):
            if result.get(field) is None:
                result.pop(field, None)
        return result

    def legacy_dict(self) -> dict:
        return self.model_dump(mode="json", exclude={"cell", "header", "key"})


class SourceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    study: dict[str, JsonValue]
    reference: dict[str, JsonValue]
    files: dict[str, Path] = Field(default_factory=dict)
