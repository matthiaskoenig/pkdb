"""Stable errors raised by the public client."""

from pkdb.schemas.validation import ValidationReport


class ClientError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
        retry_after: str | None = None,
        report: ValidationReport | None = None,
        request_id: str | None = None,
        stage: str | None = None,
        persistence: str = "not_attempted",
        envelope: dict | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.retry_after = retry_after
        self.report = report
        self.request_id = request_id
        self.stage = stage
        self.persistence = persistence
        self.envelope = envelope


class CompatibilityError(ClientError):
    """Local preparation and the destination's rules do not match."""


class SourceChangedError(ValueError):
    """The folder changed after preparation; prepare it again."""
