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
    register_review(commands)


def register_review(commands) -> None:
    from pkdb.tables_cli import _vocabulary_options

    command = commands.add_parser(
        "review",
        help="Show and edit the review of a study (review.json)",
        description="Show and edit review.json with checked, atomic writes.",
    )
    subcommands = command.add_subparsers(dest="action", required=True)

    class Actions:
        """Adds the study folder as the first positional argument of every action."""

        @staticmethod
        def add_parser(name, help):
            action = subcommands.add_parser(name, help=help)
            action.add_argument("study", type=Path, help="Study folder")
            return action

    actions = Actions()
    show = actions.add_parser("show", help="Print the review items with the revision")
    show.add_argument("--state", choices=("open", "resolved", "dismissed"))
    add = actions.add_parser("add", help="Add a review item")
    add.add_argument(
        "--kind", required=True, choices=("question", "uncertainty", "issue")
    )
    add.add_argument("--text", required=True)
    add.add_argument("--file", help="File the item refers to")
    add.add_argument(
        "--rows",
        nargs="+",
        metavar="COL=VALUE",
        help="Narrow the item to the rows with these cell values",
    )
    add.add_argument("--column", help="Column the item refers to")
    add.add_argument(
        "--acknowledges", metavar="CODE", help="Warning code to acknowledge"
    )
    reviewed = [show, add]
    for name, text_help in (
        ("reply", "Add a reply to the thread of an item"),
        ("resolve", "Resolve an open item"),
        ("dismiss", "Dismiss an open or resolved item"),
        ("reopen", "Reopen a resolved or dismissed item"),
    ):
        action = actions.add_parser(name, help=text_help)
        action.add_argument("id", help="Review item id")
        action.add_argument("--text", required=name == "reply")
        reviewed.append(action)
    status = actions.add_parser(
        "status", help="Set the review status; approving needs a person"
    )
    status.add_argument("status", choices=("draft", "in_review", "approved"))
    _vocabulary_options(status)
    acknowledge = actions.add_parser(
        "acknowledge", help="Acknowledge a validation warning with a resolved item"
    )
    acknowledge.add_argument("code", help="Warning code")
    acknowledge.add_argument("--file", required=True)
    acknowledge.add_argument("--line", type=int)
    acknowledge.add_argument("--column")
    acknowledge.add_argument("--text", required=True)
    _vocabulary_options(acknowledge)
    reviewed += [status, acknowledge]
    for action in reviewed:
        add_format(action)
        if action is not show:
            action.add_argument("--user", help="PK-DB user (default: PKDB_USER)")
            action.add_argument("--agent", help="AI agent (default: PKDB_AGENT)")
            action.add_argument(
                "--revision",
                help="Refuse the write unless review.json is at this revision",
            )


def run(args) -> int:
    """Run a `study` or `review` action and return the exit code."""
    folder = study_folder(args.study, args.command)
    if folder is None:
        return 1
    if args.command == "review":
        return _review(args, folder)
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
    if written.reference_error:
        line += f"; could not refresh reference.json: {written.reference_error}"
    emit(
        args,
        {
            "path": str(folder),
            "ok": True,
            "revision": written.revision,
            "reference": written.reference,
            **(
                {"reference_error": written.reference_error}
                if written.reference_error
                else {}
            ),
        },
        [line],
    )
    return 1 if written.reference_error else 0


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


def _review(args, folder: Path) -> int:
    """Run a `review` action; errors are reported as `pkdb study` does."""
    from pkdb.identity import IdentityError, author_from
    from pkdb.studyformat.review_edit import ApprovalRefused, ReviewError
    from pkdb.studyformat.revision import RevisionConflict

    def failure(error: str, message: str, **extra) -> int:
        return fail(
            args,
            {"path": str(folder), "ok": False, "error": error, "message": message}
            | extra,
            lambda: say(message, file=sys.stderr),
        )

    try:
        if args.action == "show":
            return _review_show(args, folder)
        author = author_from(args.user, args.agent)
        return _REVIEW_ACTIONS[args.action](args, folder, author)
    except IdentityError as error:
        return failure("no_user", str(error))
    except ApprovalRefused as error:
        return _review_error(args, folder, "approval_refused", error)
    except ReviewError as error:
        return _review_error(args, folder, "invalid", error)
    except RevisionConflict as conflict:
        message = (
            f"{conflict.file} changed on disk since revision {conflict.expected}; "
            "show it again and retry"
        )
        return failure("revision_conflict", message, revision=conflict.current)
    except OSError as error:
        reason = str(error.strerror or error)
        return failure("write_failed", f"Cannot write review.json: {reason}")


def _review_error(args, folder: Path, code: str, error) -> int:
    issues = [issue.model_dump(mode="json") for issue in error.issues]

    def human() -> None:
        say(str(error), file=sys.stderr)
        print_issues(error.issues, file=sys.stderr)

    return fail(
        args,
        {
            "path": str(folder),
            "ok": False,
            "error": code,
            "message": str(error),
            "issues": issues,
        },
        human,
    )


def _review_show(args, folder: Path) -> int:
    from pkdb.studyformat import study_label
    from pkdb.studyformat.load import load_study
    from pkdb.studyformat.review_edit import read_review

    document = read_review(folder)
    study = load_study(folder)
    items = []
    for item in document.review.items:
        if args.state and item.state != args.state:
            continue
        data = item.model_dump(mode="json", exclude_none=True)
        target = item.target
        table = study.table(target.file) if target and target.file else None
        data["matches"] = (
            len(table.matching_lines(target.rows))
            if table is not None and target is not None and target.rows
            else None
        )
        items.append(data)
    label = study_label(folder)
    lines = [label, f"revision {document.revision}", f"status {document.review.status}"]
    for data in items:
        lines.append(
            f"{data['id']} {data['state']} {data['kind']}"
            f"{_target_text(data.get('target'), data['matches'])}: {data['text']}"
        )
    emit(
        args,
        {
            "study": label,
            "path": str(folder),
            "revision": document.revision,
            "status": document.review.status,
            "items": items,
        },
        lines,
    )
    return 0


def _target_text(target: dict | None, matches: int | None) -> str:
    """The target of an item for people: file, row filter, column and matching rows."""
    if not target or not target.get("file"):
        return ""
    text = f" {target['file']}"
    rows = target.get("rows") or {}
    if rows:
        text += " " + " ".join(f"{key}={value}" for key, value in rows.items())
    if target.get("column"):
        text += f" column {target['column']}"
    if matches is not None:
        text += f" ({matches} matching row{'' if matches == 1 else 's'})"
    return text


def _written(args, folder: Path, revision: str, line: str, **extra) -> int:
    from pkdb.studyformat import study_label

    emit(
        args,
        {"path": str(folder), "ok": True, "revision": revision, **extra},
        [f"{study_label(folder)}: {line}"],
    )
    return 0


def _review_add(args, folder: Path, author) -> int:
    from pkdb.schemas.review import ReviewTarget
    from pkdb.studyformat.review_edit import ReviewError, add_item

    rows = {}
    for pair in args.rows or []:
        key, separator, value = pair.partition("=")
        if not separator or not key:
            raise ReviewError(f"--rows needs COL=VALUE, not {pair!r}")
        rows[key] = value
    if args.file or rows or args.column:
        try:
            target = ReviewTarget(file=args.file, rows=rows, column=args.column)
        except ValueError as error:
            raise ReviewError("--rows and --column require --file") from error
    else:
        target = None
    item, revision = add_item(
        folder,
        author,
        kind=args.kind,
        text=args.text,
        target=target,
        acknowledges=args.acknowledges,
        revision=args.revision,
    )
    return _written(
        args,
        folder,
        revision,
        f"added review item {item.id}",
        item=item.model_dump(mode="json", exclude_none=True),
    )


def _review_thread(args, folder: Path, author) -> int:
    from pkdb.studyformat import review_edit

    action = getattr(review_edit, args.action)
    revision = action(folder, author, args.id, args.text, revision=args.revision)
    return _written(args, folder, revision, f"{args.action} {args.id}")


def _review_status(args, folder: Path, author) -> int:
    from pkdb.studyformat.review_edit import set_status
    from pkdb.tables_cli import _vocabulary

    vocabulary = None
    if args.status == "approved":  # only approval validates the folder
        vocabulary = _vocabulary(args)
        if vocabulary is None:
            return 1
    revision = set_status(
        folder, author, args.status, vocabulary=vocabulary, revision=args.revision
    )
    return _written(args, folder, revision, f"status {args.status}")


def _review_acknowledge(args, folder: Path, author) -> int:
    from pkdb.studyformat.review_edit import acknowledge
    from pkdb.studyformat.validation import validate_folder
    from pkdb.tables_cli import _vocabulary

    vocabulary = _vocabulary(args)
    if vocabulary is None:
        return 1
    matches = [
        issue
        for issue in validate_folder(folder, vocabulary).issues
        if issue.severity == "warning"
        and issue.code == args.code
        and issue.source is not None
        and issue.source.file == args.file
        and (args.line is None or issue.source.row == args.line)
        and (args.column is None or issue.source.header == args.column)
    ]
    # One item acknowledges the warnings of one location: same row and column.
    locations = {
        (source.row, source.header) for issue in matches if (source := issue.source)
    }
    if len(locations) != 1:
        message = (
            f"{len(matches)} warnings [{args.code}] match in {args.file}; "
            f"narrow them with {_narrowing(locations)}"
            if matches
            else f"No warning [{args.code}] in {args.file} matches"
        )
        return fail(
            args,
            {
                "path": str(folder),
                "ok": False,
                "error": "no_such_warning",
                "message": message,
            },
            lambda: say(message, file=sys.stderr),
        )
    item, revision = acknowledge(
        folder, author, matches[0], args.text, revision=args.revision
    )
    covers = f"; the item covers {len(matches)} warnings" if len(matches) > 1 else ""
    return _written(
        args,
        folder,
        revision,
        f"acknowledged {args.code} with review item {item.id}{covers}",
        item=item.model_dump(mode="json", exclude_none=True),
        warnings=len(matches),
    )


def _narrowing(locations: set[tuple[int | None, str | None]]) -> str:
    """The options that tell apart warnings at these rows and columns, with their values.

    Called for two or more locations, so at least one option tells them apart.
    """
    options = []
    lines = {line for line, _ in locations}
    if len(lines) > 1:
        given = sorted(line for line in lines if line is not None)
        options.append(f"--line ({', '.join(map(str, given))})")
    columns = {column for _, column in locations}
    if len(columns) > 1:
        given = sorted(column for column in columns if column is not None)
        options.append(f"--column ({', '.join(given)})")
    return " and ".join(options)


_REVIEW_ACTIONS = {
    "add": _review_add,
    "reply": _review_thread,
    "resolve": _review_thread,
    "dismiss": _review_thread,
    "reopen": _review_thread,
    "status": _review_status,
    "acknowledge": _review_acknowledge,
}
