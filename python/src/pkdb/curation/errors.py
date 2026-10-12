"""The errors of the local curation app: the one error body, its redaction and the log.

Every failed request of the app is answered with the body that `describe` builds, every text
of it without the secrets of `pkdb curate`. Failures go with their traceback to the log file
of the state directory, and an unexpected one also as one line to the terminal. Request lines
are never logged: their URLs can carry the launch token.
"""

import logging
import sys
import traceback
from collections.abc import Callable, Iterable
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from secrets import token_hex
from subprocess import CalledProcessError, TimeoutExpired
from typing import Any

#: What replaces a secret in an error body, a report and the log.
REDACTED = "[redacted]"
#: How much of the end of the stderr of a failed command an error body keeps: 2 kB.
STDERR_TAIL = 2048
#: The size of the log file before it rotates, and how many old files it keeps.
LOG_BYTES = 1024 * 1024
LOG_BACKUPS = 3


def redact(text: str, secrets: Iterable[str | None]) -> str:
    """`text` with every secret replaced by [redacted], the longest secret first.

    Empty and blank values are no secrets: replacing them would change every gap of the text.
    """
    values = {value.strip() for value in secrets if value and value.strip()}
    for value in sorted(values, key=len, reverse=True):
        text = text.replace(value, REDACTED)
    return text


class ActionFailed(Exception):
    """An action that knew what it was doing failed.

    The message names the action and the study, such as `Could not open the tables of
    caffeine/Demo2020.`; `code` names the failure in snake case, and `cause` is the error
    behind it, whose type and text become the detail of the error body.
    """

    def __init__(self, message: str, *, code: str, cause: BaseException | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.cause = cause


class MissingField(LookupError):
    """A field that the body of a request lacks."""

    def __init__(self, name: str):
        super().__init__(f'Missing field "{name}"')
        self.name = name


def required(body: dict, name: str) -> Any:
    """The field `name` of the body of a request; MissingField names it when it is missing."""
    try:
        return body[name]
    except KeyError:
        raise MissingField(name) from None


def new_request_id() -> str:
    """The 8 hex characters that name a failure in its error body, the log and the terminal."""
    return token_hex(4)


def _program(command: object) -> str:
    """The program of an argument list or a command line, without its folder."""
    if isinstance(command, list | tuple) and command:
        first = str(command[0])
    else:
        line = str(command).strip()
        if line.startswith('"'):
            first = line[1:].split('"', 1)[0]
        else:
            first = line.split(" ", 1)[0]
    return first.replace("\\", "/").rsplit("/", 1)[-1] or first


def _tail(stream: bytes | str | None) -> str:
    """The last 2 kB of the output of a command, as text."""
    if not stream:
        return ""
    data = stream.encode("utf-8", "replace") if isinstance(stream, str) else stream
    return data[-STDERR_TAIL:].decode("utf-8", "replace").strip()


def detail_of(error: BaseException) -> str:
    """The type and the text of `error`.

    For a command that failed: its program, its exit status and the end of its stderr; for a
    command that did not return: its program and the timeout.
    """
    name = type(error).__name__
    if isinstance(error, CalledProcessError):
        text = f"{_program(error.cmd)} exited with status {error.returncode}"
        if stderr := _tail(error.stderr):
            text += f"\n{stderr}"
        return f"{name}: {text}"
    if isinstance(error, TimeoutExpired):
        program = _program(error.cmd)
        return f"{name}: {program} did not return within {error.timeout:g} seconds"
    text = str(error)
    return f"{name}: {text}" if text else name


def describe(
    error: BaseException,
    *,
    action: str,
    request_id: str,
    message: str | None = None,
    code: str = "failed",
    detailed: bool = True,
    unexpected: bool = False,
    secrets: Iterable[str | None] = (),
) -> dict:
    """The error body of the local API for `error`, every text without the secrets.

    ActionFailed brings its message, its code and, as the detail, its cause. Otherwise the
    message is `message`, by default the text of the error, and the detail is the type and
    the text of the error unless `detailed` is false: a refusal that is meant for the curator
    is not repeated. Only an unexpected error has a traceback.
    """
    if isinstance(error, ActionFailed):
        text, code, cause = error.message, error.code, error.cause
    else:
        text = message if message is not None else (str(error) or type(error).__name__)
        cause = error if detailed else None
    body: dict[str, Any] = {
        "error": text,
        "code": code,
        "detail": None if cause is None else detail_of(cause),
        "action": action,
        "request_id": request_id,
        "time": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    if unexpected:
        body["traceback"] = "".join(traceback.format_exception(error))
    hidden = list(secrets)
    return {
        key: redact(value, hidden) if isinstance(value, str) else value
        for key, value in body.items()
    }


def without_traceback(body: dict) -> dict:
    """An error body without its traceback, as the activity and a job keep it."""
    return {key: value for key, value in body.items() if key != "traceback"}


class RedactingFormatter(logging.Formatter):
    """A formatter that removes the secrets from the whole record, its traceback included.

    `secrets` is asked at every record, so that a key set in the settings is redacted too.
    """

    def __init__(self, secrets: Callable[[], Iterable[str | None]]):
        super().__init__("%(asctime)s %(levelname)s %(message)s")
        self._secrets = secrets

    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record), self._secrets())


class ErrorLog:
    """The log file of the failures of one `pkdb curate`, and the line for its terminal.

    The file is `logs/curation.log` of the state directory; it rotates at 1 MB and keeps
    three old files. Each instance has a logger of its own, so engines never share a file.
    """

    def __init__(self, path: Path, secrets: Callable[[], Iterable[str | None]]):
        self.path = path
        self._secrets = secrets
        self._closed = False
        path.parent.mkdir(parents=True, exist_ok=True)
        self.handler = RotatingFileHandler(
            path,
            maxBytes=LOG_BYTES,
            backupCount=LOG_BACKUPS,
            encoding="utf-8",
            delay=True,
        )
        self.handler.setFormatter(RedactingFormatter(secrets))
        # Not registered with logging.getLogger: no other logger reaches this file.
        self._logger = logging.Logger("pkdb.curation", logging.INFO)
        self._logger.addHandler(self.handler)

    def _write(self, level: int, body: dict, error: BaseException) -> None:
        self._logger.log(
            level,
            "Error %s in %s: %s",
            body["request_id"],
            body["action"],
            body["detail"] or body["error"],
            exc_info=error,
        )

    def _terminal(self, body: dict, error: BaseException, label: str) -> None:
        """One redacted line to the terminal; a console that cannot take it is ignored."""
        cause = (
            error.cause if isinstance(error, ActionFailed) and error.cause else error
        )
        line = (
            f"Error {body['request_id']} in {label}: {type(cause).__name__} "
            f"(see {self.path})"
        )
        if self._closed:
            return
        try:
            sys.stderr.write(redact(line, self._secrets()) + "\n")
            sys.stderr.flush()
        except OSError, ValueError:
            pass

    def failed(
        self, body: dict, error: BaseException, *, label: str | None = None
    ) -> None:
        """Log a failure that the app explains, with its traceback, and name it in one terminal line.

        The label of the line is the action of the body unless given.
        """
        self._write(logging.WARNING, body, error)
        self._terminal(body, error, label or body["action"])

    def unexpected(self, body: dict, error: BaseException, *, label: str) -> None:
        """Log an unexpected error with its traceback, and name it in one terminal line."""
        self._write(logging.ERROR, body, error)
        self._terminal(body, error, label)

    def close(self) -> None:
        """Close the file; later records go nowhere, not even to the last resort handler."""
        self._closed = True
        self._logger.removeHandler(self.handler)
        self.handler.close()
        if not self._logger.handlers:
            self._logger.addHandler(logging.NullHandler())
