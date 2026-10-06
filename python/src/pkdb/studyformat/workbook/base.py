"""Location of the workbook, its `_base` sheet, its sync state file and its lock files.

This module stays free of openpyxl and of the study format modules, because the
layout scan imports SHEET_NAME_LIMIT from it.
"""

import base64
import hashlib
import json
import zlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pkdb.cache import atomic_json

# Excel limits sheet names to 31 characters.
SHEET_NAME_LIMIT = 31
# Hidden sheet with the lists of the dropdowns.
LISTS_SHEET = "_lists"
# Very hidden sheet with the tables the workbook was generated from.
BASE_SHEET = "_base"
# Version of the workbook layout, stored in `_base`.
WORKBOOK_FORMAT = 1
# Characters per `_base` cell; a spreadsheet cell holds at most 32,767.
BASE_CHUNK = 32000
BASE_MARKER = "pkdb workbook"
STATE_FORMAT = 1


@dataclass(frozen=True)
class WorkbookBase:
    """The tables a workbook was generated from: the base of the 3-way merge.

    `generation` is a uuid4 hex that a regeneration renews, `created` the UTC
    time of the generation and `files` the canonical text of each table file.
    """

    generation: str
    created: datetime
    files: Mapping[str, str]


class BaseError(Exception):
    """The `_base` sheet cannot be read: `workbook_base_invalid` or `workbook_newer`."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def base_rows(base: WorkbookBase) -> list[tuple[object, ...]]:
    """Rows of the `_base` sheet.

    The first row holds the marker, the workbook format, the generation and the
    creation time. Every further row holds a file name, the SHA-256 of its text,
    the index of the chunk and the chunk: the base64 of the zlib-compressed text,
    split every BASE_CHUNK characters.
    """
    rows: list[tuple[object, ...]] = [
        (BASE_MARKER, WORKBOOK_FORMAT, base.generation, base.created.isoformat())
    ]
    for file in sorted(base.files):
        data = base.files[file].encode("utf-8")
        checksum = hashlib.sha256(data).hexdigest()
        encoded = base64.b64encode(zlib.compress(data)).decode("ascii")
        rows.extend(
            (file, checksum, index, encoded[start : start + BASE_CHUNK])
            for index, start in enumerate(range(0, len(encoded), BASE_CHUNK))
        )
    return rows


def _integer(value: object) -> int | None:
    # A spreadsheet application may store a whole number as a float.
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _invalid(message: str) -> BaseError:
    return BaseError("workbook_base_invalid", message)


def parse_base(rows: Iterable[tuple[object, ...]]) -> WorkbookBase:
    """Read the rows of the `_base` sheet; trailing empty cells and empty rows are ignored."""
    rows = iter(rows)
    head = tuple(next(rows, ()))
    if len(head) < 4 or head[0] != BASE_MARKER:
        raise _invalid(f"The {BASE_SHEET} sheet does not start with {BASE_MARKER!r}")
    version, generation, created = _integer(head[1]), head[2], None
    if version is None or version < 1:
        raise _invalid(f"The {BASE_SHEET} sheet has an invalid format {head[1]!r}")
    if version > WORKBOOK_FORMAT:
        raise BaseError(
            "workbook_newer",
            f"The workbook has format {version}, but this pkdb reads format "
            f"{WORKBOOK_FORMAT}; update pkdb",
        )
    if not isinstance(generation, str) or not generation:
        raise _invalid(f"The {BASE_SHEET} sheet has no generation")
    if isinstance(head[3], str):
        try:
            created = datetime.fromisoformat(head[3])
        except ValueError:
            pass
    if created is None or created.tzinfo is None:
        raise _invalid(f"The {BASE_SHEET} sheet has an invalid time {head[3]!r}")
    chunks: dict[str, list[str]] = {}
    checksums: dict[str, str] = {}
    for number, row in enumerate(rows, start=2):
        cells = (*row[:4], None, None, None, None)[:4]
        if all(cell is None for cell in row):
            continue
        file, checksum, index, chunk = cells
        if not (
            isinstance(file, str)
            and isinstance(checksum, str)
            and isinstance(chunk, str)
        ):
            raise _invalid(f"Row {number} of the {BASE_SHEET} sheet is incomplete")
        parts = chunks.setdefault(file, [])
        if (
            _integer(index) != len(parts)
            or checksums.setdefault(file, checksum) != checksum
        ):
            raise _invalid(
                f"Row {number} of the {BASE_SHEET} sheet does not continue {file}"
            )
        parts.append(chunk)
    files = {}
    for file, parts in chunks.items():
        try:
            data = zlib.decompress(base64.b64decode("".join(parts), validate=True))
            text = data.decode("utf-8")
        except ValueError, zlib.error:
            raise _invalid(f"The base of {file} cannot be decoded") from None
        if hashlib.sha256(data).hexdigest() != checksums[file]:
            raise _invalid(f"The base of {file} does not match its checksum")
        files[file] = text
    return WorkbookBase(generation, created, files)


def workbook_path(folder: Path) -> Path:
    """The workbook of a study folder, named after the study: Smith2020/Smith2020.xlsx."""
    return folder / f"{folder.name}.xlsx"


def state_path(workbook: Path) -> Path:
    """The hidden sync state file next to the workbook: .Smith2020.xlsx.pkdb-base."""
    return workbook.with_name(f".{workbook.name}.pkdb-base")


def open_lock(workbook: Path) -> Path | None:
    """The lock file that shows the workbook is open in a spreadsheet program, or None.

    LibreOffice creates `.~lock.<file>#` and Excel creates `~$<file>`; Office
    replaces the first two characters of the file name of long names, so the
    name without them is checked as well. Only regular files count; a folder or a
    symbolic link with such a name is no lock.
    """
    name = workbook.name
    for lock in (f".~lock.{name}#", f"~${name}", f"~${name[2:]}"):
        path = workbook.with_name(lock)
        if path.is_file() and not path.is_symlink():
            return path
    return None


def read_state(workbook: Path, generation: str) -> dict[str, str | None]:
    """The base of the tables written from the workbook since its generation.

    The values override `_base`; None means the table is absent in the base. A
    missing or unreadable state file, or one of another generation, gives {}.
    """
    try:
        state = json.loads(state_path(workbook).read_bytes())
    except OSError, ValueError:
        return {}
    if not isinstance(state, dict):
        return {}
    files = state.get("files")
    if (
        type(state.get("format")) is not int
        or state["format"] != STATE_FORMAT
        or state.get("generation") != generation
        or not isinstance(files, dict)
        or not all(value is None or isinstance(value, str) for value in files.values())
    ):
        return {}
    return files


def write_state(
    workbook: Path, generation: str, files: Mapping[str, str | None]
) -> None:
    """Write the sync state file of the workbook atomically."""
    atomic_json(
        state_path(workbook),
        {"format": STATE_FORMAT, "generation": generation, "files": dict(files)},
    )


def remove_state(workbook: Path) -> None:
    state_path(workbook).unlink(missing_ok=True)
