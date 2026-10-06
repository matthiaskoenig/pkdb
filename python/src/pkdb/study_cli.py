"""The pkdb study command: show and edit the metadata of a study format 2 folder."""

import json
import sys
from pathlib import Path

from pkdb.studyformat_cli import print_issues, say, study_folder


def add_format(command) -> None:
    command.add_argument(
        "--format",
        choices=("human", "json"),
        help="Output format (default: human on a terminal, json otherwise)",
    )


def is_human(args) -> bool:
    return args.format == "human" or (args.format is None and sys.stdout.isatty())


def emit(args, data: dict, lines: list[str] | None = None) -> None:
    """Print `data` as JSON, or the human `lines`."""
    if is_human(args):
        for line in lines or []:
            say(line)
    else:
        print(json.dumps(data, ensure_ascii=False, allow_nan=False))


def fail(args, data: dict, human) -> int:
    """Report a failure on stdout (JSON) or stderr (human) and return exit code 1."""
    if is_human(args):
        human()
    else:
        print(json.dumps(data, ensure_ascii=False, allow_nan=False))
    return 1


def register(commands) -> None:
    command = commands.add_parser(
        "study",
        help="Show and edit the metadata of a study (study.json)",
        description="Show and edit study.json with checked, atomic writes.",
    )
    actions = command.add_subparsers(dest="action", required=True)
    show = actions.add_parser("show", help="Print study.json with its revision")
    patch = actions.add_parser("patch", help="Apply a JSON merge patch to study.json")
    source = patch.add_mutually_exclusive_group(required=True)
    source.add_argument("--json", metavar="TEXT", help="The patch as JSON text")
    source.add_argument("--file", type=Path, help="A file with the patch")
    patch.add_argument(
        "--revision", help="Refuse the write unless study.json is at this revision"
    )
    reference = actions.add_parser(
        "reference", help="Set the PubMed ID or DOI and refresh reference.json"
    )
    reference.add_argument("--pmid")
    reference.add_argument("--doi")
    reference.add_argument("--offline", action="store_true")
    reference.add_argument("--cache-dir", type=Path)
    for action in (show, patch, reference):
        action.add_argument("study", type=Path, help="Study folder")
        add_format(action)


def run(args) -> int:
    """Run a `study` action and return the exit code."""
    folder = study_folder(args.study, "study")
    if folder is None:
        return 1
    actions = {"show": _show, "patch": _patch, "reference": _reference}
    return actions[args.action](args, folder)


def _show(args, folder: Path) -> int:
    from pkdb.studyformat import study_label
    from pkdb.studyformat.metadata import MetadataError, read_metadata
    from pkdb.studyformat.models import canonical_study_json

    try:
        document = read_metadata(folder)
    except MetadataError as error:
        return _invalid(args, folder, error)
    label = study_label(folder)
    emit(
        args,
        {
            "study": label,
            "path": str(folder),
            "revision": document.revision,
            "metadata": document.metadata.model_dump(mode="json", exclude_none=True),
        },
        [
            label,
            f"revision {document.revision}",
            canonical_study_json(document.metadata).rstrip("\n"),
        ],
    )
    return 0


def _patch(args, folder: Path) -> int:
    try:
        text = args.json if args.json is not None else args.file.read_text("utf-8")
        patch = json.loads(text)
        if not isinstance(patch, dict):
            raise ValueError("The patch must be a JSON object")
    except (ValueError, OSError) as error:
        message = str(getattr(error, "strerror", None) or error)
        return fail(
            args,
            {
                "path": str(folder),
                "ok": False,
                "error": "invalid_patch",
                "message": message,
            },
            lambda: say(f"Invalid patch: {message}", file=sys.stderr),
        )
    return _write(args, folder, patch, args.revision, None)


def _reference(args, folder: Path) -> int:
    from pkdb.references import ReferenceResolver

    identifiers = {"pmid": args.pmid, "doi": args.doi}
    given = {key: value for key, value in identifiers.items() if value is not None}
    if not given:
        say("Give --pmid or --doi", file=sys.stderr)
        return 1
    try:
        resolver = ReferenceResolver(args.cache_dir, offline=args.offline)
    except ValueError as error:
        say(f"Cannot resolve references: {error}", file=sys.stderr)
        return 1
    return _write(args, folder, {"reference": given}, None, resolver)


def _write(args, folder: Path, patch: dict, revision, resolver) -> int:
    from pkdb.studyformat import study_label
    from pkdb.studyformat.metadata import MetadataError, patch_metadata
    from pkdb.studyformat.revision import RevisionConflict

    try:
        written = patch_metadata(folder, patch, revision, resolver=resolver)
    except MetadataError as error:
        return _invalid(args, folder, error)
    except RevisionConflict as conflict:
        message = (
            f"{conflict.file} changed on disk since revision {conflict.expected}; "
            "show it again and retry"
        )
        return fail(
            args,
            {
                "path": str(folder),
                "ok": False,
                "error": "revision_conflict",
                "revision": conflict.current,
            },
            lambda: say(message, file=sys.stderr),
        )
    except OSError as error:
        reason = str(error.strerror or error)
        return fail(
            args,
            {
                "path": str(folder),
                "ok": False,
                "error": "write_failed",
                "message": reason,
            },
            lambda: say(f"Cannot write study.json: {reason}", file=sys.stderr),
        )
    line = f"{study_label(folder)}: wrote study.json"
    if written.reference:
        line += f"; {written.reference}"
    emit(
        args,
        {
            "path": str(folder),
            "ok": True,
            "revision": written.revision,
            "reference": written.reference,
        },
        [line],
    )
    return 0


def _invalid(args, folder: Path, error) -> int:
    issues = [issue.model_dump(mode="json") for issue in error.issues]

    def human() -> None:
        say("study.json is invalid:", file=sys.stderr)
        print_issues(error.issues, file=sys.stderr)

    return fail(
        args,
        {"path": str(folder), "ok": False, "error": "invalid", "issues": issues},
        human,
    )
