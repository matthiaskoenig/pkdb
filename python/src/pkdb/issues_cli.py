"""The `issues` command: keep one GitHub issue per study format 2 study."""

import json
import math
import os
import sys
from pathlib import Path


def github_client(repository: str, token: str | None, **options):
    """The GitHub client of the sync; imported late to keep help fast."""
    from pkdb.issues.github import GitHub

    return GitHub(repository, token, **options)


def roster(endpoint: str, api_key: str):
    """The curators of the PK-DB server with their GitHub logins."""
    from pkdb.client import Client

    with Client(endpoint, api_key) as client:
        return client.curators()


def register(commands) -> None:
    """Add the `issues` command to the command line parser."""
    command = commands.add_parser(
        "issues",
        help="Keep one GitHub issue per study format 2 study",
        description="Keep one GitHub issue per study format 2 study.",
    )
    actions = command.add_subparsers(dest="action", required=True)
    sync = actions.add_parser(
        "sync",
        help="Align title, labels, assignees and state of the issue of every study",
        description="Align title, labels, assignees and state of the issue of every study.",
    )
    sync.add_argument(
        "--root",
        type=Path,
        help="Folder inside the repository with a studies folder (default: found by searching upward from the current folder)",
    )
    sync.add_argument(
        "--repository",
        help="GitHub repository OWNER/NAME (default: PKDB_ISSUES_REPO or matthiaskoenig/pkdb_data)",
    )
    sync.add_argument(
        "--adopt",
        action="store_true",
        help="Give studies without an issue an existing or a new issue (writes study.json and review.json)",
    )
    sync.add_argument("--user", help="PK-DB user of --adopt (default: PKDB_USER)")
    sync.add_argument("--agent", help="AI agent of --adopt (default: PKDB_AGENT)")
    sync.add_argument(
        "--endpoint",
        default=os.environ.get("PKDB_ENDPOINT"),
        help="PK-DB server of the roster (default: PKDB_ENDPOINT)",
    )
    sync.add_argument(
        "--dry-run", action="store_true", help="Only show the plan; change nothing"
    )
    sync.add_argument(
        "--format",
        dest="output",
        choices=("human", "json"),
        default="human",
        help="Output format (default: human)",
    )


def _print_human(result) -> None:
    """The plan of a dry run, then the warnings, errors and the summary.

    A real run has already printed each adoption and change as progress.
    """
    from pkdb.issues.sync import INTERRUPTED, adoption_line, change_line
    from pkdb.terminal import safe_text

    if result.dry_run:
        for item in result.adopted:
            print(safe_text(adoption_line(item, dry_run=True)))
        for change in result.plan.changes:
            print(safe_text(change_line(change)))
    for warning in result.warnings:
        print(safe_text(f"Warning: {warning}"))
    for error in result.errors:
        print(safe_text(f"Error: {error}"), file=sys.stderr)
    if result.stopped == INTERRUPTED:
        print(INTERRUPTED, file=sys.stderr)
    elif result.stopped is not None:
        print(safe_text(f"Stopped: {result.stopped}"), file=sys.stderr)
    print(_summary(result))


def _summary(result) -> str:
    """The counts of a run, such as `Adopted 3 issues and changed 12 issues.`

    Adoption counts of zero are left out; a dry run says what it would do.
    """
    from pkdb.issues import counted

    adopted = sum(not item.created for item in result.adopted)
    duplicates = sum(len(item.duplicates) for item in result.adopted)
    changed = len(result.plan.changes) if result.dry_run else result.applied
    counts = [
        ("adopt", "adopted", adopted, "issue"),
        ("create", "created", len(result.adopted) - adopted, "issue"),
        ("close", "closed", duplicates, "duplicate"),
    ]
    actions = [
        f"{planned if result.dry_run else done} {counted(count, noun)}"
        for planned, done, count, noun in counts
        if count
    ]
    actions.append(
        f"{'change' if result.dry_run else 'changed'} {counted(changed, 'issue')}"
    )
    text = ", ".join(actions[:-1]) + (" and " if len(actions) > 1 else "") + actions[-1]
    summary = (
        f"Dry run: would {text}." if result.dry_run else f"{text[0].upper()}{text[1:]}."
    )
    if result.format_1:
        skipped = counted(result.format_1, "format 1 study", "format 1 studies")
        summary += f" Skipped {skipped}."
    return summary


def _progress(line: str) -> None:
    from pkdb.terminal import safe_text

    print(safe_text(line), file=sys.stderr, flush=True)


def announce_wait(seconds: float, reason: str) -> None:
    """Print a wait for GitHub to stderr."""
    from pkdb.issues import counted

    waiting = counted(math.ceil(seconds), "second")
    print(f"Waiting {waiting}: {reason}.", file=sys.stderr, flush=True)


def run(args) -> int:
    """Run the `issues` command and return the exit code."""
    from pkdb.errors import ClientError
    from pkdb.identity import author_from
    from pkdb.issues.github import repository_from, token_from
    from pkdb.issues.sync import INTERRUPTED, sync
    from pkdb.repository import repository_root
    from pkdb.terminal import safe_text

    try:
        api_key = os.environ.get("PKDB_API_KEY")
        if not args.endpoint or not api_key:
            raise ValueError(
                "Set PKDB_ENDPOINT and PKDB_API_KEY: the sync reads GitHub logins from the PK-DB roster"
            )
        token = token_from()
        if token is None and not args.dry_run:
            raise ValueError("Set GH_TOKEN or GITHUB_TOKEN to change GitHub issues")
        repository = repository_from(args.repository)
        root = repository_root(args.root or Path.cwd())
        author = None  # an IdentityError is a ValueError: a usage error
        if args.adopt:
            author = author_from(args.user, args.agent)
        curators = roster(args.endpoint, api_key)
        if not curators:
            # A wrong server would otherwise unassign every issue.
            raise ValueError("The PK-DB roster is empty; check PKDB_ENDPOINT")
        if author is not None and author.user not in {c.username for c in curators}:
            raise ValueError(f"User {author.user} is not in the PK-DB roster")
        human = args.output == "human"
        on_wait = announce_wait if human else None
        with github_client(repository, token, on_wait=on_wait) as github:
            result = sync(
                root,
                github,
                curators,
                adopt=args.adopt,
                author=author,
                dry_run=args.dry_run,
                progress=_progress if human else None,
            )
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except ValueError as error:
        print(safe_text(str(error)), file=sys.stderr)
        return 2
    except ClientError as error:
        print(safe_text(str(error)), file=sys.stderr)
        return 1
    except OSError as error:
        print(safe_text(f"Cannot sync the issues: {error}"), file=sys.stderr)
        return 1
    if args.output == "json":
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        _print_human(result)
    if result.stopped == INTERRUPTED:
        return 130
    return 0 if result.ok else 1
