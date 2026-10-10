"""Throwaway pkdb_data git checkouts for the tests of pkdb check."""

import json
import subprocess
from pathlib import Path

from pkdb.studyformat.formatter import format_folder

# A fixed identity and no signing or hooks, so the user's git configuration cannot interfere.
SETTINGS = (
    *("-c", "user.name=t", "-c", "user.email=t@example.org"),
    *("-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false"),
    *("-c", "core.hooksPath=/dev/null", "-c", "init.defaultBranch=main"),
)


def git(root: Path, *args: str) -> str:
    """Run git in `root` and return its output."""
    return subprocess.run(
        ["git", "-C", str(root), *SETTINGS, *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout


def format_2_study(root: Path, location: str, files: dict[str, str | bytes]) -> Path:
    """The formatted format 2 study `studies/<location>` made of the files of the `Example` study.

    The files named after the study are named after the folder, and formatting
    writes the folder name into the study column of the tables.
    """
    folder = root / "studies" / location
    folder.mkdir(parents=True)
    for file, content in files.items():
        if file.startswith("Example"):
            file = folder.name + file.removeprefix("Example")
        path = folder / file
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8", newline="")
    assert format_folder(folder).ok
    return folder


def format_1_study(root: Path, location: str) -> Path:
    """A format 1 study `studies/<location>`: a study.json with a sid."""
    folder = root / "studies" / location
    folder.mkdir(parents=True)
    metadata = {"sid": "123", "name": folder.name, "pmid": "123"}
    (folder / "study.json").write_text(json.dumps(metadata), encoding="utf-8")
    return folder


def study_checkout(
    root: Path,
    files: dict[str, str | bytes],
    *locations: str,
    format_1: tuple[str, ...] | list[str] = (),
) -> tuple[Path, dict[str, Path]]:
    """A git repository at `root` with one commit of format 2 studies and format 1 studies.

    Returns the root and the format 2 study folders by location.
    """
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q")
    studies = {where: format_2_study(root, where, files) for where in locations}
    for where in format_1:
        format_1_study(root, where)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "Add the studies")
    return root, studies
