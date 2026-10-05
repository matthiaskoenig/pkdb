"""study.json and review.json of study format 2."""

from datetime import date as Date
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    model_validator,
)

from pkdb.schemas.provenance import ManualCuration, StudyProvenance
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
User = Annotated[str, Field(min_length=1, max_length=255, pattern=r"^\S+$")]
Text = Annotated[str, Field(min_length=1)]
Ulid = Annotated[str, Field(pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$")]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StudyReference(Model):
    """Identifiers of the publication; the single source for which paper is curated."""

    pmid: Annotated[str, Field(pattern=r"^[1-9][0-9]*$")] | None = None
    doi: Annotated[str, Field(pattern=r"^10\.\d{4,9}/\S+$")] | None = None

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
    user: User
    rating: Annotated[
        float,
        Field(ge=0, le=5),
        PlainSerializer(_whole_as_int, return_type=float | int, when_used="json"),
    ] = 0


class Comment(Model):
    user: User
    text: Text


class Notes(Model):
    descriptions: list[Text] = Field(default_factory=list)
    comments: list[Comment] = Field(default_factory=list)


class Release(Model):
    pkdb_id: Annotated[str, Field(pattern=r"^PKDB[0-9]{5}$")]
    date: Date


class StudyMetadata(Model):
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


class ReviewTarget(Model):
    file: str | None = None
    rows: dict[str, str] = Field(default_factory=dict)
    column: str | None = None

    @model_validator(mode="after")
    def file_required(self):
        if (self.rows or self.column) and self.file is None:
            raise ValueError("rows and column require file")
        return self


class ThreadEntry(Model):
    author: User
    created: AwareDatetime
    text: Text


class ReviewItem(Model):
    id: Ulid
    kind: Literal["question", "uncertainty", "issue"]
    state: Literal["open", "resolved", "dismissed"] = "open"
    target: ReviewTarget | None = None
    acknowledges: str | None = None
    text: Text
    author: User
    agent: str | None = None
    created: AwareDatetime
    thread: list[ThreadEntry] = Field(default_factory=list)
    resolved_by: User | None = None
    resolved: AwareDatetime | None = None

    @model_validator(mode="after")
    def resolution(self):
        closed = self.state != "open"
        if closed != (self.resolved_by is not None) or closed != (
            self.resolved is not None
        ):
            raise ValueError(
                "resolved_by and resolved are set exactly when the state is resolved or dismissed"
            )
        return self


class Review(Model):
    status: Literal["draft", "in_review", "approved"]
    reviewers: list[User] = Field(default_factory=list)
    items: list[ReviewItem] = Field(default_factory=list)


def canonical_review_json(review: Review) -> str:
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
