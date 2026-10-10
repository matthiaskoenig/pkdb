"""The `pkdb check` command: the checks of pre-commit and CI for a pkdb_data checkout."""

import json
import sys
from pathlib import Path

from pkdb.study_cli import add_format, emit, is_human
from pkdb.studyformat_cli import say


def register(commands) -> None:
    """Add the `check` command to the command line parser."""
    description = (
        "Check the format 2 studies of a pkdb_data checkout: canonical form, "
        "offline validation, tracked workbooks, shared identifiers and issue numbers. "
        "Nothing is written and no server is contacted."
    )
    command = commands.add_parser(
        "check",
        help="Check the format 2 studies of a pkdb_data checkout",
        description=description,
    )
    command.add_argument(
        "paths",
        nargs="*",
        type=Path,
        metavar="PATH",
        help="Study folders or folders above them (default: every study of the checkout)",
    )
    mode = command.add_mutually_exclusive_group()
    mode.add_argument(
        "--staged",
        action="store_true",
        help="Check the studies of the files staged in git",
    )
    mode.add_argument(
        "--changed",
        metavar="BASE",
        help="Check the studies changed since the merge base with the commit BASE",
    )
    command.add_argument(
        "--root",
        type=Path,
        help="Folder inside the checkout (default: found by searching upward from the first PATH or the current folder)",
    )
    command.add_argument(
        "--vocabulary",
        type=Path,
        help="Vocabulary snapshot JSON (default: vocabulary.lock.json of the checkout, else the one bundled with pkdb)",
    )
    add_format(command)


def _line(problem) -> str:
    where = problem.study or ""
    if problem.file:
        where += f" {problem.file}" + (f":{problem.row}" if problem.row else "")
    mark = " (warning)" if problem.severity == "warning" else ""
    return f"{where} {problem.code}{mark}: {problem.message}".lstrip()


def _lines(report) -> list[str]:
    errors = sum(problem.severity == "error" for problem in report.problems)
    warnings = len(report.problems) - errors
    return [
        *map(_line, report.problems),
        f"Checked {len(report.checked)} format 2 studies, skipped {report.format_1} "
        f"format 1 studies: {errors} errors, {warnings} warnings.",
    ]


def _usage_error(args, message: str) -> int:
    """Report a usage error on stderr: a JSON object `{"ok": false, "error": ...}` in JSON mode, else a line."""
    if is_human(args):
        say(f"pkdb check: {message}", file=sys.stderr)
    else:
        data = {"ok": False, "error": message}
        print(json.dumps(data, ensure_ascii=False, allow_nan=False), file=sys.stderr)
    return 2


def run(args) -> int:
    """Run `pkdb check`: exit 0 when no problem is an error, 1 otherwise, 2 for usage errors."""
    from pkdb.checks import CheckError, check, select, vocabulary_for
    from pkdb.repository import repository_root

    try:
        if args.paths and (args.staged or args.changed is not None):
            raise CheckError(
                "Choose study paths, the staged files or a base, not several"
            )
        for path in args.paths:
            if not path.exists():
                raise CheckError(f"{path.as_posix()} does not exist")
        start = args.root or (args.paths[0] if args.paths else Path.cwd())
        root = repository_root(start)
        folders, deleted = select(
            root, paths=args.paths, staged=args.staged, changed=args.changed
        )
        vocabulary = vocabulary_for(root, args.vocabulary)
        report = check(root, folders, vocabulary, deleted=deleted, staged=args.staged)
    except ValueError as error:
        return _usage_error(args, str(error))
    emit(args, report.model_dump(mode="json"), _lines(report))
    return 0 if report.ok else 1
