"""Format 2 study folders of a pkdb_data checkout for the lifecycle tests."""

from pathlib import Path

from pkdb.studyformat.jsonio import dump_json


def released_study(
    root: Path,
    location: str,
    *,
    pkdb_id=None,
    date="2026-09-28",
    issue=None,
    status="draft",
) -> Path:
    folder = root / "studies" / location
    folder.mkdir(parents=True)
    metadata = {
        "format": 2,
        "reference": {"pmid": "123"},
        "creator": "ana",
        "licence": "open",
        "access": "private",
    }
    if issue is not None:
        metadata["issue"] = issue
    if pkdb_id is not None:
        metadata["release"] = {"pkdb_id": pkdb_id, "date": date}
    (folder / "study.json").write_text(
        dump_json(metadata), encoding="utf-8", newline=""
    )
    review = {"status": status}
    if status == "approved":
        review |= {
            "reviewers": ["bo"],
            "approved_by": "bo",
            "approved": "2026-10-01T00:00:00Z",
        }
    (folder / "review.json").write_text(dump_json(review), encoding="utf-8", newline="")
    return folder
