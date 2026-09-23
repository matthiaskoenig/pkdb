"""Stable errors raised by the public client."""

from pkdb.schemas.validation import ValidationReport


class ClientError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        report: ValidationReport | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.report = report


class CompatibilityError(ClientError):
    """Local preparation and the destination's rules do not match."""


class SourceChangedError(ValueError):
    """The folder changed after preparation; prepare it again."""
