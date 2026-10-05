from pydantic import BaseModel, Field

from pkdb.schemas.validation import ValidationIssue


class ReplacementResult(BaseModel):
    sid: str
    created: bool
    digest: str
    counts: dict[str, int]
    warnings: list[ValidationIssue] = Field(default_factory=list)
    # Web page of the study on the server's public origin; absent for older servers.
    url: str | None = None
    # The former sid of a released study that the upload renamed.
    renamed_from: str | None = None


class PublicationState(BaseModel):
    sid: str
    digest: str
    processing_version: str
    vocabulary_version: str
    current_processing_version: str
    current_vocabulary_version: str
