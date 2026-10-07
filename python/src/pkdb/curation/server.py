"""Loopback-only HTTP transport for the local curation workspace."""

import hashlib
import json
import mimetypes
import secrets
import threading
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from pkdb.curation.engine import WorkspaceError
from pkdb.curation.metadata import roster
from pkdb.curation.studies import AmbiguousStudy, UnsafeFile
from pkdb.identity import IdentityError, UserMismatch
from pkdb.references import ReferenceError
from pkdb.schemas.validation import StudyValidationError
from pkdb.studyformat.metadata import MetadataError
from pkdb.studyformat.review_edit import ApprovalRefused, ReviewError
from pkdb.studyformat.revision import RevisionConflict

MAX_BODY = 1024 * 1024
# What a refused request may still send so that the client receives the refusal.
DRAIN_LIMIT = 4 * MAX_BODY
ASSETS = Path(__file__).parent / "static"
AVATARS = Path(__file__).parent / "avatars"
NONCE_PLACEHOLDER = b"__PKDB_NONCE__"


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


class CurationServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = True

    def __init__(self, engine, port=0):
        self.engine = engine
        self.bootstrap_lock = threading.Lock()
        self.bootstrap_token = secrets.token_urlsafe(32)
        self.session_token = secrets.token_urlsafe(32)
        self.csrf_token = secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", port), Handler)
        self.origin = f"http://127.0.0.1:{self.server_port}"
        self.launch_url = f"{self.origin}/#token={self.bootstrap_token}"

    def server_close(self):
        super().server_close()
        self.engine.close()


class Handler(BaseHTTPRequestHandler):
    server: CurationServer

    def log_message(self, format, *args):
        # Request URLs and payloads must never leak bootstrap tokens or API keys.
        pass

    def _reply(
        self,
        status,
        value,
        *,
        content_type="application/json",
        cookie=None,
        etag=None,
        nonce=None,
    ):
        data = value if isinstance(value, bytes) else json.dumps(value).encode()
        self.send_response(status)
        if status != 304:
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
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
        if status != 304:
            self.wfile.write(data)

    def _versioned(self, version, build):
        """Reply with the JSON that `build` returns, or 304 when the client has `version`."""
        etag = f'"{version}"'
        if self.headers.get("If-None-Match") == etag:
            self._reply(304, b"", etag=etag)
            return
        self._reply(200, build(), etag=etag)

    def _json(self, value):
        """Reply with a JSON value whose ETag is the hash of its JSON."""
        data = json.dumps(value).encode()
        self._versioned(hashlib.sha256(data).hexdigest(), lambda: data)

    def _study(self, path):
        engine = self.server.engine
        segments = _segments(path.removeprefix("/local/studies/"))
        if len(segments) < 2:
            raise LookupError(path)
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
                data, media_type = engine.study_image(identity, file)
                self._reply(200, data, content_type=media_type)
            case _:
                raise LookupError(path)

    def _allowed(self, *, mutation=False):
        if self.headers.get_all("Host") != [self.server.origin.removeprefix("http://")]:
            self._reply(403, {"error": "Unrecognized local host"})
            return False
        origin = self.headers.get("Origin")
        if (mutation and origin != self.server.origin) or (
            origin and origin != self.server.origin
        ):
            self._reply(403, {"error": "Cross-origin requests are not allowed"})
            return False
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            self._reply(403, {"error": "Cross-site requests are not allowed"})
            return False
        return True

    def _authenticated(self, *, mutation=False):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except Exception:
            pass
        value = cookie.get("pkdb_curation")
        if not value or not _matches(value.value, self.server.session_token):
            self._reply(401, {"error": "Open the launch URL printed in your terminal"})
            return False
        if mutation and not _matches(
            self.headers.get("X-CSRF-Token", ""), self.server.csrf_token
        ):
            self._reply(403, {"error": "Missing or invalid action token"})
            return False
        return True

    def do_GET(self):
        if not self._allowed():
            return
        path = urlsplit(self.path).path
        if path.startswith("/local/"):
            if not self._authenticated():
                return
            try:
                if path == "/local/state":
                    self._json(
                        {
                            **self.server.engine.snapshot(),
                            "csrf_token": self.server.csrf_token,
                        }
                    )
                elif path.startswith("/local/reports/"):
                    try:
                        report = self.server.engine.report(
                            unquote(path.removeprefix("/local/reports/"))
                        )
                    except ValueError, FileNotFoundError:
                        raise LookupError(path) from None
                    self._json(report)
                elif path.startswith("/local/studies/"):
                    self._study(path)
                elif path == "/local/curators":
                    self._json({"curators": roster()})
                else:
                    self._reply(404, {"error": "Unknown resource"})
            except AmbiguousStudy as error:
                self._reply(409, {"error": str(error)})
            except StudyValidationError as error:
                # The study is beyond the upload limits.
                self._reply(413, {"error": str(error)})
            except LookupError, FileNotFoundError:
                self._reply(404, {"error": "Resource is not available"})
            except Exception:
                self._reply(500, {"error": "Unable to read the local workspace state"})
            return
        if path.startswith("/avatars/"):
            root, name = AVATARS, unquote(path.removeprefix("/avatars/"))
        else:
            root = ASSETS
            name = unquote(path).removeprefix("/static/").lstrip("/") or "index.html"
        asset = (root / name).resolve()
        content_type = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
        if (
            not asset.is_relative_to(root.resolve())
            or not asset.is_file()
            or (root is AVATARS and not content_type.startswith("image/"))
        ):
            self._reply(404, {"error": "Unknown resource"})
            return
        data, nonce = asset.read_bytes(), None
        if root is ASSETS and asset == (ASSETS / "index.html").resolve():
            nonce = secrets.token_urlsafe(16)
            data = data.replace(NONCE_PLACEHOLDER, nonce.encode())
        self._reply(200, data, content_type=content_type, nonce=nonce)

    def do_POST(self):
        if not self._allowed(mutation=True):
            return
        path = urlsplit(self.path).path
        if path != "/local/session" and not self._authenticated(mutation=True):
            return
        try:
            if (
                self.headers.get("Transfer-Encoding")
                or len(self.headers.get_all("Content-Length", [])) != 1
            ):
                raise ValueError("Content length required")
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY:
                self._refuse(413, "Request body is too large or empty", size)
                return
            if self.headers.get_content_type() != "application/json":
                self._refuse(415, "Use application/json", size)
                return
            self.connection.settimeout(5)
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError("Expected an object")
            if path == "/local/session":
                token = payload.get("token")
                with self.server.bootstrap_lock:
                    if (
                        not isinstance(token, str)
                        or not self.server.bootstrap_token
                        or not _matches(token, self.server.bootstrap_token)
                    ):
                        self._reply(403, {"error": "Launch token expired or invalid"})
                        return
                    self.server.bootstrap_token = ""
                self._reply(
                    200,
                    {"csrf_token": self.server.csrf_token},
                    cookie=f"pkdb_curation={self.server.session_token}; HttpOnly; SameSite=Strict; Path=/",
                )
                return
            result = self._action(path, payload)
            self._reply(200, result if isinstance(result, dict) else {"ok": True})
        except RevisionConflict as error:
            # The file changed since the app read it: the current document to reload.
            self._reply(
                409,
                {
                    "error": str(error),
                    "file": error.file,
                    "revision": error.current,
                    "content": error.content,
                },
            )
        except (MetadataError, ReviewError) as error:
            refused = (
                {"code": "approval_refused"}
                if isinstance(error, ApprovalRefused)
                else {}
            )
            self._reply(
                422,
                {
                    "error": str(error),
                    "issues": [issue.model_dump(mode="json") for issue in error.issues],
                    **refused,
                },
            )
        except UserMismatch as error:
            self._reply(403, {"error": UserMismatch.code, "message": str(error)})
        except IdentityError as error:
            self._reply(403, {"error": "no_user", "message": str(error)})
        except AmbiguousStudy as error:
            self._reply(409, {"error": str(error)})
        except (ReferenceError, WorkspaceError, UnsafeFile) as error:
            self._reply(400, {"error": str(error)})
        except LookupError:
            self._reply(404, {"error": "Unknown resource or study"})
        except ValueError, TypeError, OSError:
            self._reply(
                400,
                {
                    "error": "Action could not be completed. Check the selection, settings, and file availability."
                },
            )
        except Exception:
            self._reply(
                500,
                {
                    "error": "The local action failed. Review workspace activity and retry."
                },
            )

    def _refuse(self, status, message, size):
        """Reply without reading the body, then discard what the client sends, within bounds.

        Closing the connection with unread data resets it, and the client would lose the reply.
        """
        self.close_connection = True
        self._reply(status, {"error": message})
        remaining = min(size, DRAIN_LIMIT)
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
            return engine.tables_action(study, body)
        if path in {
            "/local/reference/read",
            "/local/reference/search",
            "/local/reference/preview",
            "/local/reference/save",
        }:
            return engine.reference_action(path.rsplit("/", 1)[-1], body)
        if path == "/local/workspace":
            return engine.select_workspace(body["path"])
        if path == "/local/workspace/forget":
            if not isinstance(body["path"], str):
                raise ValueError("Expected a folder path")
            return engine.forget_workspace(body["path"])
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
            }:
                raise ValueError("Unknown setting")
            return engine.configure(**body)
        if path == "/local/mode":
            return engine.set_mode(body["ids"], body["mode"])
        if path == "/local/jobs/cancel":
            return engine.cancel_jobs(body["ids"])
        if path == "/local/history/clear":
            return engine.clear_history()
        if path == "/local/retry":
            return engine.retry_unknown(
                body["id"], body.get("acknowledge_unknown", False)
            )
        if path == "/local/jobs":
            return engine.enqueue(body["ids"], body["action"])
        if path == "/local/pause":
            if not isinstance(body["paused"], bool):
                raise ValueError("Expected a boolean")
            return engine.set_paused(body["paused"])
        if path == "/local/files/open":
            from pkdb.curation.launch import open_path

            target = engine.resolve_file(body["study_id"], body.get("file"))
            open_path(target, reveal=bool(body.get("reveal", False)))
            return {"ok": True}
        if path == "/local/assignments/refresh":
            return engine.refresh_assignments()
        if path == "/local/resume":
            return engine.resume(body.get("ids"))
        raise LookupError(path)


def create_server(engine, port=0):
    return CurationServer(engine, port)
