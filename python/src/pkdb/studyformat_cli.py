"""Commands for study format 2 folders: format and schema."""

import json
import sys
from pathlib import Path


def register(commands) -> None:
    """Add the `format` and `schema` commands to the command line parser."""
    command = commands.add_parser(
        "format",
        help="Write study format 2 folders in canonical form",
        description="Write study format 2 folders in canonical form: sorted rows, canonical numbers and JSON, filled study and source columns.",
    )
    command.add_argument("folder", type=Path, help="Study folder or parent directory")
    command.add_argument(
        "--check",
        action="store_true",
        help="Only report files that need formatting; exit with 1 if any do",
    )
    command.add_argument(
        "--format",
        dest="output",
        choices=("human", "json"),
        help="Output format (default: human on a terminal, otherwise json)",
    )
    schema = commands.add_parser(
        "schema",
        help="Export the study format 2 schema",
        description="Export the study format 2 schema as JSON Schema or as the Markdown column reference.",
    )
    actions = schema.add_subparsers(dest="action", required=True)
    export = actions.add_parser(
        "export",
        help="Write JSON Schema files for study.json, review.json and every table",
    )
    export.add_argument(
        "--output", type=Path, required=True, help="Directory for the schema files"
    )
    docs = actions.add_parser("docs", help="Write the Markdown column reference")
    docs.add_argument(
        "--output", type=Path, required=True, help="Markdown file to write"
    )


def run(args) -> int:
    """Run the `format` or `schema` command and return the exit code."""
    return _schema(args) if args.command == "schema" else _format(args)


def _schema(args) -> int:
    from pkdb.cache import atomic_json, atomic_text
    from pkdb.studyformat.export import column_reference, json_schemas

    try:
        if args.action == "export":
            schemas = json_schemas()
            for name, schema in schemas.items():
                atomic_json(args.output / name, schema)
            print(f"Wrote {len(schemas)} schema files to {args.output}")
        else:
            atomic_text(args.output, column_reference())
            print(f"Wrote {args.output}")
    except OSError as error:
        print(f"Cannot write {args.output}: {error.strerror or error}", file=sys.stderr)
        return 1
    return 0


def say(text: str, *, file=None) -> None:
    """Print one human line; folder names and messages come from untrusted files."""
    from pkdb.terminal import safe_text

    print(safe_text(text), file=file)


def _location(source) -> str:
    if source is None:
        return ""
    if source.cell:
        return f"{source.file} {source.cell}"
    if source.row:
        return f"{source.file} line {source.row}"
    return source.file


def _print_human(label: str, result, check: bool) -> None:
    written = [change.file for change in result.changes if change.action == "write"]
    removed = [change.file for change in result.changes if change.action == "delete"]
    parts = []
    if written:
        parts.append(("would rewrite " if check else "rewrote ") + ", ".join(written))
    if removed:
        parts.append(("would remove " if check else "removed ") + ", ".join(removed))
    if parts:
        summary = "; ".join(parts)
    elif result.ok:
        summary = "already formatted"
    else:
        summary = "not formatted, fix the problems below"
    say(f"{label}: {summary}")
    print_issues(result.issues)


def print_issues(issues) -> None:
    """Print issues for people: location, message and code, then each suggestion.

    Candidates of a hint are printed one per line, such as lines to add to a file.
    """
    from pkdb.studyformat.issues import DID_YOU_MEAN

    for issue in issues:
        where = _location(issue.source)
        say(f"  {where + ': ' if where else ''}{issue.message} [{issue.code}]")
        for suggestion in issue.suggestions:
            if suggestion.message == DID_YOU_MEAN:
                candidates = ", ".join(map(str, suggestion.candidates))
                say(f"    Did you mean: {candidates}")
                continue
            say(f"    {suggestion.message}")
            for candidate in suggestion.candidates:
                say(f"      {candidate}")


def _format(args) -> int:
    from pkdb.preparation import study_folders
    from pkdb.studyformat import format_folder, is_v2_folder, study_label

    human = args.output == "human" or (args.output is None and sys.stdout.isatty())
    try:
        folders = study_folders(args.folder)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    failed = False
    for folder in folders:
        if not is_v2_folder(folder):
            message = "study format 1, left unchanged"
            if human:
                say(f"{study_label(folder)}: skipped, {message}")
            else:
                print(json.dumps({"path": str(folder), "skipped": message}), flush=True)
            continue
        try:
            result = format_folder(folder, check=args.check)
        except OSError as error:
            failed = True
            message = f"cannot format: {error.strerror or error}"
            if error.filename:
                message += f" ({error.filename})"
            if human:
                say(f"{study_label(folder)}: {message}", file=sys.stderr)
            else:
                print(
                    json.dumps({"path": str(folder), "ok": False, "error": message}),
                    flush=True,
                )
            continue
        failed |= not result.ok or (args.check and bool(result.changes))
        if human:
            _print_human(study_label(folder), result, args.check)
        else:
            entry = {
                "path": str(folder),
                "ok": result.ok,
                "changes": [
                    {"file": change.file, "action": change.action}
                    for change in result.changes
                ],
                "issues": [issue.model_dump(mode="json") for issue in result.issues],
            }
            print(json.dumps(entry, ensure_ascii=False), flush=True)
    return int(failed)
