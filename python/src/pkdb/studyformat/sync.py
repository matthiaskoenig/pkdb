"""Keep the study workbook and the canonical TSV tables in step (spec 10.3 and 10.6).

Per table file, the engine compares three versions as canonical TSV text: the
base B the workbook was generated from, the workbook content W and the tables T.

- W = T: nothing to do.
- Only the workbook changed (T = B): its content is written to the TSV file.
- Only the tables changed (W = B): the workbook needs the tables.
- Both changed: a line-based three-way merge. Conflicts write nothing, unless
  `keep` resolves them to one side.

Without `_base`, the base is empty: a table on one side only is kept, the union
of both sides, and a table that differs between the sides conflicts as a whole.

After a sync, the workbook content is the common ancestor of its later saves and
of the new tables. The sync state file next to the workbook records it as the
base of every table it changed since its generation and overrides `_base`, so a
workbook saved again while it stays open does not conflict with the first sync.
The workbook is rewritten only when the tables hold content it lacks, or when
it lost its `_base` but holds the tables after the sync, so that it gets its
base back; never while it is open, and never when it was saved during the sync.
`add_table` adds the empty sheet of a new table under the same rules.
"""

from collections.abc import Iterable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, field, replace
from io import BytesIO
from pathlib import Path
from typing import Literal

from pkdb.cache import atomic_bytes, atomic_text
from pkdb.domain.vocabulary import Vocabulary
from pkdb.schemas.validation import StudyValidationError, ValidationIssue
from pkdb.studyformat.formatter import FileChange, render_table, subject_order
from pkdb.studyformat.issues import make_issue
from pkdb.studyformat.load import (
    STRUCTURAL,
    LoadedStudy,
    LoadedTable,
    load_study,
    load_table,
)
from pkdb.studyformat.merge import Conflict, Preference, merge_lines
from pkdb.studyformat.raw import load_raw, parse_raw_file, render_raw
from pkdb.studyformat.tables import (
    KIND_ORDER,
    TABLES,
    TEXT_SOURCE,
    TableSpec,
    image_file,
    parse_table_file,
    table_file,
)
from pkdb.studyformat.text import natural_key
from pkdb.studyformat.workbook.base import (
    SHEET_NAME_LIMIT,
    open_lock,
    read_state,
    remove_state,
    state_path,
    workbook_path,
    write_state,
)
from pkdb.studyformat.workbook.read import WorkbookContent, read_workbook
from pkdb.studyformat.workbook.write import WorkbookError, build_workbook

Side = Literal["workbook", "tables"]
WorkbookAction = Literal[
    "created", "regenerated", "unchanged", "close_to_update", "sync_again"
]

SUBJECTS = table_file("subjects")
# merge_lines merges the workbook as ours and the tables as theirs.
PREFER: dict[Side, Preference] = {
    "workbook": "ours",
    "tables": "theirs",
}
# Ranges of rows an issue message lists; the conflict holds every row.
LISTED_RANGES = 5
KEEP_HINT = (
    "Keep one side with pkdb tables sync --keep workbook or --keep tables, or edit "
    "the workbook so that the conflicting rows equal the tables."
)


@dataclass(frozen=True)
class SyncConflict:
    """Rows of a table that the workbook and the tables changed differently since the last sync.

    `workbook_rows` holds the 1-based sheet rows and `table_lines` the 1-based
    TSV line numbers, each with its canonical text, and `base_lines` the lines
    both sides changed. When one side removed the whole table, its rows are
    empty and the other side lists all of its lines. `kept` is the side that
    resolved the conflict, or None while it is unresolved.
    """

    file: str
    sheet: str
    workbook_rows: tuple[tuple[int, str], ...]
    table_lines: tuple[tuple[int, str], ...]
    base_lines: tuple[str, ...]
    kept: Side | None = None


@dataclass(frozen=True)
class SyncResult:
    """Outcome of a sync, or of its plan in check mode.

    `changes` are the TSV writes and deletes, done or planned when `checked`.
    `workbook_action` is `created` or `regenerated` when the workbook was
    written, `unchanged` when it already held the tables or an issue stopped the
    sync, `close_to_update` when it needs the tables but is open, and
    `sync_again` when it needs the tables but was saved during the sync; the
    next sync merges that save. `lock` is the lock file of the open workbook, if
    one was found.
    """

    folder: Path
    workbook: Path
    changes: tuple[FileChange, ...] = ()
    workbook_action: WorkbookAction = "unchanged"
    lock: Path | None = None
    conflicts: tuple[SyncConflict, ...] = ()
    issues: tuple[ValidationIssue, ...] = ()
    checked: bool = False

    @property
    def ok(self) -> bool:
        """No error issue and no unresolved conflict."""
        return not any(issue.severity == "error" for issue in self.issues) and all(
            conflict.kept is not None for conflict in self.conflicts
        )


@dataclass
class _Plan:
    # The new text of each table file of the workbook and the tables, None to
    # remove it, with the conflicts and the issues found.
    files: dict[str, str | None] = field(default_factory=dict)
    conflicts: list[SyncConflict] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)


def _lines(text: str | None) -> list[str]:
    # str.splitlines would also split at U+0085, U+2028 and U+2029 in cells.
    return text.removesuffix("\n").split("\n") if text else []


def _parsed(file: str) -> tuple[TableSpec, str | None]:
    parsed = parse_table_file(file)
    if parsed is None:
        raise ValueError(f"{file} is not a table file")
    return parsed


def _sheet_order(file: str, study: str) -> tuple:
    # The order of the sheets: the tables not split by source come first, the
    # raw tables last.
    if (parsed := parse_table_file(file)) is not None:
        spec, source = parsed
        return KIND_ORDER[spec.kind], natural_key(source or "")
    if (source := parse_raw_file(file, study)) is not None:
        return len(KIND_ORDER), natural_key(source)
    raise ValueError(f"{file} is not a table file")


def _load(file: str, text: str, study: str) -> LoadedTable:
    spec, source = _parsed(file)
    table, _ = load_table(file, text.encode("utf-8"), spec, source, study=study)
    if table is None:
        # Lines of canonical texts always load, also when merged.
        raise ValueError(f"{file} cannot be read after merging")
    return table


def _blocking(study: LoadedStudy) -> tuple[ValidationIssue, ...]:
    """The issues that keep a table file from loading, so that it cannot be merged.

    Raw tables count as table files. Merging the tables does not need the JSON
    files; pkdb validate reports them.
    """
    return tuple(
        issue
        for issue in study.issues
        if issue.code in STRUCTURAL
        and issue.source is not None
        and (
            parse_table_file(issue.source.file) is not None
            or parse_raw_file(issue.source.file, study.name) is not None
        )
    )


def _canonical(
    file: str, text: str, study: str, order: Mapping[str, int]
) -> str | None:
    """Canonical text of a table with its rows sorted by a subject order.

    None removes an optional table without rows. A raw table keeps its row
    order, and None removes it without cells.
    """
    if (source := parse_raw_file(file, study)) is not None:
        raw, _ = load_raw(file, BytesIO(text.encode("utf-8")), source)
        if raw is None:
            # Lines of canonical texts always load, also when merged.
            raise ValueError(f"{file} cannot be read after merging")
        return render_raw(raw)
    return render_table(_load(file, text, study), study, dict(order))


def _numbers(word: str, numbers: Sequence[int]) -> str:
    """Numbers as ranges, such as `rows 2-4, 9`."""
    ranges: list[list[int]] = []
    for number in numbers:
        if ranges and number == ranges[-1][1] + 1:
            ranges[-1][1] = number
        else:
            ranges.append([number, number])
    parts = [
        str(first) if first == last else f"{first}-{last}" for first, last in ranges
    ]
    if len(parts) > LISTED_RANGES:
        parts = [*parts[:LISTED_RANGES], "..."]
    return f"{word}{'s' if len(numbers) > 1 else ''} {', '.join(parts)}"


def _region_conflict(
    workbook_name: str,
    file: str,
    rows: Sequence[int],
    conflict: Conflict,
    keep: Side | None,
    raw: bool,
) -> tuple[SyncConflict, ValidationIssue | None]:
    """A conflicting region of a merge, and its issue unless `keep` resolved it.

    `rows` are the sheet rows of the canonical workbook lines. The issue is
    located at the first row of the region in the sheet of the workbook, and
    its message names the lines of the TSV file. A side without lines is
    located at the line before the region, or at the header; a raw table has
    no header, so lines removed at its start are before its first line.
    """
    sheet = file.removesuffix(".tsv")
    workbook_rows = tuple(
        (rows[conflict.ours_start + index], line)
        for index, line in enumerate(conflict.ours)
    )
    table_lines = tuple(
        (conflict.theirs_start + index + 1, line)
        for index, line in enumerate(conflict.theirs)
    )
    found = SyncConflict(
        file, sheet, workbook_rows, table_lines, conflict.base, kept=keep
    )
    if keep is not None:
        return found, None
    if workbook_rows:
        row = workbook_rows[0][0]
        in_workbook = _numbers("row", [number for number, _ in workbook_rows])
    elif raw and not conflict.ours_start:
        row = 1
        in_workbook = "rows removed before row 1"
    else:
        row = rows[conflict.ours_start - 1] if conflict.ours_start else 1
        in_workbook = f"rows removed after row {row}"
    if table_lines:
        in_tables = _numbers("line", [number for number, _ in table_lines])
    elif raw and not conflict.theirs_start:
        in_tables = "lines removed before line 1"
    else:
        in_tables = f"lines removed after line {conflict.theirs_start or 1}"
    return found, make_issue(
        "sync_conflict",
        f"The workbook and the tables changed the same rows of {sheet} "
        f"differently since the last sync: {in_workbook} of the sheet, "
        f"{in_tables} of {file}",
        file=workbook_name,
        sheet=sheet,
        line=row,
        hint=KEEP_HINT,
    )


def _removal_conflict(
    workbook_name: str,
    file: str,
    versions: tuple[str | None, str | None, str | None],
    content: WorkbookContent,
    keep: Side | None,
) -> tuple[SyncConflict, ValidationIssue | None]:
    """One side removed a table that the other changed, and its issue unless kept.

    The issue is located at the sheet in the workbook, at its header row while
    the sheet exists.
    """
    workbook, tables, base = versions
    sheet = file.removesuffix(".tsv")
    workbook_rows = (
        ()
        if workbook is None
        else tuple(zip(content.tables[file].rows, _lines(workbook), strict=True))
    )
    found = SyncConflict(
        file,
        sheet,
        workbook_rows,
        tuple(enumerate(_lines(tables), start=1)),
        tuple(_lines(base)),
        kept=keep,
    )
    if keep is not None:
        return found, None
    if workbook is not None:
        message = (
            f"{file} was deleted, but the {sheet} sheet changed since the last sync"
        )
        row = 1
    elif sheet in content.sheets:
        message = (
            f"The {sheet} sheet has no rows left, but {file} changed since the "
            "last sync"
        )
        row = 1
    else:
        message = (
            f"The {sheet} sheet was removed, but {file} changed since the last sync"
        )
        row = None
    return found, make_issue(
        "sync_conflict",
        message,
        file=workbook_name,
        sheet=sheet,
        line=row,
        hint=KEEP_HINT,
    )


def _plan(
    study: str,
    workbook_name: str,
    tables: Mapping[str, str],
    tables_order: Mapping[str, int],
    workbook: Mapping[str, str],
    content: WorkbookContent,
    base: Mapping[str, str],
    keep: Side | None,
) -> _Plan:
    """The new text of every table file, merged from base, workbook and tables.

    A text taken from one side is re-sorted when the new subjects order their
    rows differently, and a merged text is always made canonical. A raw table
    is never re-sorted.
    """
    plan = _Plan()
    subjects = workbook.get(SUBJECTS)
    workbook_order = subject_order(
        None if subjects is None else _load(SUBJECTS, subjects, study)
    )
    order = tables_order
    # The subjects come first: their order sorts the rows of every other table.
    files = sorted(
        workbook.keys() | tables.keys(), key=lambda file: _sheet_order(file, study)
    )
    for file in files:
        raw = parse_raw_file(file, study) is not None
        w, t, b = workbook.get(file), tables.get(file), base.get(file)
        # The subject order of the text, None for a merged text.
        sorted_by: Mapping[str, int] | None
        if w == t or w == b:
            text, sorted_by = t, tables_order
        elif t == b:
            text, sorted_by = w, workbook_order
        elif w is None or t is None:
            # Here b is not None, or the absent side would equal it.
            conflict, issue = _removal_conflict(
                workbook_name, file, (w, t, b), content, keep
            )
            plan.conflicts.append(conflict)
            if issue is not None:
                plan.issues.append(issue)
                continue
            text, sorted_by = (
                (w, workbook_order) if keep == "workbook" else (t, tables_order)
            )
        else:
            merged = merge_lines(
                _lines(b), _lines(w), _lines(t), prefer=PREFER[keep] if keep else None
            )
            rows = content.tables[file].rows
            for region in merged.conflicts:
                conflict, issue = _region_conflict(
                    workbook_name, file, rows, region, keep, raw
                )
                plan.conflicts.append(conflict)
                if issue is not None:
                    plan.issues.append(issue)
            if merged.lines is None:
                continue
            text, sorted_by = "\n".join(merged.lines) + "\n", None
        if file == SUBJECTS:
            if text is None:
                plan.issues.append(
                    make_issue(
                        "missing_file",
                        f"{SUBJECTS} is required; restore it, because the sync "
                        "does not remove the subjects sheet",
                        file=SUBJECTS,
                    )
                )
                continue
            if sorted_by is None:
                # Merged subjects sort by their own order, as on each side.
                table = _load(SUBJECTS, text, study)
                sorted_by = subject_order(table)
                text = render_table(table, study, dict(sorted_by))
            order = sorted_by
        elif raw:
            if text is not None and sorted_by is None:
                text = _canonical(file, text, study, order)
        elif text is not None and sorted_by != order:
            text = _canonical(file, text, study, order)
        plan.files[file] = text
    return plan


def table_texts(study: LoadedStudy) -> dict[str, str]:
    """The canonical text of every table and raw table of a study, if it has rows.

    These are the tables a generated workbook holds.
    """
    order = subject_order(study.table(SUBJECTS))
    return {
        **{
            table.file: text
            for table in study.tables
            if (text := render_table(table, study.name, order)) is not None
        },
        **{
            raw.file: text
            for raw in study.raw_tables
            if (text := render_raw(raw)) is not None
        },
    }


def _remove_state(workbook: Path) -> None:
    # Best effort: read_state ignores the state file of an old generation.
    with suppress(OSError):
        remove_state(workbook)


def _signature(workbook: Path) -> tuple[int, int] | None:
    """Modification time and size of the workbook, None when it is gone."""
    try:
        status = workbook.stat()
    except OSError:
        return None
    return status.st_mtime_ns, status.st_size


def _write_issue(file: str, error: OSError) -> ValidationIssue:
    return make_issue(
        "sync_write_failed", f"{file} cannot be updated: {error}", file=file
    )


def _open_issue(
    workbook: Path, lock: Path | None, *, restore_base: bool = False
) -> ValidationIssue:
    """The workbook is open, so it was not regenerated.

    `restore_base` tells that the regeneration would only restore the lost
    `_base` sheet of a workbook that holds the tables.
    """
    purpose = (
        "restore its base, which the sync needs to merge changes of both sides"
        if restore_base
        else "update it with the changes of the tables"
    )
    if lock is None:
        message = (
            f"{workbook.name} cannot be replaced, probably because it is open in a "
            f"spreadsheet application; close it and sync again to {purpose}"
        )
    else:
        message = (
            f"{workbook.name} is open in a spreadsheet application; close it and "
            f"sync again to {purpose}. If the workbook is not open, delete {lock}"
        )
    hint = (
        "Closing the workbook and syncing again restores its base."
        if restore_base
        else None
    )
    return make_issue("workbook_open", message, file=workbook.name, hint=hint)


def _changes(
    files: Mapping[str, str | None], tables: Mapping[str, str]
) -> list[FileChange]:
    """The TSV deletes and writes of a sync, in the order they are applied.

    The deletes come first. On a case-insensitive file system, as on macOS and
    Windows, a sheet renamed only in case deletes `outputs_Tab2a.tsv` and writes
    `outputs_Tab2A.tsv`, which name the same file there, so a later delete would
    remove the new file. A crash between both leaves the table in the base and
    in the workbook, and the next sync writes it.
    """
    changes = [
        FileChange(file, "delete" if text is None else "write")
        for file, text in files.items()
        if text != tables.get(file)
    ]
    return sorted(changes, key=lambda change: change.action != "delete")


def _write_tables(
    folder: Path, files: Mapping[str, str | None], changes: Sequence[FileChange]
) -> tuple[list[FileChange], ValidationIssue | None]:
    """Apply the changes in order, each atomically, up to the first that fails.

    A file whose name equals a file written before, ignoring case, is never
    deleted, because on a case-insensitive file system that is the new file.
    """
    done: list[FileChange] = []
    written: set[str] = set()
    for change in changes:
        text = files[change.file]
        try:
            if text is None:
                if change.file.casefold() in written:
                    raise ValueError(f"{change.file} is deleted after it was written")
                (folder / change.file).unlink(missing_ok=True)
            else:
                atomic_text(folder / change.file, text)
                written.add(change.file.casefold())
        except OSError as error:
            return done, _write_issue(change.file, error)
        done.append(change)
    return done, None


def _create(
    outcome: SyncResult, tables: Mapping[str, str], vocabulary: Vocabulary
) -> SyncResult:
    """Generate the missing workbook from the tables, unless its lock file exists.

    Excel on Windows replaces the workbook through renames while it saves it,
    so for a moment the workbook is missing while it is open.
    """
    path = outcome.workbook
    if (lock := open_lock(path)) is not None:
        issue = make_issue(
            "workbook_open",
            f"{path.name} is missing, but its lock file shows that a spreadsheet "
            "application has it open, perhaps while it saves it; sync again when "
            f"it is closed. If the workbook is not open, delete {lock}",
            file=path.name,
        )
        return replace(
            outcome, workbook_action="close_to_update", lock=lock, issues=(issue,)
        )
    if outcome.checked:
        return replace(outcome, workbook_action="created")
    try:
        build = build_workbook(tables, vocabulary, study=outcome.folder.name)
    except WorkbookError as error:
        return replace(
            outcome, issues=(make_issue(error.code, error.message, file=path.name),)
        )
    issues = tuple(build.issues)
    if build.data is None:
        return replace(outcome, issues=issues)
    try:
        atomic_bytes(path, build.data)
    except OSError as error:
        return replace(outcome, issues=(*issues, _write_issue(path.name, error)))
    # A state file left by an earlier workbook belongs to another generation.
    _remove_state(path)
    return replace(outcome, workbook_action="created", issues=issues)


@dataclass(frozen=True)
class _Replacement:
    """Outcome of rebuilding and replacing the workbook.

    `status` is `written`, `open` when a lock file or Windows kept the workbook
    from being replaced, `saved` when it was saved since it was read, or
    `failed`, explained by an error in `issues`. `issues` also hold the issues
    of the build. `lock` is the lock file of an open workbook, if one was found.
    """

    status: Literal["written", "open", "saved", "failed"]
    issues: tuple[ValidationIssue, ...] = ()
    lock: Path | None = None


def _empty_sheets(
    content: WorkbookContent, files: Mapping[str, str | None], study: str
) -> list[str]:
    """The sheets that pkdb tables add added and that have no rows yet.

    They stay until they have rows; the sheet of a table that the sync removes goes.
    """
    return [
        name
        for name in content.sheets
        if (
            parse_raw_file(f"{name}.tsv", study) is not None
            or _parsed(f"{name}.tsv")[0].per_source
        )
        and f"{name}.tsv" not in content.tables
        and files.get(f"{name}.tsv") is None
    ]


def _replace_workbook(
    path: Path,
    tables: Mapping[str, str],
    vocabulary: Vocabulary,
    *,
    study: str,
    empty_sheets: Sequence[str],
    signature: tuple[int, int] | None,
) -> _Replacement:
    """Rebuild the workbook from the tables, keeping its scratch sheets, and replace it.

    `signature` is that of the workbook before it was read. A workbook opened or
    saved since then is not replaced, so that no save is lost. The replacement
    is atomic and starts a new generation without sync state file.
    """
    try:
        build = build_workbook(
            tables, vocabulary, study=study, existing=path, empty_sheets=empty_sheets
        )
    except WorkbookError as error:
        issue = make_issue(error.code, error.message, file=path.name)
        return _Replacement("failed", (issue,))
    issues = tuple(build.issues)
    if build.data is None:
        return _Replacement("failed", issues)
    if (lock := open_lock(path)) is not None:
        return _Replacement("open", issues, lock)
    if _signature(path) != signature:
        return _Replacement("saved", issues)
    try:
        atomic_bytes(path, build.data)
    except PermissionError:
        # Windows keeps an open workbook locked.
        return _Replacement("open", issues)
    except OSError as error:
        return _Replacement("failed", (*issues, _write_issue(path.name, error)))
    _remove_state(path)
    return _Replacement("written", issues)


def _regenerate(
    outcome: SyncResult,
    files: Mapping[str, str | None],
    content: WorkbookContent,
    signature: tuple[int, int] | None,
    vocabulary: Vocabulary,
    *,
    restore_base: bool,
) -> SyncResult:
    """Rewrite the workbook from the new tables, unless it is open or was saved meanwhile.

    A save during the sync is merged by the next sync. `restore_base` tells
    that the workbook holds the tables and only gets its base back.
    """
    path = outcome.workbook
    study = outcome.folder.name
    replaced = _replace_workbook(
        path,
        {file: text for file, text in files.items() if text is not None},
        vocabulary,
        study=study,
        empty_sheets=_empty_sheets(content, files, study),
        signature=signature,
    )
    issues = (*outcome.issues, *replaced.issues)
    if replaced.status == "open":
        return replace(
            outcome,
            workbook_action="close_to_update",
            lock=replaced.lock or outcome.lock,
            issues=(
                *issues,
                _open_issue(path, replaced.lock, restore_base=restore_base),
            ),
        )
    if replaced.status == "saved":
        changed = make_issue(
            "workbook_changed",
            f"{path.name} was saved during the sync, so it was not updated with "
            "the changes of the tables; sync again",
            file=path.name,
        )
        return replace(outcome, workbook_action="sync_again", issues=(*issues, changed))
    if replaced.status == "failed":
        return replace(outcome, issues=issues)
    return replace(outcome, workbook_action="regenerated", issues=issues)


def sync_study(
    folder: Path,
    vocabulary: Vocabulary,
    *,
    keep: Side | None = None,
    check: bool = False,
    max_rows: int | None = None,
) -> SyncResult:
    """Sync the workbook of a study folder with its TSV tables.

    Without a workbook, it is generated from the tables. Otherwise the changes
    of the workbook are written to the TSV files in canonical form, and the
    workbook is regenerated when the tables hold content it lacks, unless it is
    open. Changes on both sides merge line by line, and `keep` resolves
    conflicting rows to one side. Without `_base`, a table on one side only is
    kept, and a table that differs between the sides conflicts; a workbook
    without `_base` that holds the tables after the sync is regenerated to get
    it back. An error, or a
    conflict left unresolved, writes nothing; every file is replaced
    atomically. `check` only plans.
    `max_rows` limits the data rows of the tables and of the workbook, as an
    upload does.
    """
    if keep is not None and keep not in PREFER:
        raise ValueError(f"keep must be 'workbook', 'tables' or None, not {keep!r}")
    folder = Path(folder).resolve()
    path = workbook_path(folder)
    outcome = SyncResult(folder, path, checked=check)
    try:
        study = load_study(folder, max_rows=max_rows)
    except StudyValidationError as error:
        return replace(outcome, issues=tuple(error.report.issues))
    # The tables must load to be merged.
    if blocking := _blocking(study):
        return replace(outcome, issues=blocking)
    order = subject_order(study.table(SUBJECTS))
    tables = table_texts(study)
    if not path.exists():
        return _create(outcome, tables, vocabulary)

    # A save during the sync must not be overwritten by the regeneration.
    signature = _signature(path)
    try:
        content = read_workbook(path, study.name, max_rows=max_rows)
    except StudyValidationError as error:
        return replace(outcome, issues=tuple(error.report.issues))
    if not content.ok:
        return replace(outcome, issues=tuple(content.issues))
    base: dict[str, str] = {}
    state: dict[str, str | None] = {}
    if content.base is not None:
        base = dict(content.base.files)
        state = read_state(path, content.base.generation)
        for file, text in state.items():
            if text is None:
                base.pop(file, None)
            else:
                base[file] = text

    workbook = {file: sheet.text for file, sheet in content.tables.items()}
    plan = _plan(study.name, path.name, tables, order, workbook, content, base, keep)
    outcome = replace(
        outcome,
        conflicts=tuple(plan.conflicts),
        issues=(*content.issues, *plan.issues),
    )
    if not outcome.ok:
        return outcome
    changes = _changes(plan.files, tables)
    if not check:
        done, failure = _write_tables(folder, plan.files, changes)
        # The workbook content is the common ancestor of its later saves and of
        # the new tables, whether they took it, merged it or kept the tables.
        # This includes a table only the base holds, which both sides removed.
        # A table whose write failed keeps its base, so the sync is retried.
        pending = {change.file for change in changes[len(done) :]}
        recorded = {
            file: workbook.get(file)
            for file in plan.files.keys() | base.keys()
            if file not in pending and workbook.get(file) != base.get(file)
        }
        if content.base is not None and recorded:
            try:
                write_state(path, content.base.generation, {**state, **recorded})
            except OSError as error:
                failure = failure or _write_issue(state_path(path).name, error)
        if failure is not None:
            return replace(
                outcome, changes=tuple(done), issues=(*outcome.issues, failure)
            )
    lock = open_lock(path)
    outcome = replace(outcome, changes=tuple(changes), lock=lock)
    # A workbook that holds the new tables is regenerated only to get back a
    # lost base, without which every later change of both sides conflicts.
    restore_base = all(text == workbook.get(file) for file, text in plan.files.items())
    if restore_base and content.base is not None:
        return outcome
    if lock is not None:
        return replace(
            outcome,
            workbook_action="close_to_update",
            issues=(
                *outcome.issues,
                _open_issue(path, lock, restore_base=restore_base),
            ),
        )
    if check:
        return replace(outcome, workbook_action="regenerated")
    return _regenerate(
        outcome, plan.files, content, signature, vocabulary, restore_base=restore_base
    )


@dataclass(frozen=True)
class AddTableResult:
    """Outcome of adding the empty sheet of a new table to the workbook.

    `sync` is the sync that runs first, None when the table name was rejected
    before. `issues` are the problems of adding the sheet, and a warning when
    the image of its source is missing. `ok` means the sheet was added.
    """

    table: str
    sync: SyncResult | None
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def ok(self) -> bool:
        """The sync was ok and the sheet was added."""
        return (
            self.sync is not None
            and self.sync.ok
            and not any(issue.severity == "error" for issue in self.issues)
        )


def _new_table_source(table: str, study: str) -> str | None:
    """The source of the sheet of a new table or raw table of a study, or None."""
    parsed = parse_table_file(f"{table}.tsv")
    if parsed is not None:
        return parsed[1] if parsed[0].per_source else None
    return parse_raw_file(f"{table}.tsv", study)


def _table_name_issue(table: str, study: str) -> ValidationIssue | None:
    """Why a name cannot be the sheet of a new table or raw table, or None."""
    if _new_table_source(table, study) is None:
        *kinds, last = [kind for kind, spec in TABLES.items() if spec.per_source]
        return make_issue(
            "invalid_table_name",
            f"{table!r} is not a table name <kind>_<source> with the kind "
            f"{', '.join(kinds)} or {last} and a source such as Tab3, Fig2A or "
            f"Text, or the name {study}_<source> of a raw table with a source "
            "such as Tab3",
        )
    if len(table) > SHEET_NAME_LIMIT:
        return make_issue(
            "table_name_too_long",
            f"{table!r} has {len(table)} characters; Excel limits sheet names to "
            f"{SHEET_NAME_LIMIT} characters",
        )
    return None


def _same_name(name: str, names: Iterable[str]) -> str | None:
    """The name among `names` equal to `name` ignoring case, as Excel compares sheets."""
    return next((other for other in names if other.casefold() == name.casefold()), None)


def _add_open_issue(workbook: Path, table: str, lock: Path | None) -> ValidationIssue:
    return make_issue(
        "workbook_open",
        f"{workbook.name} is open in a spreadsheet application. Close the workbook "
        "first, or copy a sheet in the spreadsheet application and rename it to "
        f"{table}",
        file=workbook.name,
        severity="error",
        hint=None if lock is None else f"If the workbook is not open, delete {lock}",
    )


def add_table(
    folder: Path,
    vocabulary: Vocabulary,
    table: str,
    *,
    max_rows: int | None = None,
) -> AddTableResult:
    """Add the empty sheet of a new `<kind>_<source>` table, such as outputs_Tab3.

    The name must be a table split by source, or a raw table
    `<study>_<source>` such as Example_Tab3, at most 31 characters long, and
    new as a TSV file and as a sheet, ignoring case as Excel does. The workbook
    and the tables are synced first, creating the workbook if needed. The
    workbook is then rebuilt from the tables with the new sheet and the empty
    sheets added before, unless it is open or was saved meanwhile. The TSV file
    is written when the sheet has a row and the workbook is synced.
    """
    folder = Path(folder).resolve()
    path = workbook_path(folder)
    if (issue := _table_name_issue(table, folder.name)) is not None:
        return AddTableResult(table, None, (issue,))
    try:
        names = [entry.name for entry in folder.iterdir()]
    except OSError:
        # The sync reports a folder it cannot read.
        names = []
    if (existing := _same_name(f"{table}.tsv", names)) is not None:
        issue = make_issue("table_exists", f"{existing} already exists", file=existing)
        return AddTableResult(table, None, (issue,))
    synced = sync_study(folder, vocabulary, max_rows=max_rows)

    def refused(issue: ValidationIssue) -> AddTableResult:
        return AddTableResult(table, synced, (issue,))

    if not synced.ok:
        return AddTableResult(table, synced)
    lock = synced.lock or open_lock(path)
    if lock is not None or synced.workbook_action == "close_to_update":
        return refused(_add_open_issue(path, table, lock))
    # The workbook is rebuilt from the tables, so it must hold just them.
    signature = _signature(path)
    try:
        study = load_study(folder, max_rows=max_rows)
        content = read_workbook(path, study.name, max_rows=max_rows)
    except StudyValidationError as error:
        return AddTableResult(table, synced, tuple(error.report.issues))
    blocking = _blocking(study)
    if blocking or not content.ok:
        return AddTableResult(table, synced, (*blocking, *content.issues))
    tables = table_texts(study)
    if (
        synced.workbook_action == "sync_again"
        or {file: sheet.text for file, sheet in content.tables.items()} != tables
    ):
        return refused(
            make_issue(
                "workbook_changed",
                "The workbook or the tables changed during the sync; sync again "
                f"and then add {table}",
                file=path.name,
                severity="error",
            )
        )
    if (sheet := _same_name(table, content.sheets)) is not None:
        return refused(
            make_issue(
                "table_exists",
                f"The sheet {sheet} already exists in {path.name}",
                file=path.name,
                sheet=sheet,
            )
        )
    replaced = _replace_workbook(
        path,
        tables,
        vocabulary,
        study=study.name,
        empty_sheets=[*_empty_sheets(content, tables, study.name), table],
        signature=signature,
    )
    if replaced.status == "open":
        return refused(_add_open_issue(path, table, replaced.lock))
    if replaced.status == "saved":
        return refused(
            make_issue(
                "workbook_changed",
                f"{path.name} was saved while {table} was added; add it again",
                file=path.name,
                severity="error",
            )
        )
    issues = replaced.issues
    source = _new_table_source(table, study.name)
    if replaced.status == "written" and source is not None:
        image = image_file(study.name, source)
        if source != TEXT_SOURCE and not (folder / image).exists():
            missing = make_issue(
                "missing_image",
                f"{image} is missing; validation needs the image of {source} in "
                "the study folder",
                severity="warning",
            )
            issues = (*issues, missing)
    return AddTableResult(table, synced, issues)


def workbook_check(folder: Path, vocabulary: Vocabulary) -> dict | None:
    """Plan the sync of a folder without writing, as pkdb validate and prepare report it.

    None when the folder has no workbook. Planned TSV `changes` and `conflicts`
    are workbook changes that are not in the tables yet. `ok` is False when the
    workbook cannot be synced, and None when the tables do not load, so the
    workbook could not be compared with them; validation reports the tables.
    """
    folder = Path(folder).resolve()
    if not workbook_path(folder).exists():
        return None
    result = sync_study(folder, vocabulary, check=True)
    ok: bool | None = result.ok
    if not ok and not result.conflicts and _blocking(load_study(folder)):
        ok = None
    return {
        "action": result.workbook_action,
        "changes": [
            {"file": change.file, "action": change.action} for change in result.changes
        ],
        "conflicts": len(result.conflicts),
        "ok": ok,
    }
