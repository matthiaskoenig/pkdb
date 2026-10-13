"""Decide whether a change touches code, so that a docs-only pull request skips the tests.

The `changes` job of .github/workflows/ci-cd.yml runs it with the python of the
runner:

    python3 scripts/ci_changes.py --event "$EVENT" --ref "$GITHUB_REF" \
        --output "$GITHUB_OUTPUT"

and the test jobs run when it writes `code=true`. Only a pull request can skip
them: it is compared with its base branch. Every push (a merge into develop or
main included), release tag and manual run counts as code, and so does anything
it cannot tell, so that a doubt never skips a test. A push must not skip: the
run of an earlier push may have been cancelled by this one or may have failed,
and the docs-only diff against it would then hide code that was never tested.

The runner's python may be older than the project's: keep this file compatible
with Python 3.12. ruff enforces it with the per-file target version in .ruff.toml,
for example `except A, B:` is Python 3.14 only.
"""

import argparse
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

# The client tests read this page (python/tests/studyformat/test_studyformat_export.py).
READ_BY_TESTS = frozenset({"docs/study-format.md"})
DOCS_FOLDERS = ("docs/", "release-notes/")
DOCS_FILES = frozenset({"zensical.toml"})


def is_docs(path: str) -> bool:
    """Whether `path`, relative to the repository, is documentation only."""
    if path in READ_BY_TESTS:
        return False
    if path.startswith(DOCS_FOLDERS) or path in DOCS_FILES:
        return True
    # Markdown files at the root, such as README.md
    return "/" not in path and path.endswith(".md")


def code_changed(paths: Iterable[str]) -> bool:
    """Whether the changed `paths` hold code: anything but documentation, or nothing."""
    paths = list(paths)
    return not paths or not all(is_docs(path) for path in paths)


def git(repository: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git in `repository` and keep its output."""
    return subprocess.run(
        ["git", "-C", str(repository), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def changed_paths(repository: Path, base: str) -> list[str] | None:
    """The paths that differ between `base` and HEAD, or None if git cannot tell.

    Renames count as a removal and an addition, so that a file moved from code
    into docs/ still counts as a change of code.
    """
    result = git(repository, "diff", "--name-only", "--no-renames", "-z", base, "HEAD")
    if result.returncode != 0:
        return None
    return [path for path in result.stdout.split("\0") if path]


def decide(event: str, ref: str, repository: Path) -> bool:
    """Whether the change of a run with `event` and `ref` touches code.

    Only a pull request can be docs only, see the docstring of the module.
    """
    if event != "pull_request" or ref.startswith("refs/tags/"):
        return True
    # the merge commit of a pull request has its base branch as first parent
    paths = changed_paths(repository, "HEAD^1")
    return paths is None or code_changed(paths)


def main(argv: list[str] | None = None) -> int:
    """Print `code=true` or `code=false` and append it to the file of --output."""
    parser = argparse.ArgumentParser(
        description="Decide whether a change touches code."
    )
    parser.add_argument("--event", required=True, help="github.event_name")
    parser.add_argument("--ref", required=True, help="github.ref")
    parser.add_argument("--output", type=Path, help="file to append code=... to")
    args = parser.parse_args(argv)
    code = decide(args.event, args.ref, Path.cwd())
    line = f"code={'true' if code else 'false'}"
    print(line)
    if args.output:
        with args.output.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
