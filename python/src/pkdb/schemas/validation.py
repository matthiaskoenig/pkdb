"""Serializable, source-aware validation results shared by every interface."""

import json
import math
import re
from typing import Literal, NoReturn
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    PrivateAttr,
    model_serializer,
    model_validator,
)

from pkdb.schemas.source import SourceLocation

# Guidance belongs to the diagnostic contract, not a terminal renderer.
ISSUE_REGISTRY = {
    "unknown_measurement": (
        "vocabulary",
        "validate",
        "Check the supplied measurement against the active vocabulary.",
    ),
    "unknown_method": (
        "vocabulary",
        "validate",
        "Check the supplied method against the active vocabulary.",
    ),
    "negative_value": (
        "scientific",
        "validate",
        "Check the value and measurement type against the publication.",
    ),
    "unit_dimension": (
        "scientific",
        "validate",
        "Check the source unit and supported dimensions.",
    ),
    "unknown_image": (
        "reference",
        "parse",
        "Include the referenced attachment or correct its reference.",
    ),
    "unknown_column": (
        "schema",
        "parse",
        "Compare the column reference with the source table headers.",
    ),
}
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_SECRET_KEYS = {
    "password",
    "token",
    "api_key",
    "authorization",
    "cookie",
    "secret",
    "access_token",
}


def _bounded(value, depth=0):
    if depth > 5:
        return "[omitted]"
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, str):
        return _CONTROL.sub("", value)[:512]
    if isinstance(value, dict):
        return {
            _CONTROL.sub("", str(k))[:128]: _bounded(v, depth + 1)
            for k, v in list(value.items())[:50]
            if _CONTROL.sub("", str(k)).lower() not in _SECRET_KEYS
        }
    if isinstance(value, (list, tuple)):
        values = [_bounded(v, depth + 1) for v in value[:50]]
        return tuple(values) if isinstance(value, tuple) else values
    return value


class Suggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str
    message: str
    candidates: list[JsonValue] = Field(default_factory=list)
    command: str | None = None


class RelatedSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    source: SourceLocation


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    severity: Literal["error", "warning"] = "error"
    message: str
    source: SourceLocation | None = None
    category: str | None = None
    stage: str | None = None
    field: str | None = None
    actual: JsonValue = None
    expected: dict[str, JsonValue] = Field(default_factory=dict)
    context: dict[str, JsonValue] = Field(default_factory=dict)
    related_sources: list[RelatedSource] = Field(default_factory=list)
    suggestions: list[Suggestion] = Field(default_factory=list)
    documentation_url: str | None = None

    _content_truncated: bool = PrivateAttr(default=False)

    @model_validator(mode="after")
    def constrain_diagnostics(self):
        for name in (
            "code",
            "message",
            "category",
            "stage",
            "field",
            "actual",
            "expected",
            "context",
            "documentation_url",
        ):
            value = getattr(self, name)
            bounded = _bounded(value)
            if value != bounded:
                self._content_truncated = True
                setattr(self, name, bounded)
        for name, limit in (("suggestions", 10), ("related_sources", 10)):
            values = getattr(self, name)
            if len(values) > limit:
                self._content_truncated = True
                values = values[:limit]
            checked = []
            for value in values:
                original = value.model_dump(mode="python")
                bounded = _bounded(original)
                if name == "suggestions":
                    bounded["candidates"] = bounded["candidates"][:10]
                if bounded != original:
                    self._content_truncated = True
                checked.append(type(value).model_validate(bounded))
            setattr(self, name, checked)
        sources = ([self.source] if self.source else []) + [
            related.source for related in self.related_sources
        ]
        for source in sources:
            original = source.model_dump(mode="python")
            bounded = _bounded(original)
            # Reports expose bundle names, never operator filesystem paths.
            filename = bounded["file"].replace("\\", "/")
            if (
                filename.startswith("/")
                or ".." in filename.split("/")
                or (len(filename) > 1 and filename[1] == ":")
            ):
                bounded["file"] = filename.rsplit("/", 1)[-1]
            bounded["path"] = tuple(bounded["path"])
            if bounded != original:
                self._content_truncated = True
                replacement = SourceLocation.model_validate(bounded)
                if source is self.source:
                    self.source = replacement
                for related in self.related_sources:
                    if related.source is source:
                        related.source = replacement
        if self.documentation_url:
            try:
                url = urlsplit(self.documentation_url)
                safe = (
                    url.scheme in {"http", "https"}
                    and bool(url.hostname)
                    and not url.username
                    and not url.password
                )
            except ValueError:
                safe = False
            if not safe:
                self.documentation_url = None
                self._content_truncated = True
        if defaults := ISSUE_REGISTRY.get(self.code):
            self.category = self.category or defaults[0]
            self.stage = self.stage or defaults[1]
            if not self.suggestions:
                self.suggestions = [
                    Suggestion(kind="inspect_source", message=defaults[2])
                ]
        return self

    @model_serializer(mode="wrap")
    def serialize(self, handler):
        result = handler(self)
        if "actual" not in self.model_fields_set:
            result.pop("actual", None)
        return result

    def legacy_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "source": self.source.legacy_dict() if self.source else None,
        }


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    issues: list[ValidationIssue] = Field(default_factory=list)
    truncated: bool = False
    error_count: int = 0
    warning_count: int = 0
    returned_issue_count: int = 0
    omitted_issue_count: int = 0
    complete: bool = True
    stopped_reason: str | None = None

    @model_validator(mode="after")
    def validate_counts(self):
        return self.refresh_counts()

    def refresh_counts(self):
        bounded_reason = _bounded(self.stopped_reason)
        if bounded_reason != self.stopped_reason:
            self.stopped_reason = bounded_reason
            self.truncated = True
        self.error_count = max(
            self.error_count, sum(i.severity == "error" for i in self.issues)
        )
        self.warning_count = max(
            self.warning_count, sum(i.severity == "warning" for i in self.issues)
        )
        self.returned_issue_count = len(self.issues)
        self.omitted_issue_count = max(
            self.omitted_issue_count,
            self.error_count + self.warning_count - len(self.issues),
        )
        self.truncated = (
            self.truncated
            or self.omitted_issue_count > 0
            or any(i._content_truncated for i in self.issues)
        )
        return self

    def legacy_dict(self) -> dict:
        return {
            "issues": [issue.legacy_dict() for issue in self.issues],
            "truncated": self.truncated,
            "error_count": self.error_count,
        }

    def finalize(self, max_issues: int = 1000) -> ValidationReport:
        if max_issues < 1:
            raise ValueError("max_issues must be positive")
        self.issues.sort(
            key=lambda i: (
                i.source.file if i.source else "",
                i.source.sheet or "" if i.source else "",
                i.source.row or 0 if i.source else 0,
                i.source.column or "" if i.source else "",
                i.code,
            )
        )
        self.refresh_counts()
        if len(self.issues) > max_issues:
            self.issues = self.issues[:max_issues]
        budget = 2 * 1024 * 1024 - 16384
        kept = []
        for issue in self.issues:
            size = (
                len(
                    json.dumps(
                        issue.model_dump(mode="json"),
                        ensure_ascii=True,
                        allow_nan=False,
                    ).encode()
                )
                + 2
            )
            if size > budget:
                break
            kept.append(issue)
            budget -= size
        self.issues = kept
        self.refresh_counts()
        return self

    @property
    def valid(self) -> bool:
        return (
            self.complete
            and self.error_count == 0
            and not any(issue.severity == "error" for issue in self.issues)
        )


class StudyValidationError(ValueError):
    def __init__(self, report: ValidationReport):
        self.report = report.finalize()
        super().__init__("; ".join(issue.message for issue in report.issues))


def fail(
    code: str, message: str, source: SourceLocation | None = None, **details
) -> NoReturn:
    raise StudyValidationError(
        ValidationReport(
            error_count=1,
            complete=False,
            stopped_reason=code,
            issues=[
                ValidationIssue(
                    code=code,
                    message=message,
                    source=source,
                    **details,
                )
            ],
        )
    )
