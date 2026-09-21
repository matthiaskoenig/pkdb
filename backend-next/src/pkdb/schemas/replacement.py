from pydantic import BaseModel, Field

from pkdb.schemas.validation import ValidationIssue


class ReplacementResult(BaseModel):
    sid: str
    created: bool
    digest: str
    counts: dict[str, int]
    warnings: list[ValidationIssue] = Field(default_factory=list)
