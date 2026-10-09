"""The study lifecycle commands of a pkdb_data checkout."""

import argparse
from pathlib import Path


def _date(text: str):
    import datetime

    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a date YYYY-MM-DD") from None


# pkdb release and pkdb move read the vocabulary without contacting PK-DB.
OFFLINE_HELP = (
    "Never contact PK-DB; release and move always use the pinned, cached or "
    "bundled vocabulary"
)


def _add_root(command) -> None:
    command.add_argument(
        "--root",
        type=Path,
        help="Folder inside the repository with a studies folder (default: found by searching upward from the current folder)",
    )


def register(commands) -> None:
    """Add the lifecycle commands to the command line parser."""
    from pkdb.study_cli import add_format
    from pkdb.tables_cli import _vocabulary_options

    new = commands.add_parser(
        "new",
        help="Create a study folder",
        description=(
            "Create the draft study studies/SUBSTANCE/NAME with study.json, "
            "reference.json, subjects.tsv and review.json. The PDF NAME.pdf and the "
            "images NAME_SOURCE.png of papers/SUBSTANCE/NAME/ move into the study."
        ),
    )
    new.add_argument("location", metavar="SUBSTANCE/NAME")
    publication = new.add_mutually_exclusive_group(required=True)
    publication.add_argument("--pmid", help="PubMed ID of the paper")
    publication.add_argument("--doi", help="DOI of the paper")
    new.add_argument(
        "--licence",
        required=True,
        choices=("open", "closed"),
        help="Licence of the paper",
    )
    new.add_argument(
        "--access",
        required=True,
        choices=("public", "private"),
        help="Who may read the study in PK-DB",
    )
    new.add_argument(
        "--user", help="PK-DB user who creates the study (default: PKDB_USER)"
    )
    new.add_argument(
        "--agent", help="AI agent that curates the study (default: PKDB_AGENT)"
    )
    new.add_argument(
        "--agent-version", help="Version of the agent; needed with --agent"
    )
    new.add_argument(
        "--run-id", help="Identifier of the agent's run; needed with --agent"
    )
    new.add_argument(
        "--asset",
        action="append",
        default=[],
        type=Path,
        metavar="FILE",
        help="A file the agent read besides the PDF, recorded with its SHA-256; repeat for more",
    )
    _add_root(new)
    new.add_argument(
        "--offline",
        action="store_true",
        help="Create reference.json from cached metadata only",
    )
    new.add_argument(
        "--cache-dir", type=Path, help="Cache folder of reference metadata"
    )
    new.add_argument(
        "--no-issue",
        action="store_true",
        help="Leave the GitHub issue to pkdb issues sync --adopt",
    )
    add_format(new)

    move = commands.add_parser(
        "move",
        help="Rename or move a study",
        description=(
            "Move the study studies/OLD to studies/NEW and rename the files named "
            "after it, NAME.* and NAME_*: the PDF, the images, the raw tables, the "
            "digitizations and other attachments such as NAME_Supp.pdf. "
            "Review targets and provenance assets follow the files, the tables get "
            "the new name, also reference.json when it has the old name, the entry "
            "of a released study in studies/study_identifiers.json gets the new "
            "location, and the GitHub issue gets the new title. A workbook that "
            "holds edits that are not in the tables, or scratch sheets, refuses the "
            "move; otherwise it is removed, and pkdb tables open creates it again."
        ),
    )
    move.add_argument("old", metavar="OLD", help="SUBSTANCE/NAME of the study")
    move.add_argument("new", metavar="NEW", help="New SUBSTANCE/NAME of the study")
    _add_root(move)
    _vocabulary_options(move, offline_help=OFFLINE_HELP)
    add_format(move)

    release = commands.add_parser(
        "release",
        help="Give approved studies the next PKDB identifiers",
        description=(
            "Give approved studies without open review items and validation errors "
            "the next PKDB identifiers in the release block of study.json, in the "
            "order of the arguments. --access sets their access in the same write. "
            "Nothing is written when one study is refused."
        ),
    )
    release.add_argument(
        "studies",
        nargs="+",
        type=Path,
        metavar="STUDY",
        help=(
            "A study folder, or SUBSTANCE/NAME of the checkout that contains the "
            "current folder or of --root"
        ),
    )
    release.add_argument(
        "--date", type=_date, help="Release date YYYY-MM-DD (default: today in UTC)"
    )
    release.add_argument(
        "--access",
        choices=("public", "private"),
        help="Set the access of the studies with their release (default: keep it)",
    )
    _add_root(release)
    _vocabulary_options(release, offline_help=OFFLINE_HELP)
    add_format(release)

    command = commands.add_parser(
        "registry",
        help="List released studies by PKDB identifier",
        description="List released studies by PKDB identifier.",
    )
    _add_root(command)
    command.add_argument(
        "--check",
        action="store_true",
        help=(
            "Exit with 1 when studies share an identifier or an issue number, a "
            "study.json cannot be read, or studies/study_identifiers.json gives an "
            "identifier to another location or cannot be read"
        ),
    )
    add_format(command)


def run(args) -> int:
    """Run a lifecycle command and return the exit code."""
    import sys

    from pkdb.studyformat_cli import say

    try:
        if args.command == "new":
            return _new(args)
        if args.command == "move":
            return _move(args)
        if args.command == "release":
            return _release(args)
        if args.command == "registry":
            return _registry(args)
    except ValueError as error:
        say(str(error), file=sys.stderr)
        return 2
    raise AssertionError(args.command)


def github_client(repository: str, token: str | None, **options):
    """The GitHub client of the lifecycle commands; imported late to keep help fast."""
    from pkdb.issues.github import GitHub

    return GitHub(repository, token, **options)


def _on_wait(args):
    """What announces the waits for GitHub: stderr in human output, else nothing."""
    from pkdb.issues_cli import announce_wait
    from pkdb.study_cli import is_human

    return announce_wait if is_human(args) else None


def _new(args) -> int:
    from pkdb.issues.github import repository_from, token_from

    # The client is built first: a bad token fails before anything is written.
    github = None
    if not args.no_issue:
        token = token_from()
        if token is None:
            raise ValueError("Set GH_TOKEN or GITHUB_TOKEN, or pass --no-issue")
        github = github_client(repository_from(), token, on_wait=_on_wait(args))
    try:
        return _new_study(args, github)
    finally:
        if github is not None:
            github.close()


def _new_study(args, github) -> int:
    import sys

    from pkdb.identity import author_from
    from pkdb.issues.github import GitHubError
    from pkdb.lifecycle.new import NewStudyRefused, citation, create_study
    from pkdb.references import ReferenceResolver
    from pkdb.repository import PAPERS, STUDIES, location, repository_root
    from pkdb.study_cli import emit, fail, is_human
    from pkdb.studyformat.metadata import MetadataError
    from pkdb.studyformat.revision import RevisionConflict
    from pkdb.studyformat_cli import say

    # An IdentityError and a checkout without studies folder are usage errors.
    author = author_from(args.user, args.agent)
    root = repository_root(args.root or Path.cwd())
    resolver = ReferenceResolver(args.cache_dir, offline=args.offline)
    try:
        created = create_study(
            root,
            args.location,
            pmid=args.pmid,
            doi=args.doi,
            licence=args.licence,
            access=args.access,
            author=author,
            resolver=resolver,
            agent_version=args.agent_version,
            run_id=args.run_id,
            assets=args.asset,
        )
    except NewStudyRefused as refused:
        message = str(refused)
        return fail(
            args,
            {"location": args.location, "error": message},
            lambda: say(message, file=sys.stderr),
        )
    place = location(created.folder)
    issue = None
    # The study is complete: a failed or interrupted issue step keeps it.
    error, code = None, 0
    if github is not None:
        try:
            issue = _record_issue(github, root, place, created.folder)
        except (GitHubError, RevisionConflict, MetadataError) as failure:
            error = f"Created {STUDIES}/{place}, but its issue failed: {failure}."
            code = 1
        except KeyboardInterrupt:
            error = (
                f"Interrupted while giving {STUDIES}/{place} its issue; "
                "the study is kept."
            )
            code = 130
    paper = citation(created.folder)
    data = {
        "location": place,
        "path": str(created.folder),
        "moved": created.moved,
        "left": created.left,
        "misnamed": created.misnamed,
        "reference": created.reference,
        "paper": paper,
        "new_substance": created.new_substance,
        "warnings": created.warnings,
    }
    if issue is not None:
        data["issue"] = issue[0]
        data["issue_closed"] = issue[2]
    if error is not None:
        error += " Run pkdb issues sync --adopt to give it one."
        data["error"] = error
    lines = [f"Created {STUDIES}/{place}"]
    if created.new_substance:
        lines.append(f"New substance folder {created.folder.parent.name}")
    if created.moved:
        lines.append(f"Moved from {PAPERS}/{place}: {', '.join(created.moved)}")
    if created.left:
        left = [
            f"{file} (differs only in case from {created.misnamed[file]})"
            if file in created.misnamed
            else file
            for file in created.left
        ]
        lines.append(f"Left in {PAPERS}/{place}: {', '.join(left)}")
    if created.reference:
        lines.append(created.reference)
    if paper:
        lines.append(f"Paper: {paper}")
    if issue is not None:
        how = "created" if issue[1] else "adopted, closed" if issue[2] else "adopted"
        lines.append(f"Issue #{issue[0]} ({how})")
    emit(args, data, lines)
    if is_human(args):
        for warning in created.warnings:
            say(f"Warning: {warning}", file=sys.stderr)
        if error is not None:
            say(error, file=sys.stderr)
    return code


def _record_issue(
    github, root: Path, place: str, folder: Path
) -> tuple[int, bool, bool]:
    """Create or adopt the issue of a new study and write its number to study.json.

    Returns the number, whether the issue was created, and whether it is closed.
    """
    from pkdb.issues.single import issue_for_new_study
    from pkdb.issues.state import read_studies
    from pkdb.studyformat.metadata import patch_metadata, read_metadata

    revision = read_metadata(folder).revision
    studies = read_studies(root)
    claimed = {state.issue for state in studies.states if state.issue is not None}
    issue, created = issue_for_new_study(
        github, place, claimed=frozenset(claimed) | studies.claimed
    )
    patch_metadata(folder, {"issue": issue.number}, revision)
    return issue.number, created, issue.state == "closed"


def _move(args) -> int:
    from pkdb.issues.github import repository_from, token_from

    # A bad token or repository fails before anything moves.
    token = token_from()
    github = None
    if token is not None:
        github = github_client(repository_from(), token, on_wait=_on_wait(args))
    try:
        return _move_study(args, github)
    finally:
        if github is not None:
            github.close()


def _move_study(args, github) -> int:
    import sys

    from pkdb.lifecycle.move import MoveIncomplete, MoveRefused, move_study
    from pkdb.lifecycle.registry import REGISTRY_PATH
    from pkdb.repository import STUDIES, location, repository_root
    from pkdb.study_cli import emit, fail, is_human
    from pkdb.studyformat_cli import say
    from pkdb.tables_cli import _vocabulary

    root = repository_root(args.root or Path.cwd())
    vocabulary = _vocabulary(args, root)
    if vocabulary is None:
        return 2
    old = args.old.removesuffix("/")
    error = None
    try:
        moved = move_study(root, old, args.new, vocabulary)
    except (MoveRefused, MoveIncomplete) as failure:
        # A move that failed after the renames is reported with what it did.
        done = failure.moved if isinstance(failure, MoveIncomplete) else None
        if done is None:
            message = str(failure)
            return fail(
                args,
                {"from": old, "location": args.new, "error": message},
                lambda: say(message, file=sys.stderr),
            )
        moved, error = done, str(failure)
    place = location(moved.folder)
    lines = [f"Moved {STUDIES}/{old} to {STUDIES}/{place}"]
    lines += [f"Renamed {before} to {after}" for before, after in moved.renamed]
    if moved.workbook is not None:
        lines.append(
            f"Removed {moved.workbook}; pkdb tables open creates the workbook again"
        )
    if moved.targets:
        plural = "" if moved.targets == 1 else "s"
        lines.append(f"Updated {moved.targets} review target{plural}")
    if moved.assets:
        plural = "" if moved.assets == 1 else "s"
        lines.append(f"Updated {moved.assets} provenance asset{plural} of study.json")
    if moved.reference:
        lines.append("Updated the name in reference.json")
    if moved.registry:
        lines.append(f"Updated {moved.pkdb_id} in {REGISTRY_PATH}")
    warnings, renamed, interrupted = _rename_issue(github, moved.issue, place)
    if moved.issue is None and moved.pkdb_id is None:
        # The server follows a move by the issue number or the PKDB identifier.
        warnings.append(
            "The study has no issue and no release, so PK-DB cannot follow the "
            f"move: if PK-DB stores it as {old}, uploading {place} is refused. "
            "Then move it back, run pkdb issues sync --adopt, upload it, and move "
            "it again."
        )
    if renamed:
        lines.append(f"Issue #{moved.issue} renamed to {place}")
    data = {
        "from": old,
        "location": place,
        "path": str(moved.folder),
        "renamed": [{"from": before, "to": after} for before, after in moved.renamed],
        "targets": moved.targets,
        "assets": moved.assets,
        "reference": moved.reference,
        "registry": moved.registry,
        "workbook": moved.workbook,
        "issue": moved.issue,
        "issue_renamed": renamed,
        "warnings": warnings,
    }
    if error is not None:
        data["error"] = error
    emit(args, data, lines)
    if is_human(args):
        for warning in warnings:
            say(f"Warning: {warning}", file=sys.stderr)
        if error is not None:
            say(error, file=sys.stderr)
    if interrupted:
        return 130
    return 0 if error is None else 1


def _rename_issue(
    github, issue: int | None, place: str
) -> tuple[list[str], bool, bool]:
    """Give the issue of a moved study its new title.

    Returns the warnings, whether the issue was renamed, and whether Ctrl+C
    interrupted the rename; the move is complete either way.
    """
    from pkdb.issues.github import GitHubError
    from pkdb.issues.single import rename_issue

    later = "pkdb issues sync renames it later"
    if issue is None:
        return [], False, False
    if github is None:
        return (
            [f"Set GH_TOKEN or GITHUB_TOKEN to rename issue #{issue} now; {later}"],
            False,
            False,
        )
    try:
        rename_issue(github, issue, place)
    except GitHubError as error:
        return [f"Issue #{issue} was not renamed: {error}; {later}"], False, False
    except KeyboardInterrupt:
        return [f"Renaming issue #{issue} was interrupted; {later}"], False, True
    return [], True, False


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
    ] or ["No released studies."]
    lines += problems
    lines += [f"Error: {error}" for error in result.errors]
    emit(args, data, lines)
    return 1 if args.check and (problems or result.errors) else 0


def _release_folders(
    values: list[Path], root_option: Path | None
) -> tuple[Path, list[Path]]:
    """The checkout and the study folders of the arguments, or a ValueError.

    An argument is the path of a study folder, or SUBSTANCE/NAME of the
    checkout that contains the current folder or of --root.
    """
    from pkdb.repository import STUDIES, repository_root

    folders: list[Path] = []
    roots: set[Path] = set()
    for value in values:
        path = value.resolve()
        as_path = path if _is_study(path) else None
        as_location = _checkout_study(value, root_option)
        if as_path and as_location and as_path != as_location:
            raise ValueError(
                f"{value} is the folder of another study than {STUDIES}/{value} of "
                f"the checkout; give the path of the folder you mean, such as {path}"
            )
        folder = as_path or as_location
        if folder is None:
            if _is_location(value):
                raise ValueError(
                    f"Neither {value} nor {STUDIES}/{value} of the checkout is a "
                    "study format 2 folder"
                )
            raise ValueError(f"{value} is not a study format 2 folder")
        if folder in folders:
            raise ValueError(f"{value} is given twice")
        try:
            root = repository_root(folder)
        except ValueError as error:
            raise ValueError(f"{value}: {error}") from None
        if folder.parent.parent != root / STUDIES:
            raise ValueError(f"{value} is not a folder {STUDIES}/SUBSTANCE/NAME")
        folders.append(folder)
        roots.add(root)
    if len(roots) > 1:
        raise ValueError("The studies lie in different checkouts")
    return roots.pop(), folders


def _is_study(folder: Path) -> bool:
    from pkdb.studyformat.validation import is_v2_folder

    return folder.is_dir() and is_v2_folder(folder)


def _is_location(value: Path) -> bool:
    """Whether an argument has the form SUBSTANCE/NAME."""
    parts = value.parts
    return (
        not value.is_absolute()
        and len(parts) == 2
        and not any(part.startswith(".") for part in parts)
    )


def _checkout_study(value: Path, root_option: Path | None) -> Path | None:
    """The study folder SUBSTANCE/NAME of the checkout, or None."""
    from pkdb.repository import STUDIES, repository_root

    if not _is_location(value):
        return None
    try:
        root = repository_root(root_option or Path.cwd())
    except ValueError:
        return None
    folder = root / STUDIES / value
    if folder.is_symlink() or not _is_study(folder):
        return None
    return folder.resolve()


def _say_all(lines: list[str]) -> None:
    import sys

    from pkdb.studyformat_cli import say

    for line in lines:
        say(line, file=sys.stderr)


def _release(args) -> int:
    import datetime

    from pkdb.lifecycle.release import (
        LargestIdentifierUnknown,
        ReleaseConflict,
        ReleaseRefused,
        release,
    )
    from pkdb.study_cli import emit, fail
    from pkdb.tables_cli import _vocabulary

    root, folders = _release_folders(args.studies, args.root)
    vocabulary = _vocabulary(args, root)
    if vocabulary is None:
        return 2
    on = args.date or datetime.datetime.now(datetime.UTC).date()
    try:
        done = release(root, folders, vocabulary, on=on, access=args.access)
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
    except LargestIdentifierUnknown as unknown:
        message = str(unknown)
        return fail(args, {"error": message}, lambda: _say_all([message]))
    except ReleaseConflict as conflict:
        data = {
            "error": str(conflict),
            "released": [
                {
                    "location": item.location,
                    "pkdb_id": item.pkdb_id,
                    "access": item.access,
                }
                for item in conflict.released
            ],
        }
        lines = [str(conflict)]
        return fail(args, data, lambda: _say_all(lines))
    data = {
        "released": [
            {
                "location": item.location,
                "pkdb_id": item.pkdb_id,
                "date": on.isoformat(),
                "access": item.access,
            }
            for item in done
        ]
    }
    lines = [f"{item.location}: {item.pkdb_id}" for item in done]
    if args.access is None:
        # A released study may be public; without --access it stays as it was.
        lines += [
            f"{item.location} stays private. Set its access to public with pkdb "
            "study patch to publish it; pkdb release --access public does both "
            "at once."
            for item in done
            if item.access == "private"
        ]
    emit(args, data, lines)
    return 0
