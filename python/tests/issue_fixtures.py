"""Format 2 study folders and GitHub issues for the issue sync tests."""

from collections.abc import Sequence
from pathlib import Path

from pkdb.issues.github import Issue
from pkdb.studyformat.jsonio import dump_json


def study(
    root: Path,
    location: str,
    *,
    issue: int | None = None,
    status: str = "draft",
    curators: Sequence[str] = ("ana",),
    reviewers: Sequence[str] = (),
    release: dict | None = None,
) -> Path:
    folder = root / "studies" / location
    folder.mkdir(parents=True)
    metadata = {
        "format": 2,
        "reference": {"pmid": "123"},
        "creator": curators[0] if curators else "ana",
        "curators": [{"user": user, "rating": 3} for user in curators],
        "licence": "open",
        "access": "private",
    }
    if issue is not None:
        metadata["issue"] = issue
    if release is not None:
        metadata["release"] = release
    (folder / "study.json").write_text(dump_json(metadata), encoding="utf-8")
    review = {"status": status, "reviewers": list(reviewers)}
    if status == "approved":
        review |= {"approved_by": reviewers[0], "approved": "2026-10-01T00:00:00Z"}
    (folder / "review.json").write_text(dump_json(review), encoding="utf-8")
    return folder


def table(folder: Path, file: str, rows: Sequence[dict[str, str]]) -> None:
    """Write a table of the study `folder` with the columns of the first row."""
    header = list(rows[0])
    lines = [
        "\t".join(header),
        *("\t".join(row[name] for name in header) for row in rows),
    ]
    (folder / file).write_text("\n".join(lines) + "\n", encoding="utf-8")


def issue(
    number, title, *, state="open", reason=None, labels=(), assignees=()
) -> Issue:
    return Issue(number, title, state, reason, tuple(labels), tuple(assignees))
