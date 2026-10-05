"""Layer 4: relationships between rows, tables and files."""

import os
import shlex
from collections import defaultdict
from collections.abc import Iterator
from difflib import get_close_matches
from pathlib import Path

from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.issues import make_issue, row_issue
from pkdb.studyformat.load import LoadedStudy, LoadedTable, Row
from pkdb.studyformat.tables import (
    REFERENCE_JSON,
    REVIEW_JSON,
    ROOT,
    STUDY_JSON,
    TEXT_SOURCE,
    image_file,
)

SERIES_COLUMNS = (
    "subjects",
    "interventions",
    "measurement",
    "calculation",
    "substance",
    "tissue",
    "method",
)
_CHARACTERISTICA_KEY = (
    "subjects",
    "measurement",
    "calculation",
    "substance",
    "tissue",
    "method",
    "choice",
    "time",
    "time_unit",
)
OBSERVATION_KEYS = {
    "characteristica": _CHARACTERISTICA_KEY,
    "outputs": (*_CHARACTERISTICA_KEY, "interventions"),
    "scatters": ("name", "subjects"),
}
DATA_KINDS = frozenset({"characteristica", "outputs", "timecourses", "scatters"})
Issues = Iterator[ValidationIssue]


def check_relations(study: LoadedStudy) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for check in (
        _unique_names,
        _references,
        _subject_tree,
        _series,
        _duplicates,
        _unused,
        _images,
        _study_rules,
        _review_rules,
    ):
        issues.extend(check(study))
    return issues


def _names(value: object) -> tuple[str, ...]:
    if isinstance(value, tuple):
        return value
    return (value,) if isinstance(value, str) and value else ()


def _unique_names(study: LoadedStudy) -> Issues:
    for kind in ("subjects", "interventions"):
        seen: dict[str, int] = {}
        for table, row in study.rows(kind):
            name = row.cells["name"]
            if not name:
                continue
            if name in seen:
                yield row_issue(
                    table,
                    row,
                    "duplicate_name",
                    f"{name!r} is already defined in line {seen[name]}",
                    "name",
                )
            else:
                seen[name] = row.line
    for kind, column, code in (
        ("timecourses", "label", "duplicate_label"),
        ("scatters", "name", "duplicate_name"),
    ):
        owner: dict[str, str] = {}
        reported: set[tuple[str, str]] = set()
        for table, row in study.rows(kind):
            value = row.cells[column]
            if not value:
                continue
            first = owner.setdefault(value, table.file)
            if first != table.file and (table.file, value) not in reported:
                reported.add((table.file, value))
                yield row_issue(
                    table,
                    row,
                    code,
                    f"{value!r} is also used in {first}; {column}s are unique across the study",
                    column,
                )


def _references(study: LoadedStudy) -> Issues:
    known = {
        kind: sorted(
            {row.cells["name"] for _, row in study.rows(kind) if row.cells["name"]}
        )
        for kind in ("subjects", "interventions")
    }
    for table in study.tables:
        for column in table.spec.columns:
            target = column.references
            if target is None or target in study.broken:
                continue
            names = set(known[target])
            for row in table.rows:
                seen: set[str] = set()
                for name in _names(row.values[column.name]):
                    if name in seen:
                        yield row_issue(
                            table,
                            row,
                            "duplicate_reference",
                            f"{name!r} is listed twice",
                            column.name,
                        )
                    seen.add(name)
                    if name not in names:
                        yield row_issue(
                            table,
                            row,
                            "unknown_reference",
                            f"{target}.tsv has no row named {name!r}",
                            column.name,
                            actual=name,
                            candidates=get_close_matches(
                                name, known[target], n=5, cutoff=0.6
                            ),
                        )


def _subject_tree(study: LoadedStudy) -> Issues:
    tables = study.of_kind("subjects")
    if not tables:
        return
    table = tables[0]
    rows: dict[str, Row] = {}
    for row in table.rows:
        if row.cells["name"]:
            rows.setdefault(row.cells["name"], row)
    if ROOT not in rows:
        yield make_issue(
            "missing_root",
            "subjects.tsv needs the root group 'all'",
            file=table.file,
        )
    parents = {name: row.cells["parent"] for name, row in rows.items()}
    for name, row in rows.items():
        if name == ROOT and parents[name]:
            yield row_issue(
                table,
                row,
                "root_parent",
                "The root group 'all' has no parent",
                "parent",
            )
        elif name != ROOT and not parents[name]:
            yield row_issue(
                table, row, "missing_parent", f"{name!r} needs a parent group", "parent"
            )
    done: set[str] = set()
    for start in parents:
        path: list[str] = []
        position: dict[str, int] = {}
        current = start
        while current in parents and current not in done:
            if current in position:
                for member in path[position[current] :]:
                    yield row_issue(
                        table,
                        rows[member],
                        "subject_cycle",
                        f"{member!r} is its own ancestor",
                        "parent",
                    )
                break
            position[current] = len(path)
            path.append(current)
            current = parents[current]
        done.update(path)
    for name, row in rows.items():
        parent = rows.get(parents[name])
        child_count = row.values["count"]
        parent_count = parent.values["count"] if parent else None
        if (
            isinstance(child_count, int)
            and isinstance(parent_count, int)
            and child_count > parent_count
        ):
            yield row_issue(
                table,
                row,
                "subject_count_exceeds_parent",
                f"count {child_count} exceeds the count {parent_count} of {parents[name]!r}",
                "count",
            )


def _series(study: LoadedStudy) -> Issues:
    for table in study.of_kind("timecourses"):
        series: dict[str, list[Row]] = defaultdict(list)
        for row in table.rows:
            if row.cells["label"]:
                series[row.cells["label"]].append(row)
        for label, rows in series.items():
            first = rows[0]
            times: dict[tuple[float, str], int] = {}
            for row in rows:
                if row is not first:
                    for name in SERIES_COLUMNS:
                        if row.cells[name] != first.cells[name]:
                            yield row_issue(
                                table,
                                row,
                                "inconsistent_series",
                                f"Series {label!r} has {name} {first.cells[name]!r} in line {first.line}",
                                name,
                            )
                time = row.values["time"]
                if isinstance(time, float):
                    key = (time, row.cells["time_unit"])
                    if key in times:
                        yield row_issue(
                            table,
                            row,
                            "duplicate_time",
                            f"Time {row.cells['time']} appears twice in series {label!r} (line {times[key]})",
                            "time",
                        )
                    else:
                        times[key] = row.line


def _duplicates(study: LoadedStudy) -> Issues:
    for table in study.tables:
        if table.kind not in DATA_KINDS:
            continue
        content_names = [
            column.name
            for column in table.spec.columns
            if not column.owned and column.name not in {"study", "comment"}
        ]
        keys = OBSERVATION_KEYS.get(table.kind)
        rows_seen: dict[tuple[str, ...], int] = {}
        keys_seen: dict[tuple[str, ...], int] = {}
        for row in table.rows:
            content = tuple(row.cells[name] for name in content_names)
            if content in rows_seen:
                yield row_issue(
                    table,
                    row,
                    "duplicate_row",
                    f"Row repeats line {rows_seen[content]}",
                )
                continue
            rows_seen[content] = row.line
            if keys:
                key = tuple(row.cells[name] for name in keys)
                if key in keys_seen:
                    yield row_issue(
                        table,
                        row,
                        "duplicate_observation",
                        f"Line {keys_seen[key]} describes the same observation with other values",
                    )
                else:
                    keys_seen[key] = row.line


def _unused(study: LoadedStudy) -> Issues:
    if study.broken:
        return
    used: dict[str, set[str]] = {"subjects": set(), "interventions": set()}
    for table in study.tables:
        for column in table.spec.columns:
            if column.references:
                for row in table.rows:
                    used[column.references].update(_names(row.values[column.name]))
    for kind, code in (
        ("subjects", "unused_subject"),
        ("interventions", "unused_intervention"),
    ):
        for table, row in study.rows(kind):
            name = row.cells["name"]
            if name and name not in used[kind]:
                yield row_issue(
                    table, row, code, f"{name!r} is not referenced by any row", "name"
                )


def _images(study: LoadedStudy) -> Issues:
    reported: set[str] = set()
    for table in study.tables:
        entries: list[tuple[str | None, Row | None]] = []
        if table.spec.per_source:
            entries.append((table.source, None))
        else:
            for row in table.rows:
                source = row.values.get("source")
                if isinstance(source, str):
                    entries.append((source, row))
        for source, row in entries:
            if not source or source == TEXT_SOURCE or source in reported:
                continue
            image = image_file(study.name, source)
            if image in study.layout.files:
                continue
            reported.add(source)
            if row is None:
                yield make_issue(
                    "missing_image",
                    f"{image} is missing for {table.file}",
                    file=table.file,
                )
            else:
                yield row_issue(
                    table,
                    row,
                    "missing_image",
                    f"{image} is missing for source {source}",
                    "source",
                )


def _shell_path(folder: Path) -> str:
    """The folder as a shell argument, relative to the working directory when possible."""
    try:
        path = os.path.relpath(folder)
    except ValueError:
        path = str(folder)
    return shlex.quote(path)


def _study_rules(study: LoadedStudy) -> Issues:
    metadata = study.metadata
    if metadata is None:
        return
    if metadata.access == "public" and metadata.release is None:
        yield make_issue(
            "public_requires_release",
            "Only released studies can be public; set access to private or release the study",
            file=STUDY_JSON,
            field="access",
        )
    if study.reference is None or metadata.reference is None:
        return
    command = f"pkdb reference resolve {_shell_path(study.folder)} --write"
    for name, expected in (
        ("pmid", metadata.reference.pmid),
        ("doi", metadata.reference.doi),
    ):
        if expected is None:
            continue
        actual = study.reference.get(name)
        found = "" if actual is None else str(actual)
        same = found.lower() == expected.lower() if name == "doi" else found == expected
        if not same:
            yield make_issue(
                "reference_mismatch",
                f"study.json names {name} {expected} but reference.json has {found or 'none'}; run {command} to refresh reference.json",
                file=REFERENCE_JSON,
                field=name,
            )


def _review_rules(study: LoadedStudy) -> Issues:
    review = study.review
    if review is None:
        return
    open_items = sum(item.state == "open" for item in review.items)
    if review.status == "approved" and open_items:
        yield make_issue(
            "approved_with_open_items",
            f"An approved study has no open review items; {open_items} are open",
            file=REVIEW_JSON,
            field="status",
        )
    table_names = {table_file.name for table_file in study.layout.tables}
    for item in review.items:
        target = item.target
        if target is None or target.file is None:
            continue
        table: LoadedTable | None = study.table(target.file)
        if table is None:
            plain = target.file in study.layout.files and target.file not in table_names
            if (plain and not target.rows and not target.column) or (
                target.file in table_names
            ):
                continue
            yield make_issue(
                "unknown_review_target",
                f"Review item {item.id} targets {target.file}, which is not a file of this study",
                file=REVIEW_JSON,
            )
            continue
        columns = [*target.rows, *([target.column] if target.column else [])]
        unknown = [name for name in columns if name not in table.spec.names]
        if unknown:
            yield make_issue(
                "unknown_review_target",
                f"Review item {item.id} targets unknown columns {', '.join(unknown)} of {target.file}",
                file=REVIEW_JSON,
            )
            continue
        if target.rows and not any(
            all(row.cells[key] == value for key, value in target.rows.items())
            for row in table.rows
        ):
            yield make_issue(
                "review_target_unmatched",
                f"Review item {item.id} no longer matches a row of {target.file}",
                file=REVIEW_JSON,
            )
