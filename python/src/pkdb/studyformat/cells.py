"""Canonical text and typed values of single TSV cells."""

import re
from dataclasses import dataclass

from pkdb.studyformat.columns import Column, ColumnType
from pkdb.studyformat.tables import SOURCE_PATTERN
from pkdb.studyformat.text import format_number, natural_key, parse_number

NOT_REPORTED = "NR"
NAME_PATTERN = re.compile(r"[^,;\t\r\n]+")
MISSING = frozenset({"NA", "nan", "NaN"})
DECIMAL_COMMA = re.compile(r"[+-]?[0-9]+,[0-9]+")


@dataclass(frozen=True)
class CellProblem:
    """Why a cell cannot be parsed: an issue code, a message and an optional hint."""

    code: str
    message: str
    hint: str | None = None


def canonical_cell(column: Column, text: str) -> str:
    """Canonical text of a cell. Values that cannot be parsed stay unchanged."""
    text = text.strip()
    if column.type is not ColumnType.TEXT and text in MISSING:
        return ""
    if not text:
        return ""
    match column.type:
        case ColumnType.NUMBER | ColumnType.INTEGER | ColumnType.TIME:
            value = parse_number(text)
            return text if value is None else format_number(value)
        case ColumnType.TIMES:
            values = [parse_number(part.strip()) for part in text.split(";")]
            if any(value is None for value in values):
                return text
            return ";".join(
                format_number(value) for value in values if value is not None
            )
        case ColumnType.NAMES:
            names = [part.strip() for part in text.split(",")]
            if not all(names):
                return text
            return ",".join(sorted(names, key=natural_key))
        case _:
            return text


def _decimal_comma_hint(text: str, *, listed: bool = False) -> str | None:
    """A hint for a number written with a decimal comma, or a `;` list with one."""
    parts = text.split(";") if listed else [text]
    if any(DECIMAL_COMMA.fullmatch(part.strip()) for part in parts):
        return f"Use a decimal point: {text.replace(',', '.')} instead of {text}."
    return None


def _number_problem(text: str) -> CellProblem:
    return CellProblem(
        "invalid_number",
        f"Expected a number, found {text!r}",
        _decimal_comma_hint(text),
    )


def parse_cell(column: Column, text: str) -> tuple[object, CellProblem | None]:
    """Typed value of a canonical cell, or None and the problem."""
    if not text:
        return ((), None) if column.type is ColumnType.NAMES else (None, None)
    if column.allows_nr and text == NOT_REPORTED:
        return NOT_REPORTED, None
    match column.type:
        case ColumnType.NUMBER:
            value = parse_number(text)
            return (value, None) if value is not None else (None, _number_problem(text))
        case ColumnType.INTEGER:
            value = parse_number(text)
            if value is None or not value.is_integer() or value < 0:
                return None, CellProblem(
                    "invalid_integer",
                    f"Expected a whole number of at least 0, found {text!r}",
                    _decimal_comma_hint(text),
                )
            return int(value), None
        case ColumnType.TIME:
            value = parse_number(text)
            if value is None:
                return None, CellProblem(
                    "invalid_time",
                    f"Expected a number or NR, found {text!r}",
                    _decimal_comma_hint(text),
                )
            return value, None
        case ColumnType.TIMES:
            values = [parse_number(part) for part in text.split(";")]
            if any(value is None for value in values):
                return None, CellProblem(
                    "invalid_time",
                    f"Expected a number, a ;-separated list of numbers or NR, found {text!r}",
                    _decimal_comma_hint(text, listed=True),
                )
            return tuple(value for value in values if value is not None), None
        case ColumnType.NAME:
            if not NAME_PATTERN.fullmatch(text):
                return None, CellProblem(
                    "invalid_name",
                    f"Names cannot contain commas or semicolons: {text!r}",
                )
            return text, None
        case ColumnType.NAMES:
            names = tuple(part.strip() for part in text.split(","))
            if not all(NAME_PATTERN.fullmatch(name) for name in names):
                return None, CellProblem(
                    "invalid_name",
                    f"Expected comma-separated names without empty entries, found {text!r}",
                )
            return names, None
        case ColumnType.ENUM:
            if text not in column.choices:
                return None, CellProblem(
                    "invalid_enum",
                    f"Expected one of {', '.join(column.choices)}, found {text!r}",
                )
            return text, None
        case ColumnType.SOURCE:
            if not SOURCE_PATTERN.fullmatch(text):
                return None, CellProblem(
                    "invalid_source",
                    f"Expected Tab or Fig followed by letters or digits (Tab1, Fig2A) or Text, found {text!r}",
                )
            return text, None
        case _:
            return text, None
