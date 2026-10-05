"""Canonical form of study format 2 folders."""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pkdb.cache import atomic_text
from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.columns import Column, ColumnType
from pkdb.studyformat.jsonio import dump_json
from pkdb.studyformat.load import STRUCTURAL, LoadedStudy, LoadedTable, load_study
from pkdb.studyformat.models import canonical_review_json, canonical_study_json
from pkdb.studyformat.tables import (
    REFERENCE_JSON,
    REVIEW_JSON,
    ROOT,
    STUDY_JSON,
    TableSpec,
)
from pkdb.studyformat.text import natural_key, parse_number, render_tsv


@dataclass(frozen=True)
class FileChange:
    file: str
    action: Literal["write", "delete"]


@dataclass
class FormatResult:
    folder: Path
    changes: list[FileChange] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


def subject_order(table: LoadedTable | None) -> dict[str, int]:
    """Depth-first order of the subject tree: `all` first, children by name."""
    if table is None:
        return {}
    # A duplicated name takes its smallest parent so that sorting the rows
    # cannot change the order and formatting stays idempotent.
    parents: dict[str, str] = {}
    for row in table.rows:
        name, parent = row.cells["name"], row.cells["parent"]
        if name and (
            name not in parents or natural_key(parent) < natural_key(parents[name])
        ):
            parents[name] = parent
    children: dict[str, list[str]] = defaultdict(list)
    roots = []
    for name, parent in parents.items():
        if parent and parent in parents and parent != name:
            children[parent].append(name)
        else:
            roots.append(name)
    order: dict[str, int] = {}
    stack = sorted(
        roots, key=lambda name: (name != ROOT, natural_key(name)), reverse=True
    )
    while stack:
        name = stack.pop()
        if name in order:
            continue
        order[name] = len(order)
        stack.extend(sorted(children[name], key=natural_key, reverse=True))
    for name in sorted(parents, key=natural_key):
        order.setdefault(name, len(order))
    return order


def _cell_key(column: Column, text: str, order: dict[str, int]) -> tuple:
    if not text:
        return (0,)
    if column.references == "subjects" and column.type is ColumnType.NAME:
        return (1, order.get(text, len(order)), natural_key(text))
    if column.type is ColumnType.TIME:
        value = parse_number(text)
        return (1, value, ()) if value is not None else (2, 0.0, natural_key(text))
    return (1, natural_key(text))


def _row_key(spec: TableSpec, cells: tuple[str, ...], order: dict[str, int]) -> tuple:
    by_name = dict(zip(spec.names, cells, strict=True))
    if spec.kind == "subjects":
        name = by_name["name"]
        keys: tuple = ((order.get(name, len(order)), natural_key(name)),)
    else:
        keys = tuple(
            _cell_key(spec.column(name), by_name[name], order)
            for name in spec.sort_columns
        )
    return (*keys, "\t".join(cells))


def render_table(
    table: LoadedTable, study_name: str, order: dict[str, int]
) -> str | None:
    spec = table.spec
    rows = []
    for row in table.rows:
        cells = dict(row.cells)
        cells["study"] = study_name
        if spec.per_source:
            cells["source"] = table.source or ""
        rows.append(tuple(cells[name] for name in spec.names))
    if not rows and not spec.required:
        return None
    rows.sort(key=lambda cells: _row_key(spec, cells, order))
    return render_tsv(spec.names, rows)


def planned_files(study: LoadedStudy) -> dict[str, str | None]:
    """Canonical content of every loadable file; None removes an empty table."""
    subjects = study.of_kind("subjects")
    order = subject_order(subjects[0] if subjects else None)
    plan: dict[str, str | None] = {
        table.file: render_table(table, study.name, order) for table in study.tables
    }
    if study.metadata is not None:
        plan[STUDY_JSON] = canonical_study_json(study.metadata)
    if study.review is not None:
        plan[REVIEW_JSON] = canonical_review_json(study.review)
    if study.reference is not None:
        plan[REFERENCE_JSON] = dump_json(study.reference)
    return plan


def format_folder(folder: Path, *, check: bool = False) -> FormatResult:
    folder = Path(folder)
    study = load_study(folder)
    result = FormatResult(
        folder, issues=[issue for issue in study.issues if issue.code in STRUCTURAL]
    )
    for name, text in planned_files(study).items():
        path = folder / name
        if text is None:
            result.changes.append(FileChange(name, "delete"))
            if not check:
                path.unlink()
        elif path.read_bytes() != text.encode("utf-8"):
            result.changes.append(FileChange(name, "write"))
            if not check:
                atomic_text(path, text)
    return result
