"""The pkdb tables commands: edit the tables of study format 2 folders in a workbook.

`sync` keeps the generated workbook `<name>.xlsx` and the TSV tables of a study
in step, `open` syncs and opens the workbook, and `add` adds the empty sheet of
a new `<kind>_<source>` table or of the raw table `<name>_<source>` of a paper
table. The TSV tables are the files to commit; git should ignore the workbook
and its sync state file.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from pkdb.studyformat_cli import print_issues, say, study_folder

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

# The summary of a sync that wrote the tables but not the workbook.
SYNCED_WITHOUT_WORKBOOK = {
    "close_to_update": "tables synced, workbook not updated (close it and sync again)",
    "sync_again": "tables synced, the workbook was saved during the sync; sync again",
}


def _vocabulary_options(
    command,
    offline_help: str = "Never contact the server; tables commands only use cached vocabulary",
) -> None:
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
        help=offline_help,
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
            "as outputs_Tab3, or the empty text sheet of the raw table of a paper "
            "table with --raw. Its TSV file is written when the sheet has a row "
            "and the workbook is synced."
        ),
    )
    add.add_argument("study", type=Path, help="Study folder")
    # Exactly one of both; argparse reports a usage error otherwise.
    target = add.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "table", nargs="?", help="Table name <kind>_<source>, such as outputs_Tab3"
    )
    target.add_argument(
        "--raw",
        metavar="SOURCE",
        help="Add the sheet of the raw table of a paper table, such as Tab2",
    )
    _vocabulary_options(add)


def run(args) -> int:
    """Run a `tables` action and return the exit code."""
    actions = {"open": _open, "sync": _sync, "add": _add}
    return actions[args.action](args)


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


def _reason(error: OSError) -> str:
    reason = str(error.strerror or error)
    return f"{reason} ({error.filename})" if error.filename else reason


def _planned(result) -> bool:
    """Whether the sync changed, or in check mode would change, a table or the workbook."""
    return bool(result.changes) or result.workbook_action != "unchanged"


def _entry(folder: Path, result, issues) -> dict:
    """The JSON line of a synced study."""
    from pkdb.studyformat.sync import conflict_data

    return {
        "path": str(folder),
        "ok": result.ok,
        "workbook": str(result.workbook),
        "workbook_action": result.workbook_action,
        "lock": None if result.lock is None else str(result.lock),
        "changes": [
            {"file": change.file, "action": change.action} for change in result.changes
        ],
        "conflicts": [conflict_data(conflict) for conflict in result.conflicts],
        "issues": [issue.model_dump(mode="json") for issue in issues],
    }


def _cells(file: str, text: str) -> str:
    """The filled cells of a canonical TSV line by column name.

    The owned columns, which the formatter fills, are left out. A raw table has
    no header, so its cells are named by their column letter.
    """
    from pkdb.studyformat.issues import column_letter
    from pkdb.studyformat.tables import parse_table_file

    values = text.split("\t")
    parsed = parse_table_file(file)
    if parsed is None:
        cells = [
            f"{column_letter(index)}={value}"
            for index, value in enumerate(values)
            if value
        ]
    else:
        cells = [
            f"{column.name}={value}"
            for column, value in zip(parsed[0].columns, values, strict=False)
            if value and not column.owned
        ]
    return ", ".join(cells) or "(empty row)"


def _print_rows(file: str, label: str, rows, removed: str) -> None:
    from pkdb.studyformat.tables import parse_table_file

    # The header is the first row and line on both sides of a table; only data
    # rows conflict. A raw table has no header.
    if parse_table_file(file) is not None:
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
    elif result.checked and _planned(result):
        summary = "out of sync"
    elif result.workbook_action == "close_to_update" and not result.workbook.exists():
        # A lock file without workbook: it is open while it is saved.
        summary = (
            "tables synced, workbook not created (it is open; close it and sync again)"
        )
    elif result.workbook_action in SYNCED_WITHOUT_WORKBOOK:
        summary = SYNCED_WITHOUT_WORKBOOK[result.workbook_action]
    elif _planned(result):
        summary = "synced"
    else:
        summary = "in sync"
    say(f"{label}: {summary}")
    for change in result.changes:
        say(f"  {CHANGES[change.action][planned]} {change.file}")
    if result.workbook_action == "unchanged" and not result.workbook.exists():
        # The problems below stopped the sync before the workbook was created.
        words = ("not created", "cannot be created")[planned]
        say(f"  {result.workbook.name}: {words} because of the problems below")
    elif result.workbook_action == "close_to_update" and not result.workbook.exists():
        # A lock file without workbook: it is open while it is saved.
        say(f"  {result.workbook.name}: not created because it is open")
    else:
        words = WORKBOOK_ACTIONS[result.workbook_action][planned]
        say(f"  {result.workbook.name}: {words}")
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
    from pkdb.studyformat.workbook.git import git_issues

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
        issues = [*result.issues, *git_issues(result.workbook)]
        failed |= not result.ok or (args.check and _planned(result))
        if human:
            _print_result(label, result, issues)
        else:
            entry = _entry(folder, result, issues)
            print(json.dumps(entry, ensure_ascii=False), flush=True)
    return int(failed)


def _open(args) -> int:
    from pkdb.studyformat import study_label, sync_study
    from pkdb.studyformat.workbook.git import git_issues

    folder = study_folder(args.study, "tables")
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
    _print_result(label, result, [*result.issues, *git_issues(result.workbook)])
    if not args.no_open:
        if not result.workbook.is_file():
            # A failed sync said why it did not create the workbook.
            if result.ok:
                say(f"{result.workbook} does not exist", file=sys.stderr)
            return 1
        from pkdb.curation.launch import open_path

        try:
            open_path(result.workbook)
        except (OSError, subprocess.SubprocessError) as error:
            say(f"Cannot open {result.workbook}: {error}", file=sys.stderr)
            return 1
        say(f"Opened {result.workbook}")
    return int(not result.ok)


def _add(args) -> int:
    from pkdb.studyformat import add_table, study_label

    folder = study_folder(args.study, "tables")
    if folder is None:
        return 1
    # The raw table is named after the study folder, also when it is given as `.`.
    table = args.table if args.raw is None else f"{folder.resolve().name}_{args.raw}"
    vocabulary = _vocabulary(args)
    if vocabulary is None:
        return 1
    try:
        result = add_table(folder, vocabulary, table)
    except OSError as error:
        say(f"Cannot add {table}: {_reason(error)}", file=sys.stderr)
        return 1
    if result.sync is not None:
        _print_result(study_label(folder), result.sync, result.sync.issues)
    if result.ok:
        assert result.sync is not None
        content = "a row" if args.raw is None else "a cell"
        say(
            f"Added the sheet {table} to {result.sync.workbook.name}; {table}.tsv is "
            f"written when the sheet has {content} and the workbook is synced"
        )
        print_issues(result.issues)
        return 0
    # The sync report comes first, also when stdout is a pipe.
    sys.stdout.flush()
    if any(issue.severity == "error" for issue in result.issues):
        say(f"Cannot add {table}: fix the problems below", file=sys.stderr)
        print_issues(result.issues, file=sys.stderr)
    else:
        say(f"Cannot add {table}: fix the problems of the sync first", file=sys.stderr)
    return 1
