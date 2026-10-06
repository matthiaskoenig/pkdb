"""Canonical text: TSV parsing and rendering, numbers and natural sort order."""

import math
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from io import BytesIO

NUMBER_PATTERN = re.compile(r"[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
_DIGITS = re.compile(r"([0-9]+)")
# Lines git writes around the two sides of a merge conflict.
CONFLICT_MARKERS = ("<<<<<<<", "|||||||", "=======", ">>>>>>>")


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
    """Canonical text of a number written with a decimal point; None for any other text."""
    value = parse_number(text)
    return None if value is None else format_number(value)


def _number_key(digits: str) -> tuple:
    # Compares like int(digits) without converting, which Python refuses
    # for more than 4300 digits.
    significant = digits.lstrip("0")
    return 0, len(significant), significant


def natural_key(text: str) -> tuple:
    """Sort key that orders embedded numbers by value: Tab2 before Tab10.

    Text parts compare case-insensitively; the original text only breaks ties.
    """
    parts = tuple(
        _number_key(part) if index % 2 else (1, part.casefold())
        for index, part in enumerate(_DIGITS.split(text))
        if part
    )
    return parts, text


def unquote(cell: str) -> str:
    """Remove spreadsheet export quoting from a cell wrapped in double quotes.

    A cell whose unquoted text would again be wrapped in quotes keeps its text,
    so that reading a formatted file a second time changes nothing.
    """
    if len(cell) >= 2 and cell[0] == cell[-1] == '"':
        inner = cell[1:-1]
        if '"' not in inner.replace('""', ""):
            text = inner.replace('""', '"').strip()
            if not (text.startswith('"') and text.endswith('"')):
                return text
    return cell


class TsvError(ValueError):
    """The bytes are not a UTF-8 text table."""


@dataclass(frozen=True)
class TsvLine:
    """A line of a TSV file: its 1-based line number and its cell texts."""

    number: int
    cells: tuple[str, ...]
    # The line is a git conflict marker.
    conflict: bool = False


@dataclass(frozen=True)
class ParsedTsv:
    """Header, data lines and git conflict marker lines of a TSV file."""

    header: tuple[str, ...]
    lines: tuple[TsvLine, ...]
    # Numbers of the lines that are git conflict markers.
    conflicts: tuple[int, ...] = ()


def _cells(line: str) -> tuple[str, ...]:
    return tuple(unquote(cell.strip()) for cell in line.split("\t"))


_BOM = b"\xef\xbb\xbf"


def _text_lines(chunks: Iterable[bytes]) -> Iterator[str]:
    # A binary file yields its bytes split after each LF. CRLF, CR and LF all
    # end a line, and the text after the last line break is a line if it is
    # not empty. CR and LF never occur inside a UTF-8 multibyte sequence.
    offset = 0
    for chunk in chunks:
        start = offset
        offset += len(chunk)
        if start == 0 and chunk.startswith(_BOM):
            chunk, start = chunk[len(_BOM) :], len(_BOM)
        ended = chunk.endswith(b"\n")
        body = chunk[: -2 if chunk.endswith(b"\r\n") else -1] if ended else chunk
        parts = body.split(b"\r")
        if not ended and not parts[-1]:
            parts.pop()
        for part in parts:
            try:
                yield part.decode("utf-8")
            except UnicodeDecodeError as error:
                raise TsvError(
                    f"File is not UTF-8 encoded (byte {start + error.start})"
                ) from None
            start += len(part) + 1


def read_tsv(chunks: Iterable[bytes]) -> Iterator[TsvLine]:
    """Read a tab-separated table lazily, one line at a time.

    `chunks` are the bytes of the file, split after each LF as a binary file
    yields them. The header comes first, followed by the data lines; blank
    data lines are skipped. A line that is not UTF-8 raises TsvError when it
    is reached.
    """
    for number, text in enumerate(_text_lines(chunks), start=1):
        if number == 1 or text.strip():
            yield TsvLine(number, _cells(text), text.startswith(CONFLICT_MARKERS))


def parse_tsv(data: bytes) -> ParsedTsv:
    """Read a whole tab-separated table leniently; blank lines are skipped."""
    lines = read_tsv(BytesIO(data))
    header = next(lines, None)
    if header is None:
        return ParsedTsv((), ())
    rest = tuple(lines)
    return ParsedTsv(
        header.cells,
        rest,
        tuple(line.number for line in (header, *rest) if line.conflict),
    )


def render_tsv(header: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    """Canonical TSV text: tab-separated cells, LF line endings and a final newline."""
    return "".join("\t".join(cells) + "\n" for cells in (header, *rows))
