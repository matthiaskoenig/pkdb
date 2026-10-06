"""Classify the files of a study format 2 folder."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pkdb.schemas.validation import ValidationIssue
from pkdb.source_files import ignored_source
from pkdb.studyformat.digitize import parse_digitization_file
from pkdb.studyformat.issues import make_issue
from pkdb.studyformat.raw import parse_raw_file
from pkdb.studyformat.tables import (
    JSON_FILES,
    KIND_ORDER,
    REFERENCE_JSON,
    REVIEW_JSON,
    STUDY_JSON,
    TABLES,
    TableSpec,
    parse_table_file,
)
from pkdb.studyformat.text import natural_key
from pkdb.studyformat.workbook.base import SHEET_NAME_LIMIT

DATA_SUFFIXES = frozenset({".tsv", ".json", ".csv", ".xls", ".xlsx"})
# Study names that PK-DB URLs use after a study identifier, such as
# /api/v2/studies/{sid}/publication, so `<substance>/publication` would be ambiguous,
# and the kinds of tables split by source, whose files `<kind>_<source>.tsv`
# would also be the raw tables of a study named like the kind.
RESERVED_NAMES = frozenset(
    {
        "publication",
        "validate",
        *(spec.kind for spec in TABLES.values() if spec.per_source),
    }
)
REQUIRED_FILES = (STUDY_JSON, REFERENCE_JSON, REVIEW_JSON, "subjects.tsv")
TABLE_NAMES = (
    "Table files are subjects.tsv, interventions.tsv, characteristica.tsv or "
    "<kind>_<source>.tsv with kind outputs, timecourses or scatters and a source "
    "such as Tab1, Fig2A or Text. A raw table, the paper table as printed, is "
    "<study>_<source>.tsv with a Tab source, such as Example_Tab2.tsv."
)


@dataclass(frozen=True)
class TableFile:
    """A table file of a study folder; `source` is None for tables not split by source."""

    name: str
    spec: TableSpec
    source: str | None


@dataclass(frozen=True)
class RawFile:
    """A raw extraction file of a study folder and the source it belongs to."""

    name: str
    source: str


@dataclass
class Layout:
    """Files of a study folder by role: tables, attachments and structural issues."""

    folder: Path
    study: str
    substance: str
    files: frozenset[str]
    tables: list[TableFile] = field(default_factory=list)
    raw_tables: list[RawFile] = field(default_factory=list)
    digitizations: list[RawFile] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)


def table_name_issues(tables: Sequence[TableFile | RawFile]) -> list[ValidationIssue]:
    """Issues of table names that cannot be the sheets of one Excel workbook.

    A sheet name has at most 31 characters and Excel compares sheet names
    ignoring case; the tables are in natural order, so the later of two tables
    with equal names is the duplicate.
    """
    issues, seen = [], {}
    for table in tables:
        sheet = table.name.removesuffix(".tsv")
        if len(sheet) > SHEET_NAME_LIMIT:
            issues.append(
                make_issue(
                    "table_name_too_long",
                    f"The table name {sheet!r} has {len(sheet)} characters; "
                    f"Excel limits sheet names to {SHEET_NAME_LIMIT} characters",
                    file=table.name,
                    hint="Rename the file with a shorter source, such as Fig1 or Tab2.",
                )
            )
        if (first := seen.setdefault(sheet.casefold(), table.name)) != table.name:
            issues.append(
                make_issue(
                    "duplicate_table_name",
                    f"The table file {table.name!r} equals {first!r} ignoring "
                    "case; Excel sheet names are case-insensitive",
                    file=table.name,
                    hint="Rename one of the files with a different source.",
                )
            )
    return issues


def scan_folder(folder: Path) -> Layout:
    """Classify the files of a study folder without reading their content."""
    # The study and substance names come from the path, so make it absolute first.
    folder = Path(folder).resolve()
    study = folder.name
    files, tables, raw_tables, digitizations, attachments, issues = (
        set(),
        [],
        [],
        [],
        [],
        [],
    )
    if study in RESERVED_NAMES:
        issues.append(
            make_issue(
                "reserved_name",
                f"A study folder cannot be named {study!r}; PK-DB uses the name in "
                "study URLs, or table files of that kind would be ambiguous",
                hint="Name the folder after the first author and the year, such as Smith2020.",
            )
        )
    for path in sorted(folder.iterdir(), key=lambda item: natural_key(item.name)):
        name = path.name
        if path.is_symlink():
            issues.append(
                make_issue("symlink", "Symbolic links are not accepted", file=name)
            )
            continue
        if path.is_dir():
            if not name.startswith("."):
                issues.append(
                    make_issue(
                        "unknown_directory",
                        f"Unexpected folder {name!r}; a study folder contains files only",
                        file=name,
                    )
                )
            continue
        if ignored_source(Path(name)) or name == f"{study}.xlsx":
            continue
        files.add(name)
        if name in JSON_FILES:
            continue
        if (table := parse_table_file(name)) is not None:
            tables.append(TableFile(name, *table))
            continue
        if (source := parse_raw_file(name, study)) is not None:
            raw_tables.append(RawFile(name, source))
            continue
        if (source := parse_digitization_file(name, study)) is not None:
            digitizations.append(RawFile(name, source))
            continue
        suffix = path.suffix.lower()
        if name.startswith("."):
            if suffix == ".tsv":
                issues.append(
                    make_issue(
                        "legacy_file",
                        f"{name} is a hidden table of study format 1; remove it",
                        file=name,
                    )
                )
            continue
        if suffix in DATA_SUFFIXES:
            hint = (
                TABLE_NAMES
                if suffix == ".tsv"
                else (
                    f"Only {study}.xlsx, the generated workbook, is allowed"
                    if suffix in {".xls", ".xlsx"}
                    else None
                )
            )
            issues.append(
                make_issue(
                    "unknown_file", f"Unknown data file {name!r}", file=name, hint=hint
                )
            )
            continue
        attachments.append(name)
    for required in REQUIRED_FILES:
        if required not in files:
            issues.append(
                make_issue("missing_file", f"{required} is required", file=required)
            )
    tables.sort(
        key=lambda table: (KIND_ORDER[table.spec.kind], natural_key(table.source or ""))
    )
    raw_tables.sort(key=lambda raw: natural_key(raw.source))
    digitizations.sort(key=lambda item: natural_key(item.source))
    issues.extend(table_name_issues([*tables, *raw_tables]))
    return Layout(
        folder,
        study,
        folder.parent.name,
        frozenset(files),
        tables,
        raw_tables,
        digitizations,
        attachments,
        issues,
    )
