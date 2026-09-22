"""Serializable, source-aware validation results shared by every interface."""

from typing import Literal, NoReturn

from pydantic import BaseModel, ConfigDict, Field

from pkdb.schemas.source import SourceLocation


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    severity: Literal["error", "warning"] = "error"
    message: str
    source: SourceLocation | None = None


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    issues: list[ValidationIssue] = Field(default_factory=list)
    truncated: bool = False
    error_count: int = 0

    @property
    def valid(self) -> bool:
        return self.error_count == 0 and not any(
            issue.severity == "error" for issue in self.issues
        )


class StudyValidationError(ValueError):
    def __init__(self, report: ValidationReport):
        self.report = report
        super().__init__("; ".join(issue.message for issue in report.issues))


def fail(code: str, message: str, source: SourceLocation | None = None) -> NoReturn:
    raise StudyValidationError(
        ValidationReport(
            error_count=1,
            issues=[
                ValidationIssue(
                    code=code,
                    message=message,
                    source=source,
                )
            ],
        )
    )
