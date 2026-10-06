"""study.json, review.json and reference.json of study format 2."""

from collections.abc import Callable
from typing import Annotated, Literal

from pydantic import AfterValidator, Field, PlainSerializer, model_validator

from pkdb.references import ReferenceError, normalize_doi, normalize_pmid
from pkdb.schemas.provenance import ManualCuration, StudyProvenance
from pkdb.schemas.review import Model, Release, Review, Text, User
from pkdb.schemas.review import ReviewItem as ReviewItem
from pkdb.schemas.review import ReviewTarget as ReviewTarget
from pkdb.schemas.review import ThreadEntry as ThreadEntry
from pkdb.schemas.review import Ulid as Ulid
from pkdb.schemas.study import Reference
from pkdb.studyformat.jsonio import dump_json

TABLE_KINDS = (
    "subjects",
    "interventions",
    "characteristica",
    "outputs",
    "timecourses",
    "scatters",
)
TableKind = Literal[
    "subjects", "interventions", "characteristica", "outputs", "timecourses", "scatters"
]


def _normalizable(normalizer: Callable[[str], str], kind: str) -> AfterValidator:
    """Accept an identifier that PK-DB can normalize, unchanged.

    The server matches publications by normalized identifiers, so one that has
    no normalized form cannot be published.
    """

    def check(value: str) -> str:
        try:
            normalizer(value)
        except ReferenceError:
            raise ValueError(
                f"{value!r} is not a valid {kind}, also after decoding percent escapes"
            ) from None
        return value

    return AfterValidator(check)


PubMedId = Annotated[str, _normalizable(normalize_pmid, "PubMed ID")]
Doi = Annotated[str, _normalizable(normalize_doi, "DOI")]


class StudyReference(Model):
    """Identifiers of the publication; the single source for which paper is curated."""

    pmid: Annotated[PubMedId, Field(pattern=r"^[1-9][0-9]*$")] | None = None
    doi: Annotated[Doi, Field(pattern=r"^10\.\d{4,9}/\S+$")] | None = None

    @model_validator(mode="after")
    def identifier(self):
        if self.pmid is None and self.doi is None:
            raise ValueError(
                "Give a pmid or a doi, or remove reference for a manual reference"
            )
        return self


def _whole_as_int(value: float) -> float | int:
    return int(value) if value.is_integer() else value


class Curator(Model):
    """A user who curated the study, with a rating from 0 to 5."""

    user: User
    rating: Annotated[
        float,
        Field(ge=0, le=5),
        PlainSerializer(_whole_as_int, return_type=float | int, when_used="json"),
    ] = 0


class Comment(Model):
    """A free-text comment of a user."""

    user: User
    text: Text


class Notes(Model):
    """Descriptions and comments about one table kind."""

    descriptions: list[Text] = Field(default_factory=list)
    comments: list[Comment] = Field(default_factory=list)


class ReferenceSnapshot(Reference):
    """Content of `reference.json`: the canonical reference of the publication.

    Its PubMed ID and DOI must have the normalized form by which the server
    matches publications.
    """

    pmid: PubMedId | None = None
    doi: Doi | None = None


class StudyMetadata(Model):
    """Content of `study.json`: reference, people, access, provenance, release and notes."""

    format: Literal[2]
    reference: StudyReference | None = None
    creator: User
    curators: list[Curator] = Field(default_factory=list)
    collaborators: list[Text] = Field(default_factory=list)
    licence: Literal["open", "closed"]
    access: Literal["public", "private"]
    provenance: StudyProvenance = Field(default_factory=ManualCuration)
    issue: Annotated[int, Field(gt=0)] | None = None
    release: Release | None = None
    descriptions: list[Text] = Field(default_factory=list)
    comments: list[Comment] = Field(default_factory=list)
    notes: dict[TableKind, Notes] = Field(default_factory=dict)


def _without_empty(data: dict, keys: tuple[str, ...]) -> dict:
    return {key: value for key, value in data.items() if key not in keys or value}


def canonical_study_json(study: StudyMetadata) -> str:
    """Canonical `study.json` text without empty values or the default provenance."""
    data = study.model_dump(mode="json", exclude_none=True)
    if data["provenance"] == ManualCuration().model_dump(mode="json"):
        del data["provenance"]
    notes = {}
    for kind in TABLE_KINDS:
        if kind in data["notes"]:
            entry = _without_empty(data["notes"][kind], ("descriptions", "comments"))
            if entry:
                notes[kind] = entry
    data["notes"] = notes
    return dump_json(
        _without_empty(
            data, ("curators", "collaborators", "descriptions", "comments", "notes")
        )
    )


def canonical_review_json(review: Review) -> str:
    """Canonical `review.json` text with items sorted by id and no empty optional values."""
    data = review.model_dump(mode="json", exclude_none=True)
    items = []
    for item in sorted(data["items"], key=lambda entry: entry["id"]):
        if "target" in item:
            target = _without_empty(item["target"], ("rows",))
            if target:
                item["target"] = target
            else:
                del item["target"]
        items.append(_without_empty(item, ("thread",)))
    data["items"] = items
    return dump_json(_without_empty(data, ("reviewers", "items")))
