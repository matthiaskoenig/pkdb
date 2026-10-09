"""The `issues` command: keep one GitHub issue per study format 2 study."""

import json
import os
import sys
from pathlib import Path


def github_client(repository: str, token: str | None):
    """The GitHub client of the sync; imported late to keep help fast."""
    from pkdb.issues.github import GitHub

    return GitHub(repository, token)


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
        "--root", type=Path, help="Repository with a studies folder (default: current)"
    )
    sync.add_argument(
        "--repository",
        help="GitHub repository OWNER/NAME (default: PKDB_ISSUES_REPO or matthiaskoenig/pkdb_data)",
    )
    sync.add_argument(
        "--adopt",
        action="store_true",
        help="Give studies without an issue an existing or a new issue (writes study.json)",
    )
    sync.add_argument("--user", help="PK-DB user of --adopt (default: PKDB_USER)")
    sync.add_argument("--agent", help="AI agent of --adopt (default: PKDB_AGENT)")
    sync.add_argument("--endpoint", default=os.environ.get("PKDB_ENDPOINT"))
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


def _adoption_line(item) -> str:
    if item.created:
        return f"{item.study}: new issue"
    parts = [f"adopt #{item.number}"]
    if item.renamed:
        parts.append("rename")
    parts += [f"close #{number} as duplicate" for number in item.duplicates]
    if item.in_review:
        parts.append("set review status in_review")
    return f"{item.study}: {', '.join(parts)}"


def _change_line(change) -> str:
    parts = []
    if change.title is not None:
        parts.append("title")
    if change.add_labels or change.remove_labels:
        labels = [f"+{name}" for name in change.add_labels]
        labels += [f"-{name}" for name in change.remove_labels]
        parts.append(f"labels {' '.join(labels)}")
    if change.assignees is not None:
        parts.append(
            f"assignees {' '.join(change.assignees)}"
            if change.assignees
            else "no assignees"
        )
    if change.state is not None:
        parts.append("close" if change.state == "closed" else "reopen")
    return f"#{change.number} {change.study}: {', '.join(parts)}"


def _print_human(result) -> None:
    from pkdb.terminal import safe_text

    for item in result.adopted:
        print(safe_text(_adoption_line(item)))
    for change in result.plan.changes:
        print(safe_text(_change_line(change)))
    for warning in result.warnings:
        print(safe_text(f"Warning: {warning}"))
    for error in result.errors:
        print(safe_text(f"Error: {error}"), file=sys.stderr)
    if result.dry_run:
        print(f"Dry run: {len(result.plan.changes)} changes.")
    else:
        print(f"Changed {result.applied} issues.")


def run(args) -> int:
    """Run the `issues` command and return the exit code."""
    from pkdb.errors import ClientError
    from pkdb.identity import author_from
    from pkdb.issues.github import GitHubError, repository_from, token_from
    from pkdb.issues.sync import sync
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
        if author is not None and author.user not in {c.username for c in curators}:
            raise ValueError(f"User {author.user} is not in the PK-DB roster")
        with github_client(repository, token) as github:
            result = sync(
                root,
                github,
                curators,
                adopt=args.adopt,
                author=author,
                dry_run=args.dry_run,
            )
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except ValueError as error:
        print(safe_text(str(error)), file=sys.stderr)
        return 2
    except (ClientError, GitHubError) as error:
        print(safe_text(str(error)), file=sys.stderr)
        return 1
    except OSError as error:
        print(safe_text(f"Cannot sync the issues: {error}"), file=sys.stderr)
        return 1
    if args.output == "json":
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        _print_human(result)
    return 0 if result.ok else 1
