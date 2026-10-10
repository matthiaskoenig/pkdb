"""study.json and review.json of a converted study from its format 1 study.json."""

import re
from datetime import UTC, datetime, time

from pkdb.migration.model import Decision, NotConverted
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
PMID = re.compile(r"[1-9][0-9]*")


def single_line(text: object) -> str:
    """Text on one line: format 2 cells and study.json texts hold no line breaks or tabs."""
    return " ".join(str(text).split())


def _malformed(study: str, field: str, problem: str) -> NotConverted:
    return NotConverted("study_json", f"{study}: study.json {field} {problem}")


def _list(values: object, study: str, field: str) -> list:
    """The list of a study.json field; absent is empty."""
    if values is None:
        return []
    if not isinstance(values, list):
        raise _malformed(study, field, f"must be a list, not {type(values).__name__}")
    return values


def _comments(values: object, user: str, study: str, field: str) -> list[Comment]:
    pairs = []
    for index, value in enumerate(_list(values, study, field)):
        if isinstance(value, list) and len(value) == 2:
            pairs.append((str(value[0]), single_line(value[1])))
        elif isinstance(value, dict):
            if "text" not in value:
                raise _malformed(study, f"{field}[{index}]", "has no text")
            pairs.append((str(value.get("user") or user), single_line(value["text"])))
        else:
            pairs.append((user, single_line(value)))
    return [Comment(user=author, text=text) for author, text in pairs if text]


def _descriptions(values: object, study: str, field: str) -> list[str]:
    texts = []
    for index, value in enumerate(_list(values, study, field)):
        if isinstance(value, dict):
            if "text" not in value:
                raise _malformed(study, f"{field}[{index}]", "has no text")
            value = value["text"]
        texts.append(single_line(value))
    return [text for text in texts if text]


def _curators(values: object, study: str) -> list[Curator]:
    curators = []
    for index, value in enumerate(_list(values, study, "curators")):
        if isinstance(value, str):
            curators.append(Curator(user=value))
        elif isinstance(value, list):
            if len(value) != 2:
                raise _malformed(
                    study, f"curators[{index}]", "must be a pair [user, rating]"
                )
            curators.append(Curator(user=value[0], rating=value[1]))
        elif isinstance(value, dict):
            curators.append(Curator.model_validate(value))
        else:
            raise _malformed(
                study, f"curators[{index}]", "must be a name, a pair or an object"
            )
    return curators


def _pmid(value: object) -> str | None:
    return str(value) if value is not None and PMID.fullmatch(str(value)) else None


def _reference(v1: dict, reference: dict) -> StudyReference | None:
    """The PubMed ID of study.json and the DOI of its reference.json snapshot.

    study.json names the publication; reference.json only describes it. A
    snapshot with another PubMed ID describes another publication, so its DOI
    is not kept, and `sync_reference` replaces the snapshot.
    """
    stated, snapshot = _pmid(v1.get("reference")), _pmid(reference.get("pmid"))
    pmid = stated or snapshot
    doi = reference.get("doi") or None
    if snapshot is not None and snapshot != pmid:
        doi = None
    if pmid is None and doi is None:
        return None
    return StudyReference(pmid=pmid, doi=doi)


def study_metadata(
    v1: dict,
    reference: dict,
    release: Release | None,
    *,
    creator_fallback: str,
    study: str,
) -> tuple[StudyMetadata, list[Decision]]:
    """The metadata of the converted study and what a person should check."""
    creator = str(v1.get("creator") or creator_fallback)
    decisions = []
    if not v1.get("creator"):
        decisions.append(
            Decision(
                kind="creator_fallback",
                detail=f"study.json has no creator; {creator} is the creator",
            )
        )
    notes: dict[str, Notes] = {}
    for section, kind in SECTION_KINDS.items():
        content = v1.get(section) or {}
        if not isinstance(content, dict):
            raise _malformed(study, section, "must be an object")
        descriptions = _descriptions(
            content.get("descriptions"), study, f"{section}.descriptions"
        )
        comments = _comments(
            content.get("comments"), creator, study, f"{section}.comments"
        )
        if descriptions or comments:
            merged = notes.setdefault(kind, Notes())
            merged.descriptions.extend(descriptions)
            merged.comments.extend(comments)
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
            "curators": _curators(v1.get("curators"), study),
            "collaborators": [
                single_line(c)
                for c in _list(v1.get("collaborators"), study, "collaborators")
            ],
            "licence": v1.get("licence", "closed"),
            "access": access,
            "provenance": provenance if provenance else ManualCuration(),
            "release": release,
            "descriptions": _descriptions(
                v1.get("descriptions"), study, "descriptions"
            ),
            "comments": _comments(v1.get("comments"), creator, study, "comments"),
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
