"""Validated scientific graph and the exact rules used to prepare it."""

from pydantic import BaseModel, ConfigDict

from pkdb.schemas.study import CanonicalStudy
from pkdb.schemas.validation import ValidationReport


class PreparedStudy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    study: CanonicalStudy
    report: ValidationReport
    vocabulary_version: str
    processing_version: str
