"""The study lifecycle commands of a pkdb_data checkout."""

from pathlib import Path


def register(commands) -> None:
    """Add the lifecycle commands to the command line parser."""
    from pkdb.study_cli import add_format

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
        if args.command == "registry":
            return _registry(args)
    except ValueError as error:
        say(str(error), file=sys.stderr)
        return 2
    raise AssertionError(args.command)


def _registry(args) -> int:
    from pkdb.lifecycle.registry import duplicates, scan
    from pkdb.repository import repository_root
    from pkdb.study_cli import emit

    result = scan(repository_root(args.root or Path.cwd()))
    problems = duplicates(result)
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
