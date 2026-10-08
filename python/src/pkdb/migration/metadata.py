"""study.json and review.json of a converted study from its format 1 study.json."""

import re
from datetime import UTC, datetime, time

from pkdb.migration.model import Decision
from pkdb.schemas.provenance import ManualCuration
from pkdb.schemas.review import Release, Review
from pkdb.studyformat.models import (
    Comment,
    Curator,
    Notes,
    StudyMetadata,
    StudyReference,
)

# Format 1 sections and the table kind whose notes they become.
SECTION_KINDS = {
    "groupset": "subjects",
    "individualset": "subjects",
    "interventionset": "interventions",
    "outputset": "outputs",
    "dataset": "scatters",
}
PKDB_ID = re.compile(r"PKDB[0-9]{5}")
PMID = re.compile(r"[1-9][0-9]*")


def single_line(text: object) -> str:
    """Text on one line: format 2 cells and study.json texts hold no line breaks or tabs."""
    return " ".join(str(text).split())


def _comments(values: list | None, user: str) -> list[Comment]:
    pairs = []
    for value in values or []:
        if isinstance(value, list) and len(value) == 2:
            pairs.append((str(value[0]), single_line(value[1])))
        elif isinstance(value, dict):
            pairs.append((str(value.get("user") or user), single_line(value["text"])))
        else:
            pairs.append((user, single_line(value)))
    return [Comment(user=author, text=text) for author, text in pairs if text]


def _descriptions(values: list | None) -> list[str]:
    texts = [single_line(v["text"] if isinstance(v, dict) else v) for v in values or []]
    return [text for text in texts if text]


def _curators(values: list | None) -> list[Curator]:
    curators = []
    for value in values or []:
        if isinstance(value, str):
            curators.append(Curator(user=value))
        elif isinstance(value, list):
            curators.append(Curator(user=value[0], rating=value[1]))
        else:
            curators.append(Curator.model_validate(value))
    return curators


def _reference(v1: dict, reference: dict) -> StudyReference | None:
    pmid = next(
        (
            str(value)
            for value in (reference.get("pmid"), v1.get("reference"))
            if value is not None and PMID.fullmatch(str(value))
        ),
        None,
    )
    doi = reference.get("doi") or None
    if pmid is None and doi is None:
        return None
    return StudyReference(pmid=pmid, doi=doi)


def study_metadata(
    v1: dict, reference: dict, release: Release | None, *, creator_fallback: str
) -> tuple[StudyMetadata, list[Decision]]:
    """The metadata of the converted study and what a person should check."""
    creator = str(v1.get("creator") or creator_fallback)
    notes: dict[str, Notes] = {}
    for section, kind in SECTION_KINDS.items():
        content = v1.get(section) or {}
        descriptions = _descriptions(content.get("descriptions"))
        comments = _comments(content.get("comments"), creator)
        if descriptions or comments:
            merged = notes.setdefault(kind, Notes())
            merged.descriptions.extend(descriptions)
            merged.comments.extend(comments)
    decisions = []
    sid = str(v1.get("sid", ""))
    if (
        release is not None
        and v1.get("date")
        and str(v1["date"]) != release.date.isoformat()
    ):
        decisions.append(
            Decision(
                kind="registry_date",
                detail=f"study.json date {v1['date']}, registry date {release.date.isoformat()}",
            )
        )
    if release is None and PKDB_ID.fullmatch(sid):
        decisions.append(
            Decision(
                kind="registry_sid",
                detail=f"study.json sid {sid} is not in the registry",
            )
        )
    elif release is not None and PKDB_ID.fullmatch(sid) and sid != release.pkdb_id:
        decisions.append(
            Decision(
                kind="registry_sid",
                detail=f"study.json sid {sid}, registry identifier {release.pkdb_id}",
            )
        )
    access = v1.get("access", "private")
    if access == "public" and release is None:
        # Format 2: only released studies can be public.
        access = "private"
        decisions.append(
            Decision(
                kind="access_private",
                detail="Public study without a release becomes private",
            )
        )
    provenance = v1.get("provenance")
    metadata = StudyMetadata.model_validate(
        {
            "format": 2,
            "reference": _reference(v1, reference),
            "creator": creator,
            "curators": _curators(v1.get("curators")),
            "collaborators": [single_line(c) for c in v1.get("collaborators") or []],
            "licence": v1.get("licence", "closed"),
            "access": access,
            "provenance": provenance if provenance else ManualCuration(),
            "release": release,
            "descriptions": _descriptions(v1.get("descriptions")),
            "comments": _comments(v1.get("comments"), creator),
            "notes": notes,
        }
    )
    return metadata, decisions


def review(release: Release | None, approver: str | None) -> Review:
    """Released studies are approved by the approver on their release date; others are drafts."""
    if release is None:
        return Review(status="draft")
    assert approver is not None, "a registered study needs an approver"
    return Review(
        status="approved",
        reviewers=[approver],
        approved_by=approver,
        approved=datetime.combine(release.date, time(), UTC),
    )
