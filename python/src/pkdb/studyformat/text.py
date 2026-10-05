"""Canonical text: TSV parsing and rendering, numbers and natural sort order."""

import math
import re
from dataclasses import dataclass

NUMBER_PATTERN = re.compile(r"[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
_DIGITS = re.compile(r"(\d+)")


def parse_number(text: str) -> float | None:
    """Parse a decimal number written with a decimal point; None otherwise."""
    if not NUMBER_PATTERN.fullmatch(text):
        return None
    value = float(text)
    return value if math.isfinite(value) else None


def format_number(value: float) -> str:
    """Shortest text that converts back to the same float; integers without point."""
    if value == 0:
        return "0"
    if value.is_integer() and abs(value) < 1e16:
        return str(int(value))
    return repr(value)


def canonical_number(text: str) -> str | None:
    value = parse_number(text)
    return None if value is None else format_number(value)


def natural_key(text: str) -> tuple:
    """Sort key that orders embedded numbers by value: Tab2 before Tab10.

    Text parts compare case-insensitively; the original text only breaks ties.
    """
    parts = tuple(
        (0, int(part)) if index % 2 else (1, part.casefold())
        for index, part in enumerate(_DIGITS.split(text))
        if part
    )
    return parts, text


def unquote(cell: str) -> str:
    """Remove spreadsheet export quoting from a cell wrapped in double quotes."""
    if len(cell) >= 2 and cell[0] == cell[-1] == '"':
        inner = cell[1:-1]
        if '"' not in inner.replace('""', ""):
            return inner.replace('""', '"').strip()
    return cell


class TsvError(ValueError):
    """The bytes are not a UTF-8 text table."""


@dataclass(frozen=True)
class TsvLine:
    number: int
    cells: tuple[str, ...]


@dataclass(frozen=True)
class ParsedTsv:
    header: tuple[str, ...]
    lines: tuple[TsvLine, ...]


def _cells(line: str) -> tuple[str, ...]:
    return tuple(unquote(cell.strip()) for cell in line.split("\t"))


def parse_tsv(data: bytes) -> ParsedTsv:
    """Read a tab-separated table leniently; blank lines are skipped."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise TsvError(f"File is not UTF-8 encoded (byte {error.start})") from None
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return ParsedTsv((), ())
    return ParsedTsv(
        _cells(lines[0]),
        tuple(
            TsvLine(number, _cells(line))
            for number, line in enumerate(lines[1:], start=2)
            if line.strip()
        ),
    )


def render_tsv(header: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    return "".join("\t".join(cells) + "\n" for cells in (header, *rows))
