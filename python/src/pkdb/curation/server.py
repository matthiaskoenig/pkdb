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
from pkdb.curation.studies import AmbiguousStudy
from pkdb.references import ReferenceError

MAX_BODY = 64 * 1024
ASSETS = Path(__file__).parent / "static"


def _matches(received, expected):
    return isinstance(received, str) and secrets.compare_digest(
        received.encode("utf-8"), expected.encode("utf-8")
    )


def _segments(path):
    """The segments of a URL path, each percent-decoded after splitting on `/`.

    ValueError for an empty segment, `.`, `..`, or a segment with a separator or NUL.
    """
    segments = []
    for segment in path.split("/"):
        value = unquote(segment, errors="strict")
        if value in {"", ".", ".."} or any(char in value for char in "/\\\0"):
            raise ValueError("Invalid path segment")
        segments.append(value)
    return segments


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
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' https://avatars.githubusercontent.com data:; "
            "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
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
                self._json(engine.study_table(identity, file))
            case ["sources", source]:
                self._json(engine.study_source(identity, source))
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
                    self._json(
                        self.server.engine.report(
                            unquote(path.removeprefix("/local/reports/"))
                        )
                    )
                elif path.startswith("/local/studies/"):
                    self._study(path)
                else:
                    self._reply(404, {"error": "Unknown resource"})
            except AmbiguousStudy as error:
                self._reply(409, {"error": str(error)})
            except ValueError, LookupError, FileNotFoundError:
                self._reply(404, {"error": "Resource is not available"})
            except Exception:
                self._reply(500, {"error": "Unable to read the local workspace state"})
            return
        asset = (
            ASSETS
            / (unquote(path).removeprefix("/static/").lstrip("/") or "index.html")
        ).resolve()
        if not asset.is_relative_to(ASSETS.resolve()) or not asset.is_file():
            self._reply(404, {"error": "Unknown resource"})
            return
        self._reply(
            200,
            asset.read_bytes(),
            content_type=mimetypes.guess_type(asset.name)[0]
            or "application/octet-stream",
        )

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
                self._reply(413, {"error": "Request body is too large or empty"})
                return
            if self.headers.get_content_type() != "application/json":
                self._reply(415, {"error": "Use application/json"})
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
        except (ReferenceError, WorkspaceError) as error:
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

    def _action(self, path, body):
        engine = self.server.engine
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
