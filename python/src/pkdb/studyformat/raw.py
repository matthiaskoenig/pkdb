"""Raw tables: a paper table transcribed as printed, beside the mapped rows.

A raw table `<study>_<source>.tsv` is a grid of text cells without a header
line, `study` or `source` columns. Its canonical form keeps the row order,
strips each cell, pads the rows to the widest row, and removes trailing empty
cells and empty rows. Nothing is parsed as a number.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.issues import make_issue
from pkdb.studyformat.tables import parse_table_file
from pkdb.studyformat.text import (
    CONFLICT_MARKERS,
    MAX_CELLS,
    TooManyCells,
    TsvError,
    cells_of,
    text_lines,
)

if TYPE_CHECKING:
    from pkdb.studyformat.load import RowLimit

RAW_SOURCE = re.compile(r"Tab[A-Za-z0-9_-]+")


@dataclass(frozen=True)
class RawRow:
    """A non-empty line of a raw table: its line number and stripped cells."""

    line: int
    cells: tuple[str, ...]


@dataclass
class LoadedRaw:
    """A raw table read into its non-empty rows."""

    file: str
    source: str
    rows: list[RawRow]


def raw_file(study: str, source: str) -> str:
    """File name `<study>_<source>.tsv` of the raw table of a paper table."""
    return f"{study}_{source}.tsv"


def parse_raw_file(name: str, study: str) -> str | None:
    """The source of a raw table file name of a study, or None.

    The study name is the prefix, so study names and sources may contain
    underscores; template table names are never raw tables.
    """
    prefix = f"{study}_"
    if (
        not name.endswith(".tsv")
        or not name.startswith(prefix)
        or parse_table_file(name) is not None
    ):
        return None
    source = name[len(prefix) : -len(".tsv")]
    return source if RAW_SOURCE.fullmatch(source) else None


def load_raw(
    file: str, chunks: Iterable[bytes], source: str, *, limit: RowLimit | None = None
) -> tuple[LoadedRaw | None, list[ValidationIssue]]:
    """Read a raw table; None and the issue when it is not UTF-8, too wide or conflicted.

    `limit` is the RowLimit of the study, which counts the non-empty lines.
    """
    rows: list[RawRow] = []
    try:
        for number, text in enumerate(text_lines(chunks), start=1):
            if text.startswith(CONFLICT_MARKERS):
                return None, [
                    make_issue(
                        "merge_conflict",
                        f"Line {number} is a git conflict marker; resolve the conflict",
                        file=file,
                        line=number,
                    )
                ]
            if (width := text.count("\t") + 1) > MAX_CELLS:
                error = TooManyCells(number, width)
                return None, [
                    make_issue("too_many_columns", str(error), file=file, line=number)
                ]
            cells = cells_of(text)
            if any(cells):
                if limit is not None:
                    limit.count()
                rows.append(RawRow(number, cells))
    except TsvError as error:
        return None, [make_issue("invalid_encoding", str(error), file=file)]
    return LoadedRaw(file, source, rows), []


def raw_lines(raw: LoadedRaw) -> list[tuple[int, tuple[str, ...]]]:
    """The canonical rows with their line numbers, as `raw_grid` keeps them.

    A line number is that of the file, or the row of the sheet, it was read from.
    """
    width = max(
        (
            max((index + 1 for index, cell in enumerate(row.cells) if cell), default=0)
            for row in raw.rows
        ),
        default=0,
    )
    return [
        (row.line, tuple((*row.cells, *([""] * width))[:width]))
        for row in raw.rows
        if any(row.cells[:width])
    ]


def raw_grid(raw: LoadedRaw) -> list[tuple[str, ...]]:
    """The canonical rows: padded to the widest row without trailing empty cells."""
    return [cells for _, cells in raw_lines(raw)]


def render_raw(raw: LoadedRaw) -> str | None:
    """Canonical text of a raw table; None removes a table without cells."""
    grid = raw_grid(raw)
    return "".join("\t".join(row) + "\n" for row in grid) if grid else None
