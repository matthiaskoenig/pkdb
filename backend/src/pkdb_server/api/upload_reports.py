"""Negotiated, source-aware upload responses, including transport middleware errors."""

import json
import logging
from typing import Any, Literal, cast
from uuid import uuid4

from pydantic import BaseModel, ConfigDict
from starlette.responses import JSONResponse

from pkdb.domain.validation import PROCESSING_VERSION
from pkdb.schemas.validation import Suggestion, ValidationIssue, ValidationReport

log = logging.getLogger(__name__)


class UploadReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report_version: Literal[2] = 2
    request_id: str
    operation: Literal["upload", "validate"]
    status: Literal["succeeded", "failed", "unknown"]
    stage: str
    study: dict[str, str] | None = None
    persistence: Literal["not_attempted", "not_saved", "created", "replaced", "unknown"]
    summary: str
    report: ValidationReport
    result: dict[str, Any] | None = None
    versions: dict[str, Any] | None = None


ERRORS = {
    400: (
        "malformed_request",
        "schema",
        "Check the request format and report version.",
    ),
    401: ("authentication_required", "permission", "Provide a valid personal API key."),
    403: (
        "upload_forbidden",
        "permission",
        "Check the API key studies:write scope and study permissions.",
    ),
    409: (
        "publication_conflict",
        "compatibility",
        "Refresh the vocabulary and check processing compatibility before retrying.",
    ),
    413: (
        "upload_too_large",
        "limit",
        "Reduce the bundle size or contact the server administrator.",
    ),
    422: (
        "invalid_bundle",
        "schema",
        "Correct the reported source fields and validate again.",
    ),
    429: (
        "rate_limit",
        "limit",
        "Wait for the Retry-After interval before making another request.",
    ),
    503: (
        "capacity_unavailable",
        "limit",
        "Wait for the Retry-After interval before making another request.",
    ),
}


# Endpoint-specific guidance supplements scientific diagnostics from the shared registry.
REQUEST_GUIDANCE = {
    "bundle_fields": "Send exactly one study JSON part and one reference JSON part, with attachments in files parts.",
    "invalid_json": "Check that the study and reference parts contain valid JSON objects, with no duplicate keys or nonfinite numbers.",
    "duplicate_json_key": "Remove the duplicate JSON property after checking which value the source intended.",
    "sid_mismatch": "Make the request URL study identifier match the sid in the study JSON part.",
    "invalid_file": "Send attachments as named files multipart parts.",
    "invalid_filename": "Use unique attachment basenames without path separators or parent-directory components.",
    "invalid_bundle": "Check the study, reference, and attachment fields against the source bundle schema.",
}


def complete_guidance(report, stage):
    for issue in report.issues:
        if not issue.category:
            issue.category = "parsing" if stage in {"read", "parse"} else "schema"
        if not issue.stage:
            issue.stage = stage
        if not issue.suggestions:
            issue.suggestions = [
                Suggestion(
                    kind="inspect_source",
                    message=REQUEST_GUIDANCE.get(
                        issue.code,
                        "Inspect the reported field and rule, correct the source if needed, and validate again. If the cause is unclear, contact the administrator with the request ID.",
                    ),
                )
            ]
    return report


def request_field_issues(details):
    """Keep typed request coordinates without echoing raw inputs or error messages."""
    issues = []
    messages = {
        "missing": "This request field is required.",
        "string_type": "This request field must be a string.",
        "int_type": "This request field must be an integer.",
        "float_type": "This request field must be a number.",
        "list_type": "This request field must be an array.",
        "dict_type": "This request field must be an object.",
        "json_invalid": "The request contains malformed JSON.",
        "extra_forbidden": "This request field is not permitted.",
    }
    for detail in details:
        if not isinstance(detail, dict):
            continue
        kind = detail.get("type", "invalid_request_field")
        if not isinstance(kind, str):
            kind = "invalid_request_field"
        location = detail.get("loc", [])
        if not isinstance(location, (list, tuple)):
            location = []
        location = [item for item in location if isinstance(item, (str, int))][:50]
        expected = {}
        if kind == "missing":
            expected["required"] = True
        elif kind in {
            "string_type",
            "int_type",
            "float_type",
            "list_type",
            "dict_type",
        }:
            expected["type"] = {
                "string_type": "string",
                "int_type": "integer",
                "float_type": "number",
                "list_type": "array",
                "dict_type": "object",
            }[kind]
        issues.append(
            ValidationIssue(
                code="invalid_request_field",
                category="schema",
                stage="parse",
                message=messages.get(
                    kind, "This request field does not meet its schema constraints."
                ),
                field=str(location[-1]) if location else None,
                context={"request_location": location},
                expected=expected,
                suggestions=[
                    Suggestion(
                        kind="review_request",
                        message="Correct this request field using the API source bundle schema and submit again.",
                    )
                ],
            )
        )
    return issues


def build_report(scope, status_code, payload):
    state = scope["state"]
    operation = "validate" if scope["method"] == "POST" else "upload"
    stage = state.get("upload_stage", "transfer")
    succeeded = status_code < 400
    if "issues" in payload:
        report = ValidationReport.model_validate(
            {k: v for k, v in payload.items() if k != "valid"}
        )
    elif succeeded:
        report = ValidationReport(issues=payload.get("warnings", []))
    elif status_code in {400, 422} and isinstance(payload.get("detail"), list):
        issues = request_field_issues(payload["detail"])
        if not issues:
            issues = [
                ValidationIssue(
                    code="invalid_request_field",
                    message="The request does not match the source bundle schema.",
                )
            ]
        report = ValidationReport(
            issues=issues,
            complete=False,
            stopped_reason="The request schema was rejected before study validation.",
        )
    else:
        code, category, advice = ERRORS.get(
            status_code,
            (
                "internal_error",
                "internal",
                "Contact the administrator with this request ID.",
            ),
        )
        detail = payload.get("detail")
        # Only deliberate HTTP summaries are exposed; unexpected failures are generic.
        message = (
            detail
            if isinstance(detail, str) and status_code < 500
            else "The server could not complete the request."
        )
        details = {}
        if status_code == 409 and detail in {
            "processing_version_mismatch",
            "vocabulary_mismatch",
            "vocabulary_changed",
        }:
            code = detail
            stage = "compatibility"
            message = (
                "Client and server processing or vocabulary versions do not match."
            )
            details = {"expected": state.get("upload_versions", {})}
        if status_code == 413 and "upload_limit_actual" in state:
            details.update(
                actual=state["upload_limit_actual"],
                expected={"maximum_bytes": state["upload_limit_maximum"]},
            )
        report = ValidationReport(
            error_count=1,
            complete=False,
            stopped_reason="Request could not complete all validation and save stages.",
            issues=[
                ValidationIssue(
                    code=code,
                    message=message,
                    category=category,
                    stage=stage,
                    suggestions=[{"kind": "review_request", "message": advice}],
                    **details,
                )
            ],
        )
    report = complete_guidance(report, stage)
    persistence = "not_attempted" if operation == "validate" else "not_saved"
    result = None
    if succeeded and operation == "upload":
        result = {
            **payload,
            "warnings": [issue.model_dump(mode="json") for issue in report.issues],
        }
        persistence = "created" if payload["created"] else "replaced"
    elif status_code >= 500 and state.get("upload_save_started"):
        persistence = state.get("upload_persistence", "unknown")
    status = (
        "succeeded"
        if succeeded
        else "unknown"
        if persistence == "unknown"
        else "failed"
    )
    summary = (
        "Study validation completed."
        if operation == "validate"
        else f"Study {persistence.replace('_', ' ')}."
    )
    if not succeeded:
        summary = (
            "Study outcome is unknown; check the server before retrying."
            if persistence == "unknown"
            else f"Request failed with {report.error_count} error(s)."
        )
    envelope = UploadReport(
        request_id=state["upload_request_id"],
        operation=operation,
        status=status,
        stage=stage,
        study=state.get("upload_study"),
        persistence=persistence,
        summary=summary,
        report=report.finalize(),
        result=result,
        versions=state.get("upload_versions"),
    )
    # Successful results repeat warnings for Python API compatibility. Account for
    # both copies in the response budget, retaining total discovered counts.
    while (
        len(envelope.model_dump_json().encode()) > 2 * 1024 * 1024
        and envelope.report.issues
    ):
        envelope.report.issues = envelope.report.issues[
            : len(envelope.report.issues) // 2
        ]
        envelope.report.refresh_counts()
        if envelope.result is not None:
            envelope.result = {
                **envelope.result,
                "warnings": [
                    issue.model_dump(mode="json") for issue in envelope.report.issues
                ],
            }
    return envelope


class UploadReports:
    """Wrap only public bundle endpoints; preserve all legacy bodies byte-for-byte."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        target = scope["type"] == "http" and (
            scope.get("method") == "POST"
            and path == "/api/v2/studies/validate"
            or scope.get("method") == "PUT"
            and path.startswith("/api/v2/studies/")
            and "/" not in path.removeprefix("/api/v2/studies/")
        )
        if not target:
            return await self.app(scope, receive, send)
        state = scope.setdefault("state", {})
        state["upload_request_id"] = uuid4().hex
        state["upload_versions"] = {"server_processing_version": PROCESSING_VERSION}
        requested = dict(scope.get("headers", [])).get(b"x-pkdb-report-version")
        negotiated = requested not in (None, b"1")
        start: dict[str, Any] | None = None
        body = bytearray()
        sent = False

        async def capture(message):
            nonlocal start, sent
            if message["type"] == "http.response.start":
                message = {
                    **message,
                    "headers": [
                        *message.get("headers", []),
                        (b"x-request-id", state["upload_request_id"].encode()),
                    ],
                }
                start = message
                if not negotiated:
                    await send(message)
            elif message["type"] == "http.response.body" and negotiated:
                body.extend(message.get("body", b""))
                if not message.get("more_body", False):
                    assert start is not None
                    payload = json.loads(body)
                    report = build_report(scope, start["status"], payload)
                    response = JSONResponse(
                        report.model_dump(mode="json"),
                        status_code=cast(int, start["status"]),
                    )
                    response.raw_headers.extend(
                        (k, v)
                        for k, v in start["headers"]
                        if k.lower() not in {b"content-length", b"content-type"}
                    )
                    sent = True
                    await response(scope, receive, send)
            else:
                await send(message)

        if requested not in (None, b"1", b"2"):
            return await JSONResponse(
                {"detail": "Unsupported report version. Supported versions: 1, 2."},
                status_code=400,
            )(scope, receive, capture)
        try:
            await self.app(scope, receive, capture)
        except Exception:
            if not negotiated or sent:
                raise
            log.exception("Upload request failed: %s", state["upload_request_id"])
            body.clear()
            await JSONResponse({"detail": "Internal server error"}, status_code=500)(
                scope, receive, capture
            )
