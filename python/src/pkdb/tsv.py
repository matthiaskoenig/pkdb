"""Hidden TSV tables generated from a study's Excel workbook.

Each non-empty ``Tab*`` or ``Fig*`` sheet of ``<Study>/<Study>.xlsx`` is written to
``.<Study>_<Sheet>.tsv`` in the same format as the legacy upload: the description
row is skipped, ``#`` starts a comment, unnamed columns and empty rows are dropped,
and missing values are written as ``NA``. Validation reads the workbook itself; the
TSV files keep a reviewable text copy of each table next to it.
"""

import os
import warnings
from glob import escape
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd

from pkdb.studyformat.validation import is_v2_folder

SHEET_PREFIXES = ("Tab", "Fig")


class WorkbookError(ValueError):
    """The study workbook cannot be read."""


def _tables(workbook: Path) -> dict[str, str]:
    try:
        with warnings.catch_warnings():
            # openpyxl warns about unsupported Excel features such as data validation.
            warnings.simplefilter("ignore")
            sheets = pd.read_excel(
                workbook, sheet_name=None, skiprows=[0], comment="#", engine="openpyxl"
            )
    except Exception as error:
        raise WorkbookError(f"Cannot read {workbook.name}: {error}") from error
    tables = {}
    for name, frame in sheets.items():
        if not name.startswith(SHEET_PREFIXES) or frame.empty:
            continue
        frame = frame[[c for c in frame.columns if "Unnamed:" not in str(c)]]
        frame = frame.dropna(axis=0, how="all")
        tables[f".{workbook.stem}_{name}.tsv"] = frame.to_csv(
            sep="\t", index=False, na_rep="NA"
        )
    return tables


def _write(path: Path, text: str) -> None:
    # The temporary name is ignored by source scanning, so watchers never see it.
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        prefix=".",
        suffix=".swp",
        delete=False,
    ) as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    Path(handle.name).replace(path)


def sync_tsvs(folder: str | Path) -> str | None:
    """Write changed TSV tables and remove orphaned ones; describe the change.

    Study format 2 folders are left alone: their tables are the TSV files, and
    their workbook is a generated working copy.
    """
    folder = Path(folder)
    workbook = folder / f"{folder.name}.xlsx"
    if not workbook.is_file() or workbook.is_symlink() or is_v2_folder(folder):
        return None
    tables = _tables(workbook)
    study = folder / "study.json"
    referenced = study.read_text(encoding="utf-8") if study.is_file() else ""
    created = updated = removed = 0
    for name, text in tables.items():
        path = folder / name
        if path.is_file() and path.read_bytes() == text.encode("utf-8"):
            continue
        exists = path.exists()
        _write(path, text)
        updated += exists
        created += not exists
    prefix = f".{folder.name}_"
    for path in folder.glob(f"{escape(prefix)}*.tsv"):
        # A table study.json still uses (by file or sheet name) may be the last copy
        # of a deleted sheet; keep it so validation reports the missing sheet.
        sheet = path.name.removeprefix(prefix).removesuffix(".tsv")
        used = f'"{path.name}"' in referenced or f'"{sheet}"' in referenced
        if path.name not in tables and not used:
            path.unlink()
            removed += 1
    parts = [
        f"{verb} {count}"
        for verb, count in (
            ("created", created),
            ("updated", updated),
            ("removed", removed),
        )
        if count
    ]
    if not parts:
        return None
    joined = parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} and {parts[-1]}"
    return f"{joined[0].upper()}{joined[1:]} TSV files from {workbook.name}"
