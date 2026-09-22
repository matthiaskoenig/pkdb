"""Validate container shapes before interpreting legacy mapping expressions."""

import math

from pydantic import JsonValue

from pkdb.schemas.source import SourceLocation
from pkdb.schemas.validation import fail


def validate_json_tree(value: JsonValue, file: str):
    pending: list[tuple[JsonValue, tuple[str | int, ...]]] = [(value, ())]
    while pending:
        item, path = pending.pop()
        if len(path) > 64:
            fail(
                "json_depth",
                "JSON nesting exceeds 64 levels",
                SourceLocation(file=file, path=path),
            )
        if isinstance(item, float) and not math.isfinite(item):
            fail(
                "invalid_number",
                "JSON numbers must be finite",
                SourceLocation(file=file, path=path),
            )
        if isinstance(item, dict):
            pending.extend((child, (*path, key)) for key, child in item.items())
        elif isinstance(item, list):
            pending.extend((child, (*path, index)) for index, child in enumerate(item))


def list_value(value, field, source=None, *, nullable=True):
    if value is None and nullable:
        return []
    if not isinstance(value, list):
        fail("invalid_container", f"{field} must be a list", source)
    return value


def entry_structure(entry, source):
    if not isinstance(entry, dict):
        fail("invalid_entry", "Entries must be objects", source)
    for field in ("name", "source", "subset", "image"):
        value = entry.get(field)
        if field == "name" and type(value) in (int, float) and math.isfinite(value):
            continue
        if value is not None and not isinstance(value, str):
            fail("invalid_field", f"{field} must be text", source)
    for field in ("comments", "descriptions"):
        if field in entry:
            list_value(entry[field], field, source)
    for field in ("characteristica", "subsets"):
        if field in entry:
            for child in list_value(
                entry[field], field, source, nullable=field == "characteristica"
            ):
                entry_structure(child, source)
