"""Loopback-only HTTP transport for the local curation workspace."""

import hashlib
import json
import mimetypes
import re
import secrets
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from pkdb.curation.actions import Action, action_of
from pkdb.curation.engine import WorkspaceError
from pkdb.curation.errors import (
    ActionFailed,
    MissingField,
    describe,
    new_request_id,
    redact,
    required,
)
from pkdb.curation.jobs import ResumeRefused
from pkdb.curation.metadata import roster
from pkdb.curation.state import THEMES
from pkdb.curation.studies import AmbiguousStudy, StudyFile, UnsafeFile
from pkdb.identity import IdentityError, UserMismatch
from pkdb.references import ReferenceError
from pkdb.schemas.validation import StudyValidationError
from pkdb.studyformat.load import BeyondLimits
from pkdb.studyformat.metadata import MetadataError
from pkdb.studyformat.review_edit import ReviewError
from pkdb.studyformat.revision import RevisionConflict

MAX_BODY = 1024 * 1024
# What a refused request may still send so that the client receives the refusal.
DRAIN_LIMIT = 4 * MAX_BODY
ASSETS = Path(__file__).parent / "static"
AVATARS = Path(__file__).parent / "avatars"
NONCE_PLACEHOLDER = b"__PKDB_NONCE__"
# The theme of the state in the `pkdb-theme` meta tag of index.html, which the app reads before
# it mounts, so that its first paint has the theme that the curator chose.
THEME_PLACEHOLDER = b"__PKDB_THEME__"
# The `code` of the 403 for a missing or stale CSRF token; the app then takes a fresh token from
# the state and sends the action once more.
ACTION_TOKEN = "action_token"
#: The size of the pieces in which the file route sends a file: 64 kB, the size of the ranges
#: that PDF.js asks for.
CHUNK = 64 * 1024
#: The seconds that the file route waits for a browser to take one piece: one that keeps the
#: connection but stops reading frees its thread and the file then, as if it went away.
SEND_TIMEOUT = 30
#: The media types of the scripts of the app, whatever the table of the system says: a module
#: script, such as the worker of PDF.js, runs only as JavaScript, and `mimetypes` reads the
#: Windows registry, which can map `.js` to text/plain.
SCRIPT_TYPES = {".js": "text/javascript", ".mjs": "text/javascript"}
#: One byte range of a Range header (RFC 9110): its first and last byte, or its last bytes.
BYTE_RANGE = re.compile(r"bytes=(\d*)-(\d*)", re.ASCII | re.IGNORECASE)


def _csp(nonce: str | None) -> str:
    style = "style-src 'self'" + (f" 'nonce-{nonce}'" if nonce else "")
    return (
        f"default-src 'self'; script-src 'self'; {style}; "
        "img-src 'self' https://avatars.githubusercontent.com data:; "
        "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    )


def _matches(received, expected):
    return isinstance(received, str) and secrets.compare_digest(
        received.encode("utf-8"), expected.encode("utf-8")
    )


def _segments(path):
    """The segments of a URL path, each percent-decoded after splitting on `/`.

    LookupError for an empty segment, `.`, `..`, a segment with a separator or NUL, or one that
    is not UTF-8.
    """
    segments = []
    for segment in path.split("/"):
        try:
            value = unquote(segment, errors="strict")
        except UnicodeDecodeError:
            raise LookupError("Invalid path segment") from None
        if value in {"", ".", ".."} or any(char in value for char in "/\\\0"):
            raise LookupError("Invalid path segment")
        segments.append(value)
    return segments


def _route_version(version, route):
    """The version of a table or source route of a study from the version of the study.

    The study version covers every file of the study, so it versions each table and source too.
    """
    return hashlib.sha256(json.dumps([version, *route]).encode()).hexdigest()


class RangeNotSatisfiable(ValueError):
    """A Range header whose one range starts at or beyond the end of the file (416)."""


def byte_range(header: str | None, size: int) -> tuple[int, int] | None:
    """The one byte range `(start, end)`, end exclusive, that a Range header asks of `size` bytes.

    None asks for the whole file: no header, another unit, several ranges, or a range that is
    not valid, all of which RFC 9110 lets a server answer with the whole file; so do a number
    of more digits than `int` reads and the last bytes of an empty file. RangeNotSatisfiable
    for a range that starts at or beyond the end, or for the last 0 bytes.
    """
    if header is None:
        return None
    match = BYTE_RANGE.fullmatch(header.strip())
    if match is None:
        return None
    try:
        first, last = (int(digits) if digits else None for digits in match.groups())
    except ValueError:
        # More digits than `int` reads (4300).
        return None
    if first is None:
        # `bytes=-N`: the last N bytes.
        if last is None:
            return None
        if last == 0:
            raise RangeNotSatisfiable(header)
        # RFC 9110 lets an empty file satisfy it, but no Content-Range can name its bytes.
        return None if size == 0 else (max(0, size - last), size)
    if last is not None and last < first:
        return None
    if first >= size:
        raise RangeNotSatisfiable(header)
    return first, size if last is None else min(last + 1, size)


def content_disposition(name: str) -> str:
    """`inline` with the name of the file: printable ASCII in `filename`, the exact name in
    `filename*` (RFC 6266), so that any name makes a valid header."""
    fallback = "".join(
        char if " " <= char <= "~" and char not in '"\\' else "_" for char in name
    )
    if fallback == name:
        return f'inline; filename="{name}"'
    return f"inline; filename=\"{fallback}\"; filename*=UTF-8''{quote(name, safe='')}"


@dataclass(frozen=True)
class Outcome:
    """How the server answers an error: the status, the code, and what else it does."""

    status: int
    code: str
    #: The text of the error is the message for the curator, and no detail repeats it.
    own_text: bool = False
    #: Fields that the app reads besides the error body, such as the issues of a refusal.
    extra: dict = field(default_factory=dict)
    #: An error that the server did not expect: 500 with a traceback, logged and printed.
    unexpected: bool = False
    #: A failure that the log keeps with its traceback and the activity of its study lists.
    logged: bool = False


class UnserializableResult(RuntimeError):
    """A result of the app that is not JSON: a bug, so an unexpected error, not a bad request."""


def _dump(value) -> bytes:
    """The JSON of a result; the one place where a result that is no JSON is classified."""
    try:
        return json.dumps(value).encode()
    except (TypeError, ValueError) as error:
        raise UnserializableResult(f"The result is not JSON: {error}") from error


def _issues(issues) -> list[dict]:
    return [issue.model_dump(mode="json") for issue in issues]


def _outcome(error: Exception, *, reading: bool) -> Outcome:
    """How the server answers `error`; `reading` for a GET, where a missing file is not found."""
    match error:
        case ActionFailed():
            return Outcome(500, error.code, logged=True)
        case RevisionConflict():
            # The file changed since the app read it: the current document to reload.
            extra = {
                "file": error.file,
                "revision": error.current,
                "content": error.content,
            }
            return Outcome(409, "revision_conflict", own_text=True, extra=extra)
        case MetadataError() | ReviewError():
            code = (
                error.code
                if isinstance(error, ReviewError) and error.code
                else "invalid_document"
            )
            extra = {"issues": _issues(error.issues)}
            return Outcome(422, code, own_text=True, extra=extra)
        case UserMismatch():
            # `error` stays the code, as `pkdb study --json` reports it and the app reads it.
            extra = {"error": UserMismatch.code, "message": str(error)}
            return Outcome(403, UserMismatch.code, own_text=True, extra=extra)
        case IdentityError():
            extra = {"error": "no_user", "message": str(error)}
            return Outcome(403, "no_user", own_text=True, extra=extra)
        case AmbiguousStudy():
            extra = {"paths": error.paths}
            return Outcome(409, "ambiguous_study", own_text=True, extra=extra)
        case BeyondLimits():
            return Outcome(413, "beyond_limits", own_text=True)
        case StudyValidationError():
            extra = {"issues": _issues(error.report.issues)}
            return Outcome(422, "unreadable_study", own_text=True, extra=extra)
        case ReferenceError():
            return Outcome(400, "reference_refused", own_text=True)
        case WorkspaceError():
            return Outcome(400, "workspace_refused", own_text=True)
        case UnsafeFile():
            return Outcome(400, "unsafe_file", own_text=True)
        case ResumeRefused():
            return Outcome(400, "resume_refused", own_text=True)
        case MissingField():
            return Outcome(400, "missing_field", own_text=True)
        case KeyError() | IndexError():
            # A field of the body is read with `required`: any other KeyError is a bug, and
            # so is an index out of range.
            return Outcome(500, "unexpected", unexpected=True)
        case LookupError():
            return Outcome(404, "not_found", own_text=True)
        case FileNotFoundError() if reading:
            return Outcome(404, "not_found", own_text=True)
        case ValueError() | TypeError():
            return Outcome(400, "invalid_request", logged=True)
        case OSError():
            return Outcome(400, "file_error", logged=True)
        case _:
            return Outcome(500, "unexpected", unexpected=True)


def _redacted(value, hidden):
    """`value` with the secrets removed from every text of it, nested ones included."""
    if isinstance(value, str):
        return redact(value, hidden)
    if isinstance(value, list):
        return [_redacted(item, hidden) for item in value]
    if isinstance(value, dict):
        return {key: _redacted(item, hidden) for key, item in value.items()}
    return value


def _message(error: Exception) -> str | None:
    """The message of a refusal for the curator; None keeps the text of the error."""
    if isinstance(error, FileNotFoundError) and error.filename:
        return f"{error.filename} does not exist"
    return None


class CurationServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = True

    def __init__(self, engine, port=0):
        self.engine = engine
        self.bootstrap_lock = threading.Lock()
        self.bootstrap_token = secrets.token_urlsafe(32)
        self.session_token = secrets.token_urlsafe(32)
        self.csrf_token = secrets.token_urlsafe(32)
        # The JSON of the last state that GET /local/state built, with its version.
        self.state_cache: tuple[str, bytes] | None = None
        # The tokens never reach an error body, a report or the log.
        engine.protect(self.bootstrap_token, self.session_token, self.csrf_token)
        super().__init__(("127.0.0.1", port), Handler)
        self.origin = f"http://127.0.0.1:{self.server_port}"
        # A browser keeps the cookies of 127.0.0.1 for all ports: the name of the session
        # cookie has the port, so that two instances keep separate sessions.
        self.cookie_name = f"pkdb_curation_{self.server_port}"
        self.launch_url = f"{self.origin}/#token={self.bootstrap_token}"

    def server_close(self):
        super().server_close()
        self.engine.close()


class Handler(BaseHTTPRequestHandler):
    server: CurationServer

    def log_message(self, format, *args):
        # Request URLs and payloads must never leak bootstrap tokens or API keys.
        pass

    def _head(
        self,
        status,
        *,
        content_type="application/json",
        length=0,
        cookie=None,
        etag=None,
        nonce=None,
        headers=None,
    ):
        """Send the status and the headers of a reply, with the security headers of every reply.

        `headers` adds headers of the reply, such as its Content-Range. OSError when the client
        went away or stopped reading.
        """
        self.send_response(status)
        if status != 304:
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(length))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        if etag:
            self.send_header("ETag", etag)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", _csp(nonce))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def _reply(
        self,
        status,
        value,
        *,
        content_type="application/json",
        cookie=None,
        etag=None,
        nonce=None,
        headers=None,
    ):
        data = value if isinstance(value, bytes) else _dump(value)
        try:
            self._head(
                status,
                content_type=content_type,
                length=len(data),
                cookie=cookie,
                etag=etag,
                nonce=nonce,
                headers=headers,
            )
            if status != 304:
                self.wfile.write(data)
        except OSError:
            # The client went away or stopped reading, such as a socket that timed out: the
            # action is done or failed on its own, and a reply that nobody reads is neither a
            # failure of it nor worth a log record.
            self.close_connection = True

    def _versioned(self, version, build):
        """Reply with the JSON that `build` returns, or 304 when the client has `version`."""
        etag = f'"{version}"'
        if self.headers.get("If-None-Match") == etag:
            self._reply(304, b"", etag=etag)
            return
        self._reply(200, build(), etag=etag)

    def _json(self, value):
        """Reply with a JSON value whose ETag is the hash of its JSON."""
        data = _dump(value)
        self._versioned(hashlib.sha256(data).hexdigest(), lambda: data)

    def _state(self):
        """Reply with the state of the engine, built and serialized once per version; a poll
        with the current version gets 304 without either."""
        server, engine = self.server, self.server.engine
        # Read before the build, so that the state is at least as new as its version.
        version = engine.state_version()

        def build():
            cached = server.state_cache
            if cached is None or cached[0] != version:
                state = {**engine.snapshot(), "csrf_token": server.csrf_token}
                cached = server.state_cache = (version, _dump(state))
            return cached[1]

        self._versioned(version, build)

    def _reject(self, status, message, *, code, headers=None):
        """Refuse a request before it runs, with the error body of the local API."""
        action = action_of(self.command, urlsplit(self.path).path)
        self._reply(
            status,
            describe(
                ActionFailed(message, code=code),
                action=action.text(),
                request_id=new_request_id(),
                secrets=self.server.engine.secrets(),
            ),
            headers=headers,
        )

    def _fail(self, error: Exception, action: Action, *, reading: bool = False):
        """Answer `error` with the error body of the local API.

        A failure that the app does not explain itself goes to the log, and to the activity
        of its study when the request wrote to the study or opened one of its files.
        """
        engine = self.server.engine
        outcome = _outcome(error, reading=reading)
        body = describe(
            error,
            action=action.text(),
            request_id=new_request_id(),
            message=_message(error) if outcome.own_text else action.failure(),
            code=outcome.code,
            detailed=not outcome.own_text,
            unexpected=outcome.unexpected,
            secrets=engine.secrets(),
        )
        # The extra fields carry texts of the error too: redact them like the rest.
        body.update(_redacted(outcome.extra, engine.secrets()))
        if outcome.unexpected:
            engine.log.unexpected(body, error, label=action.label)
        elif outcome.logged:
            engine.log.failed(body, error, label=action.label)
        if (outcome.unexpected or outcome.logged) and action.recorded and action.study:
            if (activity := self._record(action.study, body)) is not None:
                body["activity_id"] = activity
        self._reply(outcome.status, body)

    def _record(self, study: str, body: dict) -> str | None:
        """List a failure in the activity of `study`; None when that fails too, logged."""
        engine = self.server.engine
        try:
            return engine.record_failure(study, body)
        except Exception as error:
            failure = describe(
                error,
                action=f"Record the failure {body['request_id']}",
                request_id=new_request_id(),
                code="unexpected",
                unexpected=True,
                secrets=engine.secrets(),
            )
            engine.log.unexpected(failure, error, label="Record the failure")
            return None

    def _send_file(self, opened: StudyFile) -> None:
        """Send a file of a study in pieces of CHUNK bytes: the whole file, or the one byte
        range that the request asks for (206), in which PDF.js reads a large PDF.

        A range beyond the end answers 416. The size is the one of the file when it was opened:
        a file that grew since sends no more, one that shrank ends the answer short. A browser
        that stops reading, as PDF.js does with its first request once it knows that ranges
        work, ends the answer quietly, and so does one that takes no piece for SEND_TIMEOUT
        seconds; a file that cannot be read to its end after the headers ends it short and is
        logged. Nothing but the bytes of the file ever follows the headers.
        """
        with opened.stream as stream, self._timeout(SEND_TIMEOUT):
            header = self.headers.get("Range")
            try:
                span = byte_range(header, opened.size)
            except RangeNotSatisfiable:
                self._reject(
                    416,
                    f"{header} lies beyond the {opened.size} bytes of {opened.name}",
                    code="range_not_satisfiable",
                    headers={"Content-Range": f"bytes */{opened.size}"},
                )
                return
            start, end = span or (0, opened.size)
            headers = {"Accept-Ranges": "bytes"}
            if span is not None:
                headers["Content-Range"] = f"bytes {start}-{end - 1}/{opened.size}"
            if opened.media_type == "application/pdf":
                headers["Content-Disposition"] = content_disposition(opened.name)
            # Before the headers: a file that cannot seek fails with its error body.
            stream.seek(start)
            remaining = end - start
            try:
                self._head(
                    200 if span is None else 206,
                    content_type=opened.media_type,
                    length=remaining,
                    headers=headers,
                )
                while remaining > 0:
                    try:
                        piece = stream.read(min(CHUNK, remaining))
                    except OSError as error:
                        self._interrupted(error)
                        break
                    if not piece:
                        # The file got shorter since it was opened.
                        break
                    self.wfile.write(piece)
                    remaining -= len(piece)
            except OSError:
                # The browser went away or stopped reading: as for any reply, neither a
                # failure nor worth a log record.
                self.close_connection = True
                return
            if remaining:
                # The answer is shorter than its Content-Length: closing the connection ends it.
                self.close_connection = True

    @contextmanager
    def _timeout(self, seconds: float):
        """Let each write to the client wait at most `seconds`, after which it counts as gone."""
        previous = self.connection.gettimeout()
        self.connection.settimeout(seconds)
        try:
            yield
        finally:
            self.connection.settimeout(previous)

    def _interrupted(self, error: OSError) -> None:
        """Log a file that failed after its headers were sent; the browser sees a short answer.

        The answer can no longer carry an error body: only the log keeps the failure. Never
        raises, since an error body of a log that fails too would follow the headers.
        """
        engine = self.server.engine
        action = action_of(self.command, urlsplit(self.path).path)
        try:
            body = describe(
                error,
                action=action.text(),
                request_id=new_request_id(),
                message=action.failure(),
                code="file_error",
                unexpected=True,
                secrets=engine.secrets(),
            )
            engine.log.unexpected(body, error, label=action.label)
        except Exception:
            # Nowhere else to tell: the answer still ends short and the connection closes.
            pass

    def _study(self, path):
        engine = self.server.engine
        segments = _segments(path.removeprefix("/local/studies/"))
        if len(segments) < 2:
            raise LookupError(f"Unknown resource {path}")
        substance, name, *rest = segments
        identity = f"{substance}/{name}"
        match rest:
            case []:
                self._versioned(
                    engine.study_version(identity),
                    lambda: engine.study_detail(identity),
                )
            case ["tables", file]:
                self._versioned(
                    _route_version(engine.study_version(identity), rest),
                    lambda: engine.study_table(identity, file),
                )
            case ["sources", source]:
                self._versioned(
                    _route_version(engine.study_version(identity), rest),
                    lambda: engine.study_source(identity, source),
                )
            case ["files", file]:
                self._send_file(engine.study_file(identity, file))
            case _:
                raise LookupError(f"Unknown resource {path}")

    def _allowed(self, *, mutation=False):
        if self.headers.get_all("Host") != [self.server.origin.removeprefix("http://")]:
            self._reject(403, "Unrecognized local host", code="host_refused")
            return False
        origin = self.headers.get("Origin")
        if (mutation and origin != self.server.origin) or (
            origin and origin != self.server.origin
        ):
            self._reject(
                403, "Cross-origin requests are not allowed", code="origin_refused"
            )
            return False
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            self._reject(
                403, "Cross-site requests are not allowed", code="cross_site_refused"
            )
            return False
        return True

    def _authenticated(self, *, mutation=False):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except Exception:
            pass
        value = cookie.get(self.server.cookie_name)
        if not value or not _matches(value.value, self.server.session_token):
            self._reject(
                401, "Open the launch URL printed in your terminal", code="no_session"
            )
            return False
        if mutation and not _matches(
            self.headers.get("X-CSRF-Token", ""), self.server.csrf_token
        ):
            self._reject(403, "Missing or invalid action token", code=ACTION_TOKEN)
            return False
        return True

    def do_GET(self):
        if not self._allowed():
            return
        path = urlsplit(self.path).path
        if path.startswith("/local/"):
            if not self._authenticated():
                return
            action = action_of("GET", path)
            try:
                if path == "/local/state":
                    self._state()
                elif path.startswith("/local/reports/"):
                    name = unquote(path.removeprefix("/local/reports/"))
                    try:
                        report = self.server.engine.report(name)
                    except ValueError, FileNotFoundError:
                        raise LookupError(f"Unknown report {name}") from None
                    self._json(report)
                elif path.startswith("/local/studies/"):
                    self._study(path)
                elif path == "/local/curators":
                    self._json({"curators": roster()})
                else:
                    raise LookupError(f"Unknown resource {path}")
            except Exception as error:
                self._fail(error, action, reading=True)
            return
        try:
            self._page(path)
        except Exception as error:
            self._fail(error, action_of("GET", path), reading=True)

    def _page(self, path):
        """Reply with a file of the app or the avatar of a curator.

        LookupError for a name outside their folders, or one that no file can have.
        """
        if path.startswith("/avatars/"):
            root, name = AVATARS, unquote(path.removeprefix("/avatars/"))
        else:
            root = ASSETS
            name = unquote(path).removeprefix("/static/").lstrip("/") or "index.html"
        try:
            asset = (root / name).resolve()
        except ValueError:
            # A NUL in the name.
            raise LookupError("Unknown resource") from None
        content_type = (
            SCRIPT_TYPES.get(asset.suffix.lower())
            or mimetypes.guess_type(asset.name)[0]
            or "application/octet-stream"
        )
        if (
            not asset.is_relative_to(root.resolve())
            or not asset.is_file()
            or (root is AVATARS and not content_type.startswith("image/"))
        ):
            raise LookupError("Unknown resource")
        data, nonce = asset.read_bytes(), None
        if root is ASSETS and asset == (ASSETS / "index.html").resolve():
            nonce = secrets.token_urlsafe(16)
            theme = getattr(self.server.engine, "theme", None)
            data = data.replace(NONCE_PLACEHOLDER, nonce.encode()).replace(
                THEME_PLACEHOLDER, (theme if theme in THEMES else "system").encode()
            )
        self._reply(200, data, content_type=content_type, nonce=nonce)

    def do_POST(self):
        path = urlsplit(self.path).path
        # The words of the request before its body is read; the body names the study.
        action = action_of("POST", path)
        if not self._allowed(mutation=True) or (
            path != "/local/session" and not self._authenticated(mutation=True)
        ):
            # Refused before the body was read: discard it, as _refuse does.
            self._discard_body(self.headers.get("Content-Length", "0"))
            return
        try:
            if (
                self.headers.get("Transfer-Encoding")
                or len(self.headers.get_all("Content-Length", [])) != 1
            ):
                raise ValueError("Content length required")
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY:
                self._refuse(
                    413,
                    "Request body is too large or empty",
                    size,
                    code="body_too_large",
                )
                return
            if self.headers.get_content_type() != "application/json":
                self._refuse(415, "Use application/json", size, code="json_required")
                return
            self.connection.settimeout(5)
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError("Expected an object")
            action = action_of("POST", path, payload)
            if path == "/local/session":
                token = payload.get("token")
                with self.server.bootstrap_lock:
                    if (
                        not isinstance(token, str)
                        or not self.server.bootstrap_token
                        or not _matches(token, self.server.bootstrap_token)
                    ):
                        self._reject(
                            403, "Launch token expired or invalid", code="launch_token"
                        )
                        return
                    self.server.bootstrap_token = ""
                self._reply(
                    200,
                    {"csrf_token": self.server.csrf_token},
                    cookie=f"{self.server.cookie_name}={self.server.session_token}; HttpOnly; SameSite=Strict; Path=/",
                )
                return
            result = self._action(path, payload)
            self._reply(200, result if isinstance(result, dict) else {"ok": True})
        except Exception as error:
            self._fail(error, action)

    def _refuse(self, status, message, size, *, code):
        """Reply without reading the body, then discard what the client sends."""
        self._reject(status, message, code=code)
        self._discard_body(size)

    def _discard_body(self, size):
        """Discard the body of a request that got its reply unread, within bounds, and close.

        Closing the connection with unread data resets it, and the client would lose the reply.
        """
        self.close_connection = True
        try:
            remaining = min(int(size), DRAIN_LIMIT)
        except ValueError:
            return
        try:
            self.connection.settimeout(2)
            while remaining > 0 and (chunk := self.rfile.read1(min(remaining, 65536))):
                remaining -= len(chunk)
        except OSError:
            pass

    def _action(self, path, body):
        engine = self.server.engine
        if path in {
            "/local/studies/metadata",
            "/local/studies/review",
            "/local/studies/tables",
            "/local/studies/tables/preview",
            "/local/studies/review/preview",
        }:
            study = body.get("study")
            if not isinstance(study, str):
                raise ValueError("Expected a study <substance>/<name>")
            if path == "/local/studies/metadata":
                return engine.write_metadata(
                    study, body.get("revision"), body.get("metadata")
                )
            if path == "/local/studies/review":
                return engine.review_action(study, body)
            if path == "/local/studies/tables/preview":
                return engine.table_preview(study, body)
            if path == "/local/studies/review/preview":
                return engine.target_preview(study, body)
            return engine.tables_action(study, body)
        if path in {
            "/local/reference/read",
            "/local/reference/search",
            "/local/reference/preview",
            "/local/reference/save",
        }:
            return engine.reference_action(path.rsplit("/", 1)[-1], body)
        if path == "/local/workspace":
            return engine.select_workspace(required(body, "path"))
        if path == "/local/workspace/forget":
            folder = required(body, "path")
            if not isinstance(folder, str):
                raise ValueError("Expected a folder path")
            return engine.forget_workspace(folder)
        if path == "/local/directories":
            folder = body.get("path")
            if folder is not None and not isinstance(folder, str):
                raise ValueError("Expected a folder path")
            return engine.list_directories(folder)
        if path == "/local/settings":
            if set(body) - {
                "endpoint",
                "api_key",
                "user",
                "github_user",
                "offline",
                "repository",
                "theme",
            }:
                raise ValueError("Unknown setting")
            return engine.configure(**body)
        if path == "/local/mode":
            return engine.set_mode(required(body, "ids"), required(body, "mode"))
        if path == "/local/jobs/cancel":
            return engine.cancel_jobs(required(body, "ids"))
        if path == "/local/history/clear":
            return engine.clear_history()
        if path == "/local/retry":
            return engine.retry_unknown(
                required(body, "id"), body.get("acknowledge_unknown", False)
            )
        if path == "/local/jobs":
            return engine.enqueue(required(body, "ids"), required(body, "action"))
        if path == "/local/pause":
            paused = required(body, "paused")
            if not isinstance(paused, bool):
                raise ValueError("Expected a boolean")
            return engine.set_paused(paused)
        if path == "/local/files/open":
            from pkdb.curation.launch import open_path

            study, file = required(body, "study_id"), body.get("file")
            target = engine.resolve_file(study, file)
            opening = action_of("POST", path, body)
            open_path(
                target,
                reveal=bool(body.get("reveal", False)),
                subject=f"{file} of {study}" if file else f"the folder of {study}",
                # The command may fail after this request answered: the log keeps it.
                late_failure=lambda failure: engine.log.failed_later(
                    failure, action=opening.text(), label=opening.label
                ),
            )
            return {"ok": True}
        if path == "/local/assignments/refresh":
            return engine.refresh_assignments()
        if path == "/local/resume":
            return engine.resume(body.get("ids"))
        raise LookupError(f"Unknown resource {path}")


def create_server(engine, port=0):
    return CurationServer(engine, port)
