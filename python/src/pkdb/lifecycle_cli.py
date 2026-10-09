"""The study lifecycle commands of a pkdb_data checkout."""

import argparse
from pathlib import Path


def _date(text: str):
    import datetime

    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a date YYYY-MM-DD") from None


def register(commands) -> None:
    """Add the lifecycle commands to the command line parser."""
    from pkdb.study_cli import add_format
    from pkdb.tables_cli import _vocabulary_options

    release = commands.add_parser(
        "release",
        help="Give approved studies the next PKDB identifiers",
        description=(
            "Give approved studies without open review items and validation errors "
            "the next PKDB identifiers in the release block of study.json, in the "
            "order of the arguments. Nothing is written when one study is refused."
        ),
    )
    release.add_argument("studies", nargs="+", type=Path, metavar="STUDY")
    release.add_argument(
        "--date", type=_date, help="Release date YYYY-MM-DD (default: today)"
    )
    _vocabulary_options(release)
    add_format(release)

    command = commands.add_parser(
        "registry",
        help="List released studies by PKDB identifier",
        description="List released studies by PKDB identifier.",
    )
    command.add_argument(
        "--root",
        type=Path,
        help="Folder inside the repository with a studies folder (default: found by searching upward from the current folder)",
    )
    command.add_argument(
        "--check",
        action="store_true",
        help="Exit with 1 when studies share an identifier or an issue number, or a study.json cannot be read",
    )
    add_format(command)


def run(args) -> int:
    """Run a lifecycle command and return the exit code."""
    import sys

    from pkdb.studyformat_cli import say

    try:
        if args.command == "release":
            return _release(args)
        if args.command == "registry":
            return _registry(args)
    except ValueError as error:
        say(str(error), file=sys.stderr)
        return 2
    raise AssertionError(args.command)


def _registry(args) -> int:
    from pkdb.lifecycle.registry import duplicates, registry_problems, scan
    from pkdb.repository import repository_root
    from pkdb.study_cli import emit

    root = repository_root(args.root or Path.cwd())
    result = scan(root)
    problems = duplicates(result) + registry_problems(result, root)
    data = {
        "released": [
            {
                "pkdb_id": item.pkdb_id,
                "location": item.location,
                "date": item.date.isoformat(),
            }
            for item in result.released
        ],
        "problems": problems,
        "errors": result.errors,
    }
    lines = [
        f"{item['pkdb_id']}  {item['location']}  {item['date']}"
        for item in data["released"]
    ]
    lines += problems
    lines += [f"Error: {error}" for error in result.errors]
    emit(args, data, lines)
    return 1 if args.check and (problems or result.errors) else 0


def _release_folders(paths: list[Path]) -> tuple[Path, list[Path]]:
    """The checkout and the study folders of the arguments, or a ValueError."""
    from pkdb.repository import STUDIES, repository_root
    from pkdb.studyformat.validation import is_v2_folder

    folders: list[Path] = []
    roots: set[Path] = set()
    for path in paths:
        folder = path.resolve()
        if not folder.is_dir() or not is_v2_folder(folder):
            raise ValueError(f"{path} is not a study format 2 folder")
        if folder in folders:
            raise ValueError(f"{path} is given twice")
        try:
            root = repository_root(folder)
        except ValueError as error:
            raise ValueError(f"{path}: {error}") from None
        if folder.parent.parent != root / STUDIES:
            raise ValueError(f"{path} is not a folder {STUDIES}/SUBSTANCE/NAME")
        folders.append(folder)
        roots.add(root)
    if len(roots) > 1:
        raise ValueError("The studies lie in different checkouts")
    return roots.pop(), folders


def _say_all(lines: list[str]) -> None:
    import sys

    from pkdb.studyformat_cli import say

    for line in lines:
        say(line, file=sys.stderr)


def _release(args) -> int:
    import datetime

    from pkdb.lifecycle.release import ReleaseConflict, ReleaseRefused, release
    from pkdb.study_cli import emit, fail
    from pkdb.tables_cli import _vocabulary

    root, folders = _release_folders(args.studies)
    vocabulary = _vocabulary(args)
    if vocabulary is None:
        return 2
    on = args.date or datetime.date.today()
    try:
        done = release(root, folders, vocabulary, on=on)
    except ReleaseRefused as refused:
        data = {
            "refused": [
                {"location": item.location, "reasons": item.reasons}
                for item in refused.refusals
            ]
        }

        lines = ["No study was released."]
        for item in refused.refusals:
            lines.append(f"{item.location}:")
            lines += [f"  {reason}" for reason in item.reasons]
        return fail(args, data, lambda: _say_all(lines))
    except ReleaseConflict as conflict:
        data = {
            "error": str(conflict),
            "released": [
                {"location": place, "pkdb_id": pkdb_id}
                for place, pkdb_id in conflict.released
            ],
        }
        lines = [str(conflict)]
        return fail(args, data, lambda: _say_all(lines))
    data = {
        "released": [
            {"location": place, "pkdb_id": pkdb_id, "date": on.isoformat()}
            for place, pkdb_id in done
        ]
    }
    emit(args, data, [f"{place}: {pkdb_id}" for place, pkdb_id in done])
    return 0
