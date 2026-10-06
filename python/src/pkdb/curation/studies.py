"""Summaries of format 2 study folders for the curation engine.

Every reader is lenient: a file that does not parse gives None or empty values, never an exception.
"""

from pathlib import Path

from pydantic import ValidationError

from pkdb.schemas.review import Review
from pkdb.studyformat.jsonio import JsonFileError, load_json
from pkdb.studyformat.models import StudyMetadata


def _read(path: Path) -> object | None:
    try:
        if path.is_symlink() or not path.is_file():
            return None
        return load_json(path.read_bytes())
    except JsonFileError, OSError:
        return None


def _object(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _user(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _curator_names(value: object) -> list[str]:
    names = []
    for item in value if isinstance(value, list) else []:
        name = _user(_object(item).get("user") if isinstance(item, dict) else item)
        if name:
            names.append(name)
    return names


def _review(folder: Path) -> tuple[str | None, int]:
    data = _read(folder / "review.json")
    try:
        review = Review.model_validate(data)
    except ValidationError:
        return None, 0
    return review.status, sum(1 for item in review.items if item.state == "open")


def _title(folder: Path) -> str | None:
    title = _object(_read(folder / "reference.json")).get("title")
    return title if isinstance(title, str) else None


def study_summary(folder: Path) -> dict:
    folder = Path(folder)
    raw = _object(_read(folder / "study.json"))
    try:
        study = StudyMetadata.model_validate(raw)
        creator = study.creator
        curators = [item.user for item in study.curators]
        issue = study.issue
        release = study.release.model_dump(mode="json") if study.release else None
        provenance = study.provenance.model_dump(mode="json")
    except ValidationError:
        creator = _user(raw.get("creator"))
        curators = _curator_names(raw.get("curators"))
        issue = raw.get("issue")
        issue = (
            issue if isinstance(issue, int) and not isinstance(issue, bool) else None
        )
        release = _object(raw.get("release"))
        release = (
            {"pkdb_id": release.get("pkdb_id"), "date": release.get("date")}
            if release.get("pkdb_id")
            else None
        )
        provenance = _object(raw.get("provenance"))
    kind = provenance.get("kind") if isinstance(provenance.get("kind"), str) else None
    status, open_items = _review(folder)
    return {
        "title": _title(folder),
        "review_status": status,
        "open_items": open_items,
        "curators": curators,
        "creator": creator,
        "release": release,
        "issue": issue,
        "provenance": {"kind": kind}
        | (
            {"method": provenance.get("method")} if kind == "automatic_curation" else {}
        ),
        "ai": kind == "automatic_curation",
    }
