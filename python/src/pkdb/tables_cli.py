"""The pkdb tables commands: edit the tables of study format 2 folders in a workbook.

`sync` keeps the generated workbook `<name>.xlsx` and the TSV tables of a study
in step, `open` syncs and opens the workbook, and `add` adds the empty sheet of
a new `<kind>_<source>` table. The TSV tables are the files to commit; git
should ignore the workbook and its sync state file.
"""

import json
import os
import shutil
import subprocess
import sys
from contextlib import suppress
from pathlib import Path

from pkdb.studyformat_cli import print_issues, say

# The .gitignore lines for the workbook and for its sync state file.
GITIGNORE_WORKBOOK = "*.xlsx"
GITIGNORE_STATE = ".*.pkdb-base"
# Rows of each side of a conflict printed for people; JSON lists every row.
LISTED_ROWS = 10
# A file change and the workbook action in plain words: done, and planned (--check).
CHANGES = {"write": ("wrote", "would write"), "delete": ("removed", "would remove")}
WORKBOOK_ACTIONS = {
    "created": ("created", "would be created"),
    "regenerated": ("updated with the tables", "would be updated with the tables"),
    "unchanged": ("unchanged", "unchanged"),
    # The warning issue that comes with these says what to do.
    "close_to_update": (
        "not updated because it is open",
        "would be updated with the tables, but it is open",
    ),
    "sync_again": (
        "not updated because it was saved during the sync",
        "not updated because it was saved during the sync",
    ),
}
CLOSE_FIRST = (
    "Close the workbook first, or copy a sheet in the spreadsheet application "
    "and rename it to {table}"
)


def _vocabulary_options(command) -> None:
    """The options of pkdb validate that choose the vocabulary of the dropdowns."""
    command.add_argument(
        "--vocabulary", type=Path, help="Pinned vocabulary snapshot JSON"
    )
    command.add_argument(
        "--endpoint",
        default=os.environ.get("PKDB_ENDPOINT"),
        help="Use the cached vocabulary of this server (default: PKDB_ENDPOINT)",
    )
    command.add_argument("--cache-dir", type=Path)
    command.add_argument(
        "--offline",
        action="store_true",
        help="Never contact the server; tables commands only use cached vocabulary",
    )


def register(commands) -> None:
    """Add the `tables` command with its actions open, sync and add."""
    tables = commands.add_parser(
        "tables",
        help="Edit the tables of study format 2 folders in a workbook",
        description=(
            "Edit the TSV tables of study format 2 folders in a generated workbook "
            "<name>.xlsx. The sync writes workbook changes to the tables and "
            "updates the workbook with changes of the tables."
        ),
    )
    actions = tables.add_subparsers(dest="action", required=True)
    open_ = actions.add_parser(
        "open",
        help="Sync the workbook of a study and open it",
        description=(
            "Sync the workbook of a study, creating it if needed, and open it in "
            "the default spreadsheet application."
        ),
    )
    open_.add_argument("study", type=Path, help="Study folder")
    open_.add_argument(
        "--no-open", action="store_true", help="Only sync, without opening"
    )
    _vocabulary_options(open_)
    sync = actions.add_parser(
        "sync",
        help="Sync the workbooks and the TSV tables of study folders",
        description=(
            "Sync the workbook and the TSV tables of every study format 2 folder "
            "under PATH with a three-way merge, and create missing workbooks."
        ),
    )
    sync.add_argument("folder", type=Path, help="Study folder or parent directory")
    sync.add_argument(
        "--keep",
        choices=("workbook", "tables"),
        help="Resolve conflicting rows to the workbook or to the tables",
    )
    sync.add_argument(
        "--check",
        action="store_true",
        help="Only report the planned changes; exit with 1 if there are any",
    )
    sync.add_argument(
        "--format",
        dest="output",
        choices=("human", "json"),
        help="Output format (default: human on a terminal, otherwise json)",
    )
    _vocabulary_options(sync)
    add = actions.add_parser(
        "add",
        help="Add the empty sheet of a new table to the workbook",
        description=(
            "Add an empty sheet with the header of a <kind>_<source> table, such "
            "as outputs_Tab3. Its TSV file is written when the sheet has a row "
            "and the workbook is synced."
        ),
    )
    add.add_argument("study", type=Path, help="Study folder")
    add.add_argument("table", help="Table name <kind>_<source>, such as outputs_Tab3")
    _vocabulary_options(add)


def run(args) -> int:
    """Run a `tables` action and return the exit code."""
    actions = {"open": _open, "sync": _sync, "add": _add}
    return actions[args.action](args)


def ignored_by_git(path: Path) -> bool | None:
    """Whether git ignores a path; None when git is missing or the path is outside a work tree."""
    git = shutil.which("git")
    if git is None:
        return None
    try:
        completed = subprocess.run(
            [git, "check-ignore", "-q", "--", path.name],
            cwd=path.parent,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except OSError, subprocess.SubprocessError:
        return None
    # 1 means not ignored; 128 means no work tree or another error.
    return {0: True, 1: False}.get(completed.returncode)


def _git_issues(workbook: Path) -> list:
    """A warning when the study is in a git work tree that does not ignore the workbook."""
    from pkdb.studyformat.issues import make_issue
    from pkdb.studyformat.workbook.base import state_path

    workbook_ignored = ignored_by_git(workbook)
    if workbook_ignored is None:
        return []
    state = state_path(workbook)
    missing = [
        (path, line)
        for path, line, ignored in (
            (workbook, GITIGNORE_WORKBOOK, workbook_ignored),
            (state, GITIGNORE_STATE, ignored_by_git(state)),
        )
        if ignored is False
    ]
    if not missing:
        return []
    names = " and ".join(path.name for path, _ in missing)
    return [
        make_issue(
            "workbook_not_ignored",
            f"Git does not ignore {names}; commit only the TSV tables",
            file=workbook.name,
            hint="Add these lines to the .gitignore file of the repository:",
            candidates=[line for _, line in missing],
        )
    ]


def _vocabulary(args):
    """The vocabulary chosen as pkdb validate does, or None after an error."""
    from pkdb.cache import VocabularyCache, select_vocabulary

    try:
        return select_vocabulary(
            args.vocabulary, args.endpoint, VocabularyCache(args.cache_dir)
        )
    except (ValueError, OSError) as error:
        say(f"Cannot load the vocabulary: {error}", file=sys.stderr)
        return None


def _study(path: Path) -> Path | None:
    """The folder of a study format 2 study, or None after an error."""
    from pkdb.studyformat import is_v2_folder

    if not (path / "study.json").is_file():
        say(f"{path} is not a study folder: it has no study.json", file=sys.stderr)
        return None
    if not is_v2_folder(path):
        say(
            f"{path} is a study of study format 1; pkdb tables needs study format 2",
            file=sys.stderr,
        )
        return None
    return path


def _reason(error: OSError) -> str:
    reason = str(error.strerror or error)
    return f"{reason} ({error.filename})" if error.filename else reason


def _planned(result) -> bool:
    """Whether the sync changed, or in check mode would change, a table or the workbook."""
    return bool(result.changes) or result.workbook_action != "unchanged"


def _entry(folder: Path, result, issues) -> dict:
    """The JSON line of a synced study."""
    return {
        "path": str(folder),
        "ok": result.ok,
        "workbook": str(result.workbook),
        "workbook_action": result.workbook_action,
        "lock": None if result.lock is None else str(result.lock),
        "changes": [
            {"file": change.file, "action": change.action} for change in result.changes
        ],
        "conflicts": [
            {
                "file": conflict.file,
                "sheet": conflict.sheet,
                "workbook_rows": [
                    {"row": row, "text": text} for row, text in conflict.workbook_rows
                ],
                "table_lines": [
                    {"line": line, "text": text} for line, text in conflict.table_lines
                ],
                "base_lines": list(conflict.base_lines),
                "kept": conflict.kept,
            }
            for conflict in result.conflicts
        ],
        "issues": [issue.model_dump(mode="json") for issue in issues],
    }


def _cells(file: str, text: str) -> str:
    """The filled cells of a canonical TSV line by column name.

    The owned columns, which the formatter fills, are left out.
    """
    from pkdb.studyformat.tables import parse_table_file

    parsed = parse_table_file(file)
    columns = parsed[0].columns if parsed else ()
    cells = [
        f"{column.name}={value}"
        for column, value in zip(columns, text.split("\t"), strict=False)
        if value and not column.owned
    ]
    return ", ".join(cells) or "(empty row)"


def _print_rows(file: str, label: str, rows, removed: str) -> None:
    # The header is the first row and line on both sides; only data rows conflict.
    rows = [(number, text) for number, text in rows if number != 1]
    if not rows:
        say(f"    {removed}")
        return
    for number, text in rows[:LISTED_ROWS]:
        say(f"    {label} {number}: {_cells(file, text)}")
    if len(rows) > LISTED_ROWS:
        say(f"    and {len(rows) - LISTED_ROWS} more; --format json lists all")


def _print_result(label: str, result, issues) -> None:
    """Print a sync for people: the changes, the workbook action, conflicts and issues."""
    planned = int(result.checked)
    if not result.ok:
        unresolved = any(conflict.kept is None for conflict in result.conflicts)
        problems = "the conflicts" if unresolved else "the problems"
        summary = f"cannot sync, resolve {problems} below"
    elif _planned(result):
        summary = "out of sync" if result.checked else "synced"
    else:
        summary = "in sync"
    say(f"{label}: {summary}")
    for change in result.changes:
        say(f"  {CHANGES[change.action][planned]} {change.file}")
    say(
        f"  {result.workbook.name}: {WORKBOOK_ACTIONS[result.workbook_action][planned]}"
    )
    for conflict in result.conflicts:
        kept = f", kept {conflict.kept}" if conflict.kept else ""
        say(f"  conflict in sheet {conflict.sheet}{kept}")
        _print_rows(
            conflict.file,
            "workbook row",
            conflict.workbook_rows,
            "workbook: rows removed",
        )
        _print_rows(
            conflict.file,
            f"{conflict.file} line",
            conflict.table_lines,
            f"{conflict.file}: lines removed",
        )
    print_issues(issues)


def _sync(args) -> int:
    from pkdb.preparation import study_folders
    from pkdb.studyformat import is_v2_folder, study_label, sync_study

    human = args.output == "human" or (args.output is None and sys.stdout.isatty())
    try:
        folders = study_folders(args.folder)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    vocabulary = _vocabulary(args)
    if vocabulary is None:
        return 1
    failed = False
    for folder in folders:
        label = study_label(folder)
        if not is_v2_folder(folder):
            message = "study format 1, left unchanged"
            if human:
                say(f"{label}: skipped, {message}")
            else:
                print(json.dumps({"path": str(folder), "skipped": message}), flush=True)
            continue
        try:
            result = sync_study(folder, vocabulary, keep=args.keep, check=args.check)
        except OSError as error:
            failed = True
            message = f"cannot sync: {_reason(error)}"
            if human:
                say(f"{label}: {message}", file=sys.stderr)
            else:
                print(
                    json.dumps({"path": str(folder), "ok": False, "error": message}),
                    flush=True,
                )
            continue
        issues = [*result.issues, *_git_issues(result.workbook)]
        failed |= not result.ok or (args.check and _planned(result))
        if human:
            _print_result(label, result, issues)
        else:
            entry = _entry(folder, result, issues)
            print(json.dumps(entry, ensure_ascii=False), flush=True)
    return int(failed)


def _open(args) -> int:
    from pkdb.studyformat import study_label, sync_study

    folder = _study(args.study)
    if folder is None:
        return 1
    vocabulary = _vocabulary(args)
    if vocabulary is None:
        return 1
    label = study_label(folder)
    try:
        result = sync_study(folder, vocabulary)
    except OSError as error:
        say(f"{label}: cannot sync: {_reason(error)}", file=sys.stderr)
        return 1
    # A sync that failed is reported, and the curator fixes it in the workbook.
    _print_result(label, result, [*result.issues, *_git_issues(result.workbook)])
    if not args.no_open:
        if not result.workbook.is_file():
            say(
                f"{result.workbook.name} was not created; fix the problems above",
                file=sys.stderr,
            )
            return 1
        from pkdb.curation.launch import open_path

        try:
            open_path(result.workbook)
        except (OSError, subprocess.SubprocessError) as error:
            say(f"Cannot open {result.workbook}: {error}", file=sys.stderr)
            return 1
        say(f"Opened {result.workbook}")
    return int(not result.ok)


def _table_problem(table: str) -> str | None:
    """Why a name cannot be a new table, or None."""
    from pkdb.studyformat.tables import TABLES, parse_table_file
    from pkdb.studyformat.workbook.base import SHEET_NAME_LIMIT

    parsed = parse_table_file(f"{table}.tsv")
    if parsed is None or not parsed[0].per_source:
        *kinds, last = [kind for kind, spec in TABLES.items() if spec.per_source]
        return (
            f"{table!r} is not a table name <kind>_<source> with the kind "
            f"{', '.join(kinds)} or {last} and a source such as Tab3, Fig2A or Text"
        )
    if len(table) > SHEET_NAME_LIMIT:
        return (
            f"{table!r} has {len(table)} characters; Excel limits sheet names to "
            f"{SHEET_NAME_LIMIT} characters"
        )
    return None


def _same_name(name: str, names) -> str | None:
    """The name among `names` that equals `name` ignoring case, as Excel compares sheets."""
    return next((other for other in names if other.casefold() == name.casefold()), None)


def _signature(path: Path) -> tuple[int, int] | None:
    """Modification time and size of a file, None when it is gone."""
    try:
        status = path.stat()
    except OSError:
        return None
    return status.st_mtime_ns, status.st_size


def _add(args) -> int:
    from pkdb.cache import atomic_bytes
    from pkdb.studyformat import study_label, sync_study
    from pkdb.studyformat.issues import make_issue
    from pkdb.studyformat.load import load_study
    from pkdb.studyformat.sync import table_texts
    from pkdb.studyformat.tables import TEXT_SOURCE, image_file, parse_table_file
    from pkdb.studyformat.workbook import write
    from pkdb.studyformat.workbook.base import open_lock, remove_state
    from pkdb.studyformat.workbook.read import read_workbook

    table = args.table

    def refuse(reason: str) -> int:
        say(f"Cannot add {table}: {reason}", file=sys.stderr)
        return 1

    folder = _study(args.study)
    if folder is None:
        return 1
    if (problem := _table_problem(table)) is not None:
        return refuse(problem)
    files = [path.name for path in folder.iterdir()]
    if (existing := _same_name(f"{table}.tsv", files)) is not None:
        return refuse(f"{existing} already exists")
    vocabulary = _vocabulary(args)
    if vocabulary is None:
        return 1
    try:
        result = sync_study(folder, vocabulary)
    except OSError as error:
        return refuse(f"the sync failed: {_reason(error)}")
    _print_result(study_label(folder), result, result.issues)
    if not result.ok:
        return refuse("fix the problems of the sync first")
    path = result.workbook
    close_first = CLOSE_FIRST.format(table=table)
    if result.workbook_action == "close_to_update" or open_lock(path) is not None:
        return refuse(f"{path.name} is open. {close_first}")
    # The workbook is rebuilt from the tables, so it must hold nothing else.
    signature = _signature(path)
    study = load_study(folder)
    tables = table_texts(study)
    content = read_workbook(path, study.name)
    if not content.ok:
        print_issues(content.issues)
        return refuse(f"{path.name} cannot be read")
    if {file: sheet.text for file, sheet in content.tables.items()} != tables:
        return refuse(f"{path.name} was saved during the sync; sync again")
    if (sheet := _same_name(table, content.sheets)) is not None:
        return refuse(f"the sheet {sheet} already exists in {path.name}")
    # Sheets added before keep their place until they have rows.
    empty = [
        name
        for name in content.sheets
        if f"{name}.tsv" not in content.tables
        and (parsed := parse_table_file(f"{name}.tsv")) is not None
        and parsed[0].per_source
    ]
    try:
        build = write.build_workbook(
            tables, vocabulary, existing=path, empty_sheets=[table, *empty]
        )
    except write.WorkbookError as error:
        return refuse(error.message)
    if build.data is None:
        print_issues(build.issues)
        return refuse(f"{path.name} cannot hold the tables")
    if open_lock(path) is not None:
        return refuse(f"{path.name} is open. {close_first}")
    if _signature(path) != signature:
        return refuse(
            f"{path.name} was saved while the sheet was added; run pkdb tables add again"
        )
    try:
        atomic_bytes(path, build.data)
    except PermissionError:
        # Windows keeps an open workbook locked.
        return refuse(
            f"{path.name} cannot be replaced, probably because it is open. {close_first}"
        )
    except OSError as error:
        return refuse(f"{path.name} cannot be written: {_reason(error)}")
    # A new generation starts; a state file left behind belongs to the old one.
    with suppress(OSError):
        remove_state(path)
    say(
        f"Added the sheet {table} to {path.name}; {table}.tsv is written when the "
        "sheet has a row and the workbook is synced"
    )
    issues = list(build.issues)
    source = table.partition("_")[2]
    image = image_file(study.name, source)
    if source != TEXT_SOURCE and not (folder / image).exists():
        issues.append(
            make_issue(
                "missing_image",
                f"{image} is missing; validation needs the image of {source} in "
                "the study folder",
                severity="warning",
            )
        )
    print_issues(issues)
    return 0


def workbook_check(folder: Path, vocabulary) -> dict | None:
    """Plan the sync of a format 2 folder without writing, for pkdb validate and prepare.

    None when the folder has no workbook. Planned TSV changes and conflicts are
    workbook changes that pkdb tables sync has not written to the tables yet.
    """
    from pkdb.studyformat import sync_study
    from pkdb.studyformat.workbook.base import workbook_path

    folder = Path(folder).resolve()
    if not workbook_path(folder).exists():
        return None
    result = sync_study(folder, vocabulary, check=True)
    return {
        "action": result.workbook_action,
        "changes": [
            {"file": change.file, "action": change.action} for change in result.changes
        ],
        "conflicts": len(result.conflicts),
        "ok": result.ok,
    }
