"""Release and review of a study, shared by study format 2 files and the canonical model."""

from datetime import date as Date
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

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
    """What a review item refers to: a file, optionally narrowed to rows and a column.

    `rows` and `column` require `file`.
    """

    file: str | None = None
    rows: dict[str, str] = Field(default_factory=dict)
    column: str | None = None

    @model_validator(mode="after")
    def file_required(self):
        if (self.rows or self.column) and self.file is None:
            raise ValueError("rows and column require file")
        return self


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
    """Content of `review.json`: review status, reviewers and items."""

    status: Literal["draft", "in_review", "approved"]
    reviewers: list[User] = Field(default_factory=list)
    items: list[ReviewItem] = Field(default_factory=list)
