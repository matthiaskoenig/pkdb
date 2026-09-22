"""Interpret the legacy column and parallel-entry syntax without executing code."""

import math
from copy import deepcopy

from pkdb.schemas.source import SourceLocation
from pkdb.schemas.validation import fail

NA_VALUES = {"na", "NA", "nan", "NAN"}
LIST_FIELDS = {"interventions", "dimensions", "shared"}
TEXT_FIELDS = {"name", "group", "individual", "parent", "label", "choice"}


def clean(value):
    if isinstance(value, str):
        value = value.strip()
        return None if value in NA_VALUES else value
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def split_entry(entry: dict) -> list[dict]:
    values = {
        key: value.split("||") if isinstance(value, str) else [value]
        for key, value in entry.items()
    }
    lengths = {len(value) for value in values.values()}
    if not lengths:
        fail("empty_entry", "Empty entries are not permitted")
    count = max(lengths)
    if lengths - {1, count}:
        fail("split_length", "Parallel || fields have incompatible lengths")
    if count > 1 and "name" in values and len(values["name"]) == 1:
        fail("split_name", "Named entries must supply a name for each split")
    result = [{} for _ in range(count)]
    for key, parts in values.items():
        for index in range(count):
            value = clean(parts[0 if len(parts) == 1 else index])
            if isinstance(value, str) and ("{{" in value or "}}" in value):
                fail("old_split_syntax", "Use || for parallel entries")
            if value == "[]":
                value = []
            if key in LIST_FIELDS and isinstance(value, str):
                value = [part.strip() for part in value.split(",")]
            if key in LIST_FIELDS and isinstance(value, list):
                value = [
                    part.strip() if isinstance(part, str) else part
                    for item in value
                    for part in (item.split(",") if isinstance(item, str) else [item])
                ]
            if (
                key in TEXT_FIELDS
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
            ):
                if not math.isfinite(value):
                    fail("invalid_number", "Text field numbers must be finite")
                value = str(value)
            result[index][key] = deepcopy(value)
    return result


def bind_columns(template, row: dict, source: SourceLocation | None = None):
    if isinstance(template, dict):
        result = {
            key: bind_columns(value, row, source) for key, value in template.items()
        }
        for key, original in template.items():
            if (
                key in LIST_FIELDS
                and isinstance(original, list)
                and any(
                    isinstance(value, str) and value.strip().startswith("col==")
                    for value in original
                )
            ):
                result[key] = [value for value in result[key] if value is not None]
        return result
    if isinstance(template, list):
        return [bind_columns(value, row, source) for value in template]
    if isinstance(template, str) and "==" in template:
        parts = [part.strip() for part in template.split("==")]
        if len(parts) != 2 or parts[0] != "col" or not parts[1]:
            fail("invalid_expression", f"Invalid column expression: {template}", source)
        if parts[1] not in row:
            fail("unknown_column", f"Unknown column: {parts[1]}", source)
        return clean(row[parts[1]])
    return clean(template)


EXTERNAL_ALIASES = {
    "individual_exs": "individuals",
    "individual_ex": "individual",
    "intervention_exs": "interventions",
    "group_exs": "groups",
    "characteristica_ex": "characteristica",
    "parent_ex": "parent",
    "output_exs": "outputs",
}


def external_aliases(value, path=()):
    if isinstance(value, list):
        return [
            external_aliases(item, (*path, index)) for index, item in enumerate(value)
        ]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, child in value.items():
        field = EXTERNAL_ALIASES.get(key, key)
        if field in result:
            fail(
                "duplicate_alias",
                f"Multiple fields map to {field}",
                SourceLocation(file="study.json", path=path),
            )
        result[field] = external_aliases(child, (*path, key))
    return result
