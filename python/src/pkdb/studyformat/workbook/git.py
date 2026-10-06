"""Whether git ignores the workbook and its sync state file, which are never committed.

The TSV tables are the files to commit. The tables commands and the curation
app warn when the study is in a git work tree that tracks the workbook or its
state file, or does not ignore them.
"""

import shutil
import subprocess
from pathlib import Path

from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.issues import make_issue
from pkdb.studyformat.workbook.base import state_path

# The .gitignore lines for the workbook and for its sync state file.
GITIGNORE_WORKBOOK = "*.xlsx"
GITIGNORE_STATE = ".*.pkdb-base"
TIMEOUT = 30


def _git(path: Path, *arguments: str) -> int | None:
    """The exit code of git run beside a path, None when git is missing or fails to run."""
    git = shutil.which("git")
    if git is None:
        return None
    try:
        completed = subprocess.run(
            [git, *arguments, "--", path.name],
            cwd=path.parent,
            capture_output=True,
            timeout=TIMEOUT,
            check=False,
        )
    except OSError, subprocess.SubprocessError:
        return None
    return completed.returncode


def ignored_by_git(path: Path) -> bool | None:
    """Whether git ignores a path; None when git is missing or the path is outside a work tree.

    git never ignores a file that it tracks.
    """
    # 1 means not ignored; 128 means no work tree or another error.
    return {0: True, 1: False}.get(_git(path, "check-ignore", "-q"))


def tracked_by_git(path: Path) -> bool | None:
    """Whether git tracks a path; None when git is missing or the path is outside a work tree."""
    # 1 means not tracked; 128 means no work tree or another error.
    return {0: True, 1: False}.get(_git(path, "ls-files", "--error-unmatch"))


def git_issues(workbook: Path) -> list[ValidationIssue]:
    """Warnings when the study is in a git work tree that tracks or does not ignore the workbook or its state file."""
    state = state_path(workbook)
    tracked = [path for path in (workbook, state) if tracked_by_git(path)]
    missing = [
        (path, line)
        for path, line in ((workbook, GITIGNORE_WORKBOOK), (state, GITIGNORE_STATE))
        if path not in tracked and ignored_by_git(path) is False
    ]
    issues = []
    if tracked:
        names = " and ".join(path.name for path in tracked)
        issues.append(
            make_issue(
                "workbook_tracked",
                f"Git tracks {names}; commit only the TSV tables",
                file=workbook.name,
                hint="Stop tracking them, keeping the files, with:",
                candidates=[f"git rm --cached {path.name}" for path in tracked],
            )
        )
    if missing:
        names = " and ".join(path.name for path, _ in missing)
        issues.append(
            make_issue(
                "workbook_not_ignored",
                f"Git does not ignore {names}; commit only the TSV tables",
                file=workbook.name,
                hint="Add these lines to the .gitignore file of the repository:",
                candidates=[line for _, line in missing],
            )
        )
    return issues
