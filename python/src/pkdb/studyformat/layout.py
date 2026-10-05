"""Classify the files of a study format 2 folder."""

from dataclasses import dataclass, field
from pathlib import Path

from pkdb.schemas.validation import ValidationIssue
from pkdb.source_files import ignored_source
from pkdb.studyformat.issues import make_issue
from pkdb.studyformat.tables import (
    JSON_FILES,
    KIND_ORDER,
    REFERENCE_JSON,
    REVIEW_JSON,
    STUDY_JSON,
    TableSpec,
    parse_table_file,
)
from pkdb.studyformat.text import natural_key

DATA_SUFFIXES = frozenset({".tsv", ".json", ".csv", ".xls", ".xlsx"})
REQUIRED_FILES = (STUDY_JSON, REFERENCE_JSON, REVIEW_JSON, "subjects.tsv")
TABLE_NAMES = (
    "Table files are subjects.tsv, interventions.tsv, characteristica.tsv or "
    "<kind>_<source>.tsv with kind outputs, timecourses or scatters and a source "
    "such as Tab1, Fig2A or Text."
)


@dataclass(frozen=True)
class TableFile:
    name: str
    spec: TableSpec
    source: str | None


@dataclass
class Layout:
    folder: Path
    study: str
    substance: str
    files: frozenset[str]
    tables: list[TableFile] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)


def scan_folder(folder: Path) -> Layout:
    folder = Path(folder)
    study = folder.name
    files, tables, attachments, issues = set(), [], [], []
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
    return Layout(
        folder, study, folder.parent.name, frozenset(files), tables, attachments, issues
    )
