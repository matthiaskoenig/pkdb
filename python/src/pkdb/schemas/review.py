"""Release and review of a study, shared by study format 2 files and the canonical model."""

from datetime import date as Date
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    model_serializer,
    model_validator,
)

User = Annotated[str, Field(min_length=1, max_length=255, pattern=r"^\S+$")]
Text = Annotated[str, Field(min_length=1)]
Ulid = Annotated[str, Field(pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$")]


class Model(BaseModel):
    """Base of the study format 2 JSON models; unknown fields are refused."""

    model_config = ConfigDict(extra="forbid")


class Release(Model):
    """Release of the study in PK-DB: its `PKDB` identifier and date."""

    pkdb_id: Annotated[str, Field(pattern=r"^PKDB[0-9]{5}$")]
    date: Date


class ReviewTarget(Model):
    """What a review item refers to: a file, optionally narrowed to rows and a column, or to a key.

    `rows` and `column` narrow a table. `key` names a part of a file without rows: the dataset of
    a WebPlotDigitizer project, or a review item of review.json. Each requires `file`, and `key`
    excludes `rows` and `column`.
    """

    file: str | None = None
    rows: dict[str, str] = Field(default_factory=dict)
    column: str | None = None
    key: Annotated[str, Field(min_length=1)] | None = None

    @model_validator(mode="after")
    def file_required(self):
        if (self.rows or self.column) and self.file is None:
            raise ValueError("rows and column require file")
        if self.key is not None:
            if self.file is None:
                raise ValueError("key requires file")
            if self.rows or self.column:
                raise ValueError("key excludes rows and column")
        return self

    @model_serializer(mode="wrap")
    def serialize(self, handler):
        # A target without a key serializes as before keys existed, also in the backend.
        result = handler(self)
        if result.get("key") is None:
            result.pop("key", None)
        return result


class ThreadEntry(Model):
    """A reply in the discussion thread of a review item."""

    author: User
    created: AwareDatetime
    text: Text


class ReviewItem(Model):
    """A question, uncertainty or issue raised in a review, with its state and thread.

    `resolved_by` and `resolved` are set exactly for resolved or dismissed items.
    """

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
    """Content of `review.json`: review status, reviewers, approval and items.

    `approved_by` and `approved` record the person who approved the study and
    when; they are set exactly when the status is approved, and the approver is
    one of the reviewers.
    """

    status: Literal["draft", "in_review", "approved"]
    reviewers: list[User] = Field(default_factory=list)
    approved_by: User | None = None
    approved: AwareDatetime | None = None
    items: list[ReviewItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def approval(self):
        approved = self.status == "approved"
        if approved != (self.approved_by is not None) or approved != (
            self.approved is not None
        ):
            raise ValueError(
                "approved_by and approved are set exactly when the status is approved"
            )
        if self.approved_by is not None and self.approved_by not in self.reviewers:
            raise ValueError("approved_by must be one of the reviewers")
        return self
