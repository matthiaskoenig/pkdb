"""Layer 4: relationships between rows, tables and files."""

import os
import shlex
from collections import defaultdict
from collections.abc import Iterator
from difflib import get_close_matches
from functools import cache
from pathlib import Path

from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.digitize import check_digitizations
from pkdb.studyformat.issues import LISTED, IssueCap, make_issue, row_issue
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
    """Check the relationships between rows, tables and files, such as references."""
    issues: list[ValidationIssue] = []
    for check in (
        _unique_names,
        _references,
        _subject_tree,
        _series,
        _scatter_subjects,
        _duplicates,
        _unused,
        _images,
        check_digitizations,
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
    # The canonical study labels scatter axes <name>_x and <name>_y, so a
    # timecourse label must not take one of these labels.
    axes = {
        f"{row.cells['name']}_{axis}": (row.cells["name"], table.file)
        for table, row in study.rows("scatters")
        if row.cells["name"]
        for axis in ("x", "y")
    }
    conflicts: set[tuple[str, str]] = set()
    for table, row in study.rows("timecourses"):
        label = row.cells["label"]
        if label in axes and (table.file, label) not in conflicts:
            conflicts.add((table.file, label))
            name, file = axes[label]
            yield row_issue(
                table,
                row,
                "duplicate_label",
                f"{label!r} is the label of an axis of scatter {name!r} in {file}; choose another label",
                "label",
            )
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

    @cache
    def suggest(name: str, target: str) -> tuple[str, ...]:
        # A misspelled name often repeats in many rows; match it once.
        return tuple(get_close_matches(name, known[target], n=5, cutoff=0.6))

    for table in study.tables:
        for column in table.spec.columns:
            target = column.references
            if target is None or target in study.broken:
                continue
            names = set(known[target])
            for row in table.rows:
                seen: set[str] = set()
                # A cell of very many names lists the first issues and counts all.
                cap = IssueCap()
                for name in _names(row.values[column.name]):
                    if name in seen and cap.admit("duplicate_reference"):
                        yield row_issue(
                            table,
                            row,
                            "duplicate_reference",
                            f"{name!r} is listed twice",
                            column.name,
                        )
                    seen.add(name)
                    if name not in names and cap.admit("unknown_reference"):
                        yield row_issue(
                            table,
                            row,
                            "unknown_reference",
                            f"{target}.tsv has no row named {name!r}",
                            column.name,
                            actual=name,
                            candidates=suggest(name, target),
                        )
                kinds = {
                    "duplicate_reference": "are listed twice",
                    "unknown_reference": f"are not rows of {target}.tsv",
                }
                for code, total in cap.beyond():
                    yield row_issue(
                        table,
                        row,
                        code,
                        f"{total:,} names of this cell {kinds[code]}; {LISTED}",
                        column.name,
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
        if parent is not None and parent.values["count"] == 1:
            yield row_issue(
                table,
                row,
                "parent_not_group",
                f"{parents[name]!r} has count 1 and is an individual; a parent must be a group",
                "parent",
            )
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


def _scatter_subjects(study: LoadedStudy) -> Issues:
    # The points of a scatter share a group or an individual field, so the
    # subjects of a scatter are all groups or all individuals (count 1). The
    # rows of the rarer kind are reported; on a tie, those that differ from the
    # first row of the scatter.
    counts = {
        row.cells["name"]: row.values["count"] for _, row in study.rows("subjects")
    }
    scatters: dict[str, list[tuple[LoadedTable, Row, bool]]] = defaultdict(list)
    for table, row in study.rows("scatters"):
        name, subject = row.cells["name"], row.cells["subjects"]
        if name and subject in counts:
            scatters[name].append((table, row, counts[subject] == 1))
    kinds = ("a group", "an individual")
    for name, rows in scatters.items():
        individuals = sum(individual for _, _, individual in rows)
        if individuals in (0, len(rows)):
            continue
        usual = (
            rows[0][2] if 2 * individuals == len(rows) else 2 * individuals > len(rows)
        )
        _, reference, _ = next(item for item in rows if item[2] == usual)
        for table, row, individual in rows:
            if individual != usual:
                yield row_issue(
                    table,
                    row,
                    "mixed_scatter_subjects",
                    f"Scatter {name!r} mixes groups and individuals: "
                    f"{row.cells['subjects']!r} is {kinds[individual]}, but "
                    f"{reference.cells['subjects']!r} in line {reference.line} is "
                    f"{kinds[usual]}",
                    "subjects",
                )


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
    for raw in study.raw_tables:
        image = image_file(study.name, raw.source)
        if raw.source not in reported and image not in study.layout.files:
            reported.add(raw.source)
            yield make_issue(
                "missing_image", f"{image} is missing for {raw.file}", file=raw.file
            )
    for digitization in study.digitizations:
        image = image_file(study.name, digitization.source)
        if digitization.source not in reported and image not in study.layout.files:
            reported.add(digitization.source)
            yield make_issue(
                "missing_image",
                f"{image} is missing for {digitization.file}",
                file=digitization.file,
            )


def _shell_path(folder: Path) -> str:
    """The folder as a shell argument, relative to the working directory when possible."""
    try:
        path = os.path.relpath(folder)
    except ValueError:
        path = str(folder)
    # Forward slashes work on every platform and need no quotes.
    return shlex.quote(Path(path).as_posix())


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
        verb = "is" if open_items == 1 else "are"
        yield make_issue(
            "approved_with_open_items",
            f"A study can only be approved when no review item is open; {open_items} {verb} open",
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
            if target.file in table_names:
                # A table that cannot be loaded is reported where it is read.
                continue
            if target.file not in study.layout.files:
                yield make_issue(
                    "unknown_review_target",
                    f"Review item {item.id} targets {target.file}, which is not a file of this study",
                    file=REVIEW_JSON,
                    key=item.id,
                )
            elif target.rows or target.column:
                yield make_issue(
                    "unknown_review_target",
                    f"Review item {item.id} targets rows or a column of {target.file}; rows and column apply only to table files",
                    file=REVIEW_JSON,
                    key=item.id,
                )
            continue
        if target.key is not None:
            yield make_issue(
                "unknown_review_target",
                f"Review item {item.id} targets the key {target.key} of {target.file}; "
                "a key names a part of a file without rows",
                file=REVIEW_JSON,
                key=item.id,
            )
            continue
        columns = [*target.rows, *([target.column] if target.column else [])]
        unknown = [name for name in columns if name not in table.spec.names]
        if unknown:
            yield make_issue(
                "unknown_review_target",
                f"Review item {item.id} targets unknown columns {', '.join(unknown)} of {target.file}",
                file=REVIEW_JSON,
                key=item.id,
            )
            continue
        if target.rows and not table.matching_lines(target.rows):
            yield make_issue(
                "review_target_unmatched",
                f"Review item {item.id} no longer matches a row of {target.file}",
                file=REVIEW_JSON,
                key=item.id,
            )
