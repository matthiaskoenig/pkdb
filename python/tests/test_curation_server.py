"""Exercise the actual local HTTP boundary without launching desktop apps."""

import io
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import threading
import time
from http.client import HTTPConnection, IncompleteRead
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY, Mock

import pytest
from curation_http import authenticate, error_body, request
from open_commands import (
    FAILING_OPENER,
    command_line,
    holding_opener,
    late_opener,
    python_program,
    stop_program,
    wait_for_open_commands,
)

from pkdb.curation import launch
from pkdb.curation import server as transport
from pkdb.curation.engine import CurationEngine, WorkspaceError
from pkdb.curation.errors import STDERR_TAIL, ActionFailed, ErrorLog, MissingField
from pkdb.curation.jobs import ResumeRefused
from pkdb.curation.launch import open_path, windows_quoted
from pkdb.curation.studies import AmbiguousStudy, StudyFile, UnsafeFile
from pkdb.identity import IdentityError, UserMismatch
from pkdb.references import ReferenceError
from pkdb.schemas.validation import StudyValidationError, refusal
from pkdb.studyformat.load import BeyondLimits
from pkdb.studyformat.metadata import MetadataError
from pkdb.studyformat.review_edit import ReviewError
from pkdb.studyformat.revision import RevisionConflict


def mock_engine():
    """An engine of the transport tests: a Mock with the secrets that error bodies redact,
    a key of the tests and the tokens that the server protects."""
    engine = Mock()
    engine.snapshot.return_value = {"studies": []}
    protected = ["secret-api-key"]
    engine.protect.side_effect = lambda *values: protected.extend(values)
    engine.secrets.side_effect = lambda: list(protected)
    engine.record_failure.return_value = "activity-1"
    return engine


@pytest.fixture
def local_server(tmp_path, monkeypatch):
    assets = tmp_path / "static"
    assets.mkdir()
    (assets / "index.html").write_text(
        '<meta name="pkdb-theme" content="__PKDB_THEME__">'
        '<h1>Local curation</h1><style nonce="__PKDB_NONCE__"></style>'
    )
    (assets / "app.js").write_text("console.log('loaded')")
    monkeypatch.setattr(transport, "ASSETS", assets)
    engine = mock_engine()
    server = transport.create_server(engine)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, engine
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)


def test_browser_bootstrap_and_actions(local_server):
    server, engine = local_server
    original_token = server.bootstrap_token
    assert request(server, "GET", "/")[0] == 200
    assert request(server, "GET", "/static/app.js")[0] == 200
    assert request(server, "GET", "/local/state")[0] == 401
    headers = authenticate(server)
    assert request(server, "GET", "/local/state", headers=headers)[0] == 200
    assert (
        request(server, "POST", "/local/session", {"token": original_token})[0] == 403
    )
    assert (
        request(
            server,
            "POST",
            "/local/jobs",
            {"ids": ["abc"], "action": "validate"},
            headers,
        )[0]
        == 200
    )
    engine.enqueue.assert_called_once_with(["abc"], "validate")


def test_two_servers_on_other_ports_keep_their_own_sessions(local_server):
    first, _ = local_server
    engine = mock_engine()
    second = transport.create_server(engine)
    thread = threading.Thread(target=second.serve_forever, daemon=True)
    thread.start()
    try:
        cookies = [authenticate(server)["Cookie"] for server in (first, second)]
        names = [cookie.split("=", 1)[0] for cookie in cookies]
        assert names == [
            f"pkdb_curation_{first.server_port}",
            f"pkdb_curation_{second.server_port}",
        ]
        # A browser keeps the cookies of 127.0.0.1 for every port and sends them all.
        both = {"Cookie": "; ".join(cookies)}
        assert request(first, "GET", "/local/state", headers=both)[0] == 200
        assert request(second, "GET", "/local/state", headers=both)[0] == 200
        other = {"Cookie": cookies[1].replace(names[1], names[0])}
        assert request(first, "GET", "/local/state", headers=other)[0] == 401
    finally:
        second.shutdown()
        second.server_close()
        thread.join(timeout=3)


def test_host_origin_and_csrf_rejected(local_server):
    server, engine = local_server
    headers = authenticate(server)
    for override in (
        {"Host": "attacker.example"},
        {"Origin": "https://attacker.example"},
        {"X-CSRF-Token": "bad"},
        {"Sec-Fetch-Site": "cross-site"},
    ):
        assert (
            request(
                server,
                "POST",
                "/local/jobs",
                {"ids": [], "action": "upload"},
                headers | override,
            )[0]
            == 403
        )
    engine.enqueue.assert_not_called()
    assert (
        request(server, "GET", "/local/state", headers=headers | {"Origin": "null"})[0]
        == 403
    )


def test_a_refused_action_token_has_a_code(local_server):
    """The app sends an action again with a fresh token when the code says so, never by the text."""
    server, engine = local_server
    headers = authenticate(server)
    for token in ({"X-CSRF-Token": "stale"}, {}):
        status, _, body = request(
            server,
            "POST",
            "/local/jobs",
            {"ids": [], "action": "validate"},
            {key: value for key, value in headers.items() if key != "X-CSRF-Token"}
            | token,
        )
        assert status == 403
        assert error_body(body) == {
            "error": "Missing or invalid action token",
            "code": transport.ACTION_TOKEN,
            "detail": None,
            "action": "Start jobs (POST /local/jobs)",
        }
    assert transport.ACTION_TOKEN == "action_token"
    engine.enqueue.assert_not_called()


def _post_large(server, headers):
    """POST a body of 1 MiB through a small send buffer, so that it is still sending when a
    server that closes the connection without reading the body resets it."""
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=10)
    connection.connect()
    connection.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 16 * 1024)
    body = json.dumps({"api_key": "x" * (1024 * 1024)})
    connection.request(
        "POST",
        "/local/settings",
        body=body,
        headers={
            "Origin": server.origin,
            "Content-Type": "application/json",
            **headers,
        },
    )
    status = connection.getresponse().status
    connection.close()
    return status


def test_a_refused_post_gets_its_reply_before_the_connection_closes(local_server):
    # The server refuses these requests before it reads their body. Closing the connection
    # with the body unread resets it, and the client loses the reply: on Windows even for a
    # small body (WinError 10053), everywhere for a body that is still being sent.
    server, engine = local_server
    assert _post_large(server, {}) == 401
    headers = authenticate(server)
    without_token = {
        key: value for key, value in headers.items() if key != "X-CSRF-Token"
    }
    assert _post_large(server, without_token) == 403
    assert _post_large(server, {**headers, "Sec-Fetch-Site": "cross-site"}) == 403
    engine.configure.assert_not_called()


def test_payload_limits_paths_and_errors(local_server):
    server, engine = local_server
    headers = authenticate(server)
    assert request(server, "GET", "/static/%2e%2e/secret")[0] == 404
    assert transport.MAX_BODY == 1024 * 1024
    engine.configure.return_value = {"ok": True}
    large = "x" * (512 * 1024)
    assert (
        request(server, "POST", "/local/settings", {"api_key": large}, headers)[0]
        == 200
    )
    engine.configure.assert_called_with(api_key=large)
    assert (
        request(
            server,
            "POST",
            "/local/settings",
            {"api_key": "x" * transport.MAX_BODY},
            headers,
        )[0]
        == 413
    )
    assert (
        request(server, "POST", "/local/settings", {"unexpected": True}, headers)[0]
        == 400
    )
    assert (
        request(server, "POST", "/local/settings", {"user": "curator"}, headers)[0]
        == 200
    )
    engine.configure.assert_called_with(user="curator")
    assert (
        request(server, "POST", "/local/settings", {"theme": "dark"}, headers)[0] == 200
    )
    engine.configure.assert_called_with(theme="dark")
    engine.enqueue.side_effect = RuntimeError("secret-api-key")
    status, _, body = request(
        server, "POST", "/local/jobs", {"ids": [], "action": "upload"}, headers
    )
    assert status == 500
    assert b"secret-api-key" not in body


def test_only_a_study_beyond_the_upload_limits_answers_413(local_server):
    """A study that cannot be read answers 422 with its issues; it is not too large."""
    server, engine = local_server
    headers = authenticate(server)
    engine.study_version.return_value = "v1"
    limit = BeyondLimits(refusal("row_limit", "The study tables have more than 3 rows"))
    unreadable = StudyValidationError(
        refusal("invalid_tsv", "timecourses_Fig1.tsv cannot be read")
    )
    preview = {"study": "caffeine/Example", "target": {"file": "timecourses_Fig1.tsv"}}
    for method, path, body, route in [
        ("POST", "/local/studies/review/preview", preview, engine.target_preview),
        (
            "GET",
            "/local/studies/caffeine/Example/tables/timecourses_Fig1.tsv",
            None,
            engine.study_table,
        ),
    ]:
        route.side_effect = limit
        status, _, data = request(server, method, path, body, headers)
        refused = error_body(data)
        assert (status, refused["error"], refused["code"], refused["detail"]) == (
            413,
            "The study tables have more than 3 rows",
            "beyond_limits",
            None,
        ), path
        route.side_effect = unreadable
        status, _, data = request(server, method, path, body, headers)
        assert status == 422, path
        refused = error_body(data)
        assert refused["error"] == "timecourses_Fig1.tsv cannot be read"
        assert refused["code"] == "unreadable_study"
        assert [issue["code"] for issue in refused["issues"]] == ["invalid_tsv"]


def exits(status: int = 0) -> Mock:
    """A stand-in for subprocess.Popen whose command exits at once with `status`."""
    return Mock(return_value=Mock(wait=Mock(return_value=status)))


def test_open_default_app_uses_argument_array(tmp_path, monkeypatch):
    file = tmp_path / "study; echo secret.xlsx"
    file.touch()
    runner = exits(0)
    monkeypatch.delenv("PKDB_OPEN_COMMAND", raising=False)
    monkeypatch.setattr("pkdb.curation.launch.sys.platform", "linux")
    monkeypatch.setattr("pkdb.curation.launch.subprocess.Popen", runner)
    open_path(file)
    assert runner.call_args.args[0] == ["xdg-open", str(file)]
    options = runner.call_args.kwargs
    assert "shell" not in options
    # No pipe: the program that the command starts inherits its streams (#933).
    assert (options["stdin"], options["stdout"]) == (
        subprocess.DEVNULL,
        subprocess.DEVNULL,
    )
    assert hasattr(options["stderr"], "fileno")
    assert options["close_fds"] is True and options["start_new_session"] is True
    runner.return_value.wait.assert_called_once_with(
        timeout=launch.EARLY_FAILURE_SECONDS
    )
    # The command exited in time: nothing reads the file of stderr any more.
    assert options["stderr"].closed
    open_path(file, reveal=True)
    assert runner.call_args.args[0] == ["xdg-open", str(tmp_path)]


def test_a_program_that_cannot_be_started_says_the_open_failed(tmp_path, monkeypatch):
    file = tmp_path / "outputs.xlsx"
    file.write_text("x")
    monkeypatch.delenv("PKDB_OPEN_COMMAND", raising=False)
    monkeypatch.setattr("pkdb.curation.launch.sys.platform", "linux")
    cause = PermissionError(13, "Permission denied", "xdg-open")
    monkeypatch.setattr(
        "pkdb.curation.launch.subprocess.Popen", Mock(side_effect=cause)
    )
    with pytest.raises(ActionFailed) as failed:
        open_path(file)
    assert (failed.value.message, failed.value.code) == (
        "Could not open outputs.xlsx.",
        "open_failed",
    )
    assert failed.value.cause is cause


def test_an_interrupted_wait_closes_the_stderr_file_of_the_command(
    tmp_path, monkeypatch
):
    file = tmp_path / "outputs.xlsx"
    file.write_text("x")
    monkeypatch.delenv("PKDB_OPEN_COMMAND", raising=False)
    monkeypatch.setattr("pkdb.curation.launch.sys.platform", "linux")
    runner = Mock(return_value=Mock(wait=Mock(side_effect=KeyboardInterrupt)))
    monkeypatch.setattr("pkdb.curation.launch.subprocess.Popen", runner)
    with pytest.raises(KeyboardInterrupt):
        open_path(file)
    assert runner.call_args.kwargs["stderr"].closed


def test_a_thread_that_cannot_start_closes_the_stderr_file_of_the_command(
    tmp_path, monkeypatch
):
    file = tmp_path / "outputs.xlsx"
    file.write_text("x")
    monkeypatch.delenv("PKDB_OPEN_COMMAND", raising=False)
    monkeypatch.setattr("pkdb.curation.launch.sys.platform", "linux")
    process = Mock(wait=Mock(side_effect=subprocess.TimeoutExpired("xdg-open", 2)))
    runner = Mock(return_value=process)
    monkeypatch.setattr("pkdb.curation.launch.subprocess.Popen", runner)
    monkeypatch.setattr(
        launch.threading.Thread, "start", Mock(side_effect=RuntimeError("no threads"))
    )
    with pytest.raises(RuntimeError):
        open_path(file)
    assert runner.call_args.kwargs["stderr"].closed


def test_curate_names_the_source_checkout_without_built_assets(
    tmp_path, monkeypatch, capsys
):
    from pkdb.curation import launch

    checkout = tmp_path / "pkdb"
    assets = checkout / "python" / "src" / "pkdb" / "curation" / "static"
    (checkout / "frontend").mkdir(parents=True)
    (checkout / "frontend" / "package.json").write_text("{}")
    monkeypatch.setattr(transport, "ASSETS", assets)
    engine = Mock(side_effect=AssertionError("The engine must not start"))
    monkeypatch.setattr("pkdb.curation.engine.CurationEngine", engine)
    assert launch.run(tmp_path, offline=True, no_browser=True) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        f"The curation app is not built: {assets} has no index.html.\n"
        f"This pkdb runs from the source checkout {checkout}. Run npm ci and "
        f"npm run build:curation in {checkout / 'frontend'}, or run an installed "
        "pkdb release, which contains the app.\n"
    )
    engine.assert_not_called()


def test_curate_names_the_installed_folder_without_built_assets(
    tmp_path, monkeypatch, capsys
):
    from pkdb.curation import launch

    assets = tmp_path / "lib" / "site-packages" / "pkdb" / "curation" / "static"
    monkeypatch.setattr(transport, "ASSETS", assets)
    engine = Mock(side_effect=AssertionError("The engine must not start"))
    monkeypatch.setattr("pkdb.curation.engine.CurationEngine", engine)
    assert launch.run(tmp_path, offline=True, no_browser=True) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        f"The curation app is not built: {assets} has no index.html.\n"
        "This pkdb was installed from a source checkout without the app. Run npm ci "
        "and npm run build:curation in frontend/ of the checkout and install it "
        "again, or install a pkdb release, which contains the app.\n"
    )
    engine.assert_not_called()


def test_curate_cli_routes_options(monkeypatch):
    from pkdb.cli import main

    run = Mock(return_value=0)
    monkeypatch.setattr("pkdb.curation.launch.run", run)
    assert (
        main(
            [
                "curate",
                "/tmp/studies",
                "--offline",
                "--no-browser",
                "--port",
                "8123",
                "--github-user",
                "curator",
            ]
        )
        == 0
    )
    assert run.call_args.kwargs["path"] == Path("/tmp/studies")
    assert run.call_args.kwargs["port"] == 8123
    assert run.call_args.kwargs["offline"] is True


def test_actions_require_matching_browser_origin(local_server):
    server, engine = local_server
    headers = authenticate(server)
    for origin in ("", "null", "http://localhost:1234"):
        assert (
            request(
                server,
                "POST",
                "/local/pause",
                {"paused": True},
                headers | {"Origin": origin},
            )[0]
            == 403
        )
    engine.set_paused.assert_not_called()


def test_open_action_resolves_registered_file(local_server, monkeypatch, tmp_path):
    server, engine = local_server
    target = tmp_path / "outputs.xlsx"
    engine.resolve_file.return_value = target
    opener = Mock()
    monkeypatch.setattr("pkdb.curation.launch.open_path", opener)
    headers = authenticate(server)
    assert (
        request(
            server,
            "POST",
            "/local/files/open",
            {"study_id": "study", "file": "outputs.xlsx", "reveal": True},
            headers,
        )[0]
        == 200
    )
    engine.resolve_file.assert_called_once_with("study", "outputs.xlsx")
    opener.assert_called_once_with(
        target, reveal=True, subject="outputs.xlsx of study", late_failure=ANY
    )
    # A failure after the answer goes to the log, named as the request.
    failure = ActionFailed(
        "Could not show outputs.xlsx of study in its folder.", code="open_failed"
    )
    opener.call_args.kwargs["late_failure"](failure)
    engine.log.failed_later.assert_called_once_with(
        failure,
        action="Show in folder (POST /local/files/open)",
        label="Show in folder",
    )


def test_invalid_bootstrap_does_not_consume_valid_token(local_server):
    server, _ = local_server
    assert request(server, "POST", "/local/session", {"token": "non-ascii-ä"})[0] == 403
    authenticate(server)


def test_reference_actions_require_authenticated_review(local_server):
    server, engine = local_server
    body = {"id": "study", "input": {"pmid": "123"}}
    assert request(server, "POST", "/local/reference/preview", body)[0] == 401
    headers = authenticate(server)
    engine.reference_action.return_value = {
        "token": "preview",
        "reference": {"pmid": "123"},
    }
    status, _, data = request(server, "POST", "/local/reference/preview", body, headers)
    assert status == 200 and json.loads(data)["token"] == "preview"
    engine.reference_action.assert_called_once_with("preview", body)
    engine.reference_action.side_effect = ReferenceError(
        "Reference sources changed since preview; preview again"
    )
    status, _, data = request(
        server,
        "POST",
        "/local/reference/save",
        {"id": "study", "token": "preview"},
        headers,
    )
    assert status == 400
    assert "changed since preview" in json.loads(data)["error"]


def test_bundled_curator_avatars_are_served_as_images():
    from pkdb.curation.metadata import profile

    server = transport.create_server(mock_engine())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = profile("mkoenig")["avatar_url"]
        status, headers, data = request(server, "GET", url)
        assert status == 200
        assert headers["Content-Type"] == "image/webp"
        assert data[:4] == b"RIFF"
        for path in (
            "/avatars/..%2f..%2fmetadata.py",
            "/avatars/../metadata.py",
            "/avatars/missing.webp",
            "/static/avatars/matthias_koenig.webp",
        ):
            assert request(server, "GET", path)[0] == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@pytest.mark.parametrize(
    "path", ["/static/%00", "/static/a%00b.js", "/avatars/%00.webp"]
)
def test_a_page_name_that_no_file_can_have_is_not_found(local_server, capsys, path):
    server, engine = local_server
    status, _, data = request(server, "GET", path)
    assert status == 404
    body = error_body(data)
    assert (body["error"], body["code"]) == ("Unknown resource", "not_found")
    assert body["action"] == f"Read a page (GET {path})"
    engine.log.failed.assert_not_called()
    engine.log.unexpected.assert_not_called()
    # Not the traceback of socketserver for a request that failed.
    assert capsys.readouterr().err == ""


def test_a_page_that_cannot_be_read_is_a_logged_failure(local_server, monkeypatch):
    server, engine = local_server

    read = transport.Path.read_bytes

    def unreadable(self):
        if self.name == "app.js":
            raise PermissionError(13, "Permission denied", str(self))
        return read(self)

    monkeypatch.setattr(transport.Path, "read_bytes", unreadable)
    status, _, data = request(server, "GET", "/static/app.js")
    assert status == 400
    body = error_body(data)
    assert (body["error"], body["code"]) == ("Could not read the page.", "file_error")
    assert body["detail"].startswith("PermissionError: [Errno 13] Permission denied")
    engine.log.failed.assert_called_once()


def _style_src(headers):
    policy = headers["Content-Security-Policy"]
    return next(
        part.strip()
        for part in policy.split(";")
        if part.strip().startswith("style-src")
    )


def test_index_gets_a_fresh_style_nonce_per_response(local_server):
    server, _ = local_server
    nonces = []
    for path in ("/", "/index.html"):
        status, headers, data = request(server, "GET", path)
        assert status == 200
        assert b"__PKDB_NONCE__" not in data
        found = re.search(rb'nonce="([^"]+)"', data)
        assert found
        nonce = found.group(1).decode()
        assert _style_src(headers) == f"style-src 'self' 'nonce-{nonce}'"
        assert "unsafe-inline" not in headers["Content-Security-Policy"]
        nonces.append(nonce)
    assert nonces[0] != nonces[1]
    status, headers, _ = request(server, "GET", "/static/app.js")
    assert status == 200
    assert _style_src(headers) == "style-src 'self'"
    assert "unsafe-inline" not in headers["Content-Security-Policy"]


def test_index_carries_the_theme_of_the_state_for_the_first_paint(local_server):
    server, engine = local_server
    # A new port is a new origin without the choice in its storage: the page brings it.
    for theme in ("dark", "light", "system"):
        engine.theme = theme
        status, headers, data = request(server, "GET", "/")
        assert status == 200
        assert f'<meta name="pkdb-theme" content="{theme}">'.encode() in data
        assert "unsafe-inline" not in headers["Content-Security-Policy"]
    # Only the three themes reach the page.
    engine.theme = '"><script>alert(1)</script>'
    data = request(server, "GET", "/")[2]
    assert b'<meta name="pkdb-theme" content="system">' in data
    assert b"<script>" not in data
    del engine.theme
    assert b'content="system"' in request(server, "GET", "/")[2]


def test_open_path_runs_the_recording_command(tmp_path, monkeypatch):
    file = tmp_path / "outputs.xlsx"
    file.write_text("x")
    record = tmp_path / "record.txt"
    command = [
        sys.executable,
        "-c",
        "import sys, pathlib; "
        f"pathlib.Path({str(record)!r}).write_text(sys.argv[1], encoding='utf-8')",
    ]
    # Quoted as the shell of the platform quotes it.
    join = subprocess.list2cmdline if os.name == "nt" else shlex.join
    monkeypatch.setenv("PKDB_OPEN_COMMAND", join(command))
    open_path(file)
    assert record.read_text(encoding="utf-8") == str(file.resolve())


def test_folder_browsing_and_recent_workspace_actions(local_server):
    server, engine = local_server
    engine.list_directories.return_value = {"path": "/data", "entries": []}
    engine.forget_workspace.return_value = {"recent_workspaces": []}
    assert request(server, "POST", "/local/directories", {})[0] == 401
    headers = authenticate(server)
    assert (
        request(
            server, "POST", "/local/directories", {}, headers | {"X-CSRF-Token": "bad"}
        )[0]
        == 403
    )
    engine.list_directories.assert_not_called()
    status, _, body = request(server, "POST", "/local/directories", {}, headers)
    assert status == 200
    assert json.loads(body)["path"] == "/data"
    engine.list_directories.assert_called_with(None)
    request(server, "POST", "/local/directories", {"path": "/data/studies"}, headers)
    engine.list_directories.assert_called_with("/data/studies")
    assert (
        request(server, "POST", "/local/workspace/forget", {"path": "/old"}, headers)[0]
        == 200
    )
    engine.forget_workspace.assert_called_once_with("/old")
    engine.list_directories.side_effect = WorkspaceError("Folder does not exist: /x")
    status, _, body = request(
        server, "POST", "/local/directories", {"path": "/x"}, headers
    )
    assert status == 400
    assert json.loads(body)["error"] == "Folder does not exist: /x"
    assert request(server, "POST", "/local/directories", {"path": 3}, headers)[0] == 400


def test_a_refused_resume_reports_its_reason(local_server):
    server, engine = local_server
    reason = "The upload of caffeine/Example has an unknown outcome."
    engine.resume.side_effect = ResumeRefused(reason)
    status, _, body = request(server, "POST", "/local/resume", {}, authenticate(server))
    assert status == 400
    assert json.loads(body)["error"] == reason


def test_curate_cli_explains_missing_workspace(tmp_path, capsys, monkeypatch):
    from pkdb.cli import main

    # A built app, so that the check of the workspace runs whether or not
    # `npm run build:curation` has run in this checkout.
    assets = tmp_path / "static"
    assets.mkdir()
    (assets / "index.html").write_text("<h1>Local curation</h1>")
    monkeypatch.setattr(transport, "ASSETS", assets)
    missing = tmp_path / "missing"
    assert (
        main(
            [
                "curate",
                str(missing),
                "--offline",
                "--no-browser",
                "--state-dir",
                str(tmp_path / "state"),
            ]
        )
        == 1
    )
    assert f"Folder does not exist: {missing}" in capsys.readouterr().err


def test_assignment_mapping_route_is_gone(local_server):
    server, engine = local_server
    headers = authenticate(server)
    status = request(
        server,
        "POST",
        "/local/assignments/map",
        {"number": 1, "study_id": "caffeine/Example"},
        headers,
    )[0]
    assert status == 404
    engine.map_assignment.assert_not_called()
    assert not hasattr(CurationEngine, "map_assignment")


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("'/opt/my tools/rec' --flag", ["/opt/my tools/rec", "--flag", "{file}"]),
        ("rec", ["rec", "{file}"]),
    ],
)
def test_open_command_is_split_like_a_shell_command_on_posix(
    tmp_path, monkeypatch, command, expected
):
    file = tmp_path / "outputs.xlsx"
    file.write_text("x")
    runner = exits(0)
    monkeypatch.setattr(
        "pkdb.curation.launch.os",
        SimpleNamespace(name="posix", environ={"PKDB_OPEN_COMMAND": command}),
    )
    monkeypatch.setattr("pkdb.curation.launch.subprocess.Popen", runner)
    open_path(file)
    path = str(file.resolve())
    assert runner.call_args.args[0] == [a.format(file=path) for a in expected]


@pytest.mark.parametrize(
    "command",
    [r"C:\Tools\rec.exe --flag", r'"C:\Program Files\Rec\rec.exe" --flag'],
)
@pytest.mark.parametrize("name", ["my study", "study"])
def test_open_command_is_a_command_line_on_windows(
    tmp_path, monkeypatch, command, name
):
    # Windows gets the command line as written, followed by the path in quotes.
    folder = tmp_path / name
    folder.mkdir()
    file = folder / "outputs.xlsx"
    file.write_text("x")
    runner = exits(0)
    monkeypatch.setattr(
        "pkdb.curation.launch.os",
        SimpleNamespace(name="nt", environ={"PKDB_OPEN_COMMAND": command}),
    )
    monkeypatch.setattr("pkdb.curation.launch.subprocess.Popen", runner)
    open_path(file)
    assert runner.call_args.args[0] == f'{command} "{file.resolve()}"'


@pytest.mark.parametrize(
    ("path", "quoted"),
    [
        (r"C:\Studies\Fig1.xlsx", r'"C:\Studies\Fig1.xlsx"'),
        (r"C:\R&D\my study", r'"C:\R&D\my study"'),
        # The C runtime reads \" as a quote, so the backslash before it is doubled.
        ("C:\\", '"C:\\\\"'),
        (r"\\server\share" + "\\", r'"\\server\share\\"'),
    ],
)
def test_a_windows_path_is_quoted_as_one_argument(path, quoted):
    assert windows_quoted(path) == quoted


SETTINGS = "Save the settings (POST /local/settings)"


@pytest.mark.parametrize(
    ("error", "status", "expected"),
    [
        (
            ActionFailed("Could not save the settings: locked.", code="keyring_locked"),
            500,
            {"error": "Could not save the settings: locked.", "code": "keyring_locked"},
        ),
        (
            RevisionConflict("study.json", "r1", "r2", "{}"),
            409,
            {
                "error": "study.json changed on disk since it was read",
                "code": "revision_conflict",
                "file": "study.json",
                "revision": "r2",
                "content": "{}",
            },
        ),
        (
            ReviewError("Item 01X does not exist"),
            422,
            {
                "error": "Item 01X does not exist",
                "code": "invalid_document",
                "issues": [],
            },
        ),
        (
            UserMismatch("The API key belongs to PK-DB user 'other'"),
            403,
            {
                "error": "user_mismatch",
                "message": "The API key belongs to PK-DB user 'other'",
                "code": "user_mismatch",
            },
        ),
        (
            IdentityError("Set your PK-DB user"),
            403,
            {"error": "no_user", "message": "Set your PK-DB user", "code": "no_user"},
        ),
        (
            AmbiguousStudy("caffeine/Example", ["a/Example", "b/Example"]),
            409,
            {
                "error": "caffeine/Example is the identity of two folders: "
                "a/Example, b/Example; rename one",
                "code": "ambiguous_study",
                "paths": ["a/Example", "b/Example"],
            },
        ),
        (
            ReferenceError("Reference preview expired; preview again"),
            400,
            {
                "error": "Reference preview expired; preview again",
                "code": "reference_refused",
            },
        ),
        (
            WorkspaceError("Folder does not exist: /x"),
            400,
            {"error": "Folder does not exist: /x", "code": "workspace_refused"},
        ),
        (
            UnsafeFile("Example.xlsx is a symlink"),
            400,
            {"error": "Example.xlsx is a symlink", "code": "unsafe_file"},
        ),
        (
            ResumeRefused("Turn off offline mode"),
            400,
            {"error": "Turn off offline mode", "code": "resume_refused"},
        ),
        (
            MissingField("ids"),
            400,
            {"error": 'Missing field "ids"', "code": "missing_field"},
        ),
        (
            LookupError("caffeine/Missing is not a study of this workspace"),
            404,
            {
                "error": "caffeine/Missing is not a study of this workspace",
                "code": "not_found",
            },
        ),
        (
            ValueError("Unknown setting"),
            400,
            {
                "error": "Could not save the settings.",
                "code": "invalid_request",
                "detail": "ValueError: Unknown setting",
            },
        ),
        (
            TypeError("expected str"),
            400,
            {
                "error": "Could not save the settings.",
                "code": "invalid_request",
                "detail": "TypeError: expected str",
            },
        ),
        (
            PermissionError(13, "Permission denied"),
            400,
            {
                "error": "Could not save the settings.",
                "code": "file_error",
                "detail": "PermissionError: [Errno 13] Permission denied",
            },
        ),
        (
            KeyError("profile"),
            500,
            {
                "error": "Could not save the settings.",
                "code": "unexpected",
                "detail": "KeyError: 'profile'",
            },
        ),
        (
            # Like a KeyError: an index of the server out of range is a bug.
            IndexError("list index out of range"),
            500,
            {
                "error": "Could not save the settings.",
                "code": "unexpected",
                "detail": "IndexError: list index out of range",
            },
        ),
        (
            RuntimeError("boom"),
            500,
            {
                "error": "Could not save the settings.",
                "code": "unexpected",
                "detail": "RuntimeError: boom",
            },
        ),
    ],
)
def test_every_failure_of_an_action_has_the_error_body(
    local_server, error, status, expected
):
    server, engine = local_server
    engine.configure.side_effect = error
    answered, _, data = request(
        server, "POST", "/local/settings", {"user": "curator"}, authenticate(server)
    )
    body = error_body(data)
    assert answered == status
    assert {key: body[key] for key in expected} == expected
    assert body["action"] == SETTINGS
    if "detail" not in expected:
        assert body["detail"] is None
    assert ("traceback" in body) == (expected["code"] == "unexpected")
    assert engine.log.unexpected.called == (expected["code"] == "unexpected")
    # The settings belong to no study: no entry in an activity.
    assert "activity_id" not in body
    engine.record_failure.assert_not_called()


def test_a_failed_read_that_the_app_polls_is_logged_once_a_minute(
    local_server, tmp_path, capsys
):
    server, engine = local_server
    headers = authenticate(server)
    engine.log = ErrorLog(tmp_path / "logs" / "curation.log", engine.secrets)
    engine.study_detail.side_effect = PermissionError(
        13, "Permission denied", "/w/caffeine/Demo2020/outputs_Tab2.tsv"
    )
    # The app asks for the study detail every 1.5 seconds.
    for _ in range(3):
        status, _, data = request(
            server, "GET", "/local/studies/caffeine/Demo2020", headers=headers
        )
        assert (status, json.loads(data)["code"]) == (400, "file_error")
    engine.log.close()
    text = engine.log.path.read_text(encoding="utf-8")
    assert text.count("Traceback") == 1
    assert text.count("repeats Error") == 2
    lines = capsys.readouterr().err.splitlines()
    assert len(lines) == 1
    assert re.fullmatch(
        r"Error [0-9a-f]{8} in Read the study: PermissionError \(see .*curation\.log\)",
        lines[0],
    )


def test_failures_reach_the_log_as_they_deserve(local_server):
    server, engine = local_server
    headers = authenticate(server)

    def fail(error):
        engine.configure.side_effect = error
        request(server, "POST", "/local/settings", {"user": "curator"}, headers)

    fail(RuntimeError("boom"))
    body, error = engine.log.unexpected.call_args.args
    assert engine.log.unexpected.call_args.kwargs == {"label": "Save the settings"}
    assert (body["code"], type(error)) == ("unexpected", RuntimeError)
    fail(ValueError("Unknown theme"))
    assert engine.log.failed.call_args.args[0]["detail"] == "ValueError: Unknown theme"
    assert engine.log.failed.call_args.kwargs == {"label": "Save the settings"}
    # Refusals that the app explains are answered, not logged.
    fail(WorkspaceError("Folder does not exist: /x"))
    assert (engine.log.unexpected.call_count, engine.log.failed.call_count) == (1, 1)


def test_a_failed_write_of_a_study_is_listed_in_its_activity(local_server):
    server, engine = local_server
    headers = authenticate(server)
    engine.tables_action.side_effect = ActionFailed(
        "Could not open the tables of caffeine/Example.", code="open_failed"
    )
    status, _, data = request(
        server,
        "POST",
        "/local/studies/tables",
        {"study": "caffeine/Example", "action": "open"},
        headers,
    )
    body = json.loads(data)
    assert (status, body["activity_id"]) == (500, "activity-1")
    identity, recorded = engine.record_failure.call_args.args
    assert identity == "caffeine/Example"
    assert recorded["error"] == "Could not open the tables of caffeine/Example."
    assert recorded["action"] == "Open tables (POST /local/studies/tables)"
    # Previews and refusals that the app explains are not listed.
    engine.table_preview.side_effect = ValueError("Unknown kind")
    request(
        server,
        "POST",
        "/local/studies/tables/preview",
        {"study": "caffeine/Example", "kind": "x", "source": "y"},
        headers,
    )
    engine.review_action.side_effect = ReviewError("Item 01X does not exist")
    request(
        server,
        "POST",
        "/local/studies/review",
        {"study": "caffeine/Example", "action": "resolve"},
        headers,
    )
    engine.record_failure.assert_called_once()


def test_a_failure_to_record_a_failure_still_answers_the_failure(local_server):
    server, engine = local_server
    engine.tables_action.side_effect = ActionFailed(
        "Could not open the tables of caffeine/Example.", code="open_failed"
    )
    engine.record_failure.side_effect = OSError("state.json: disk full")
    status, _, data = request(
        server,
        "POST",
        "/local/studies/tables",
        {"study": "caffeine/Example", "action": "open"},
        authenticate(server),
    )
    body = json.loads(data)
    assert (status, body["code"]) == (500, "open_failed")
    assert "activity_id" not in body
    engine.log.failed.assert_called_once()
    assert engine.log.unexpected.call_args.kwargs == {"label": "Record the failure"}


def test_a_missing_field_is_named(local_server):
    server, engine = local_server
    status, _, data = request(
        server, "POST", "/local/jobs/cancel", {}, authenticate(server)
    )
    body = error_body(data)
    assert (status, body["error"], body["code"]) == (
        400,
        'Missing field "ids"',
        "missing_field",
    )
    engine.cancel_jobs.assert_not_called()


def test_a_failed_read_names_what_it_read(local_server):
    server, engine = local_server
    headers = authenticate(server)
    engine.snapshot.side_effect = RuntimeError("boom")
    status, _, data = request(server, "GET", "/local/state", headers=headers)
    body = error_body(data)
    assert (status, body["error"], body["code"], body["action"]) == (
        500,
        "Could not read the workspace state.",
        "unexpected",
        "Read the workspace state (GET /local/state)",
    )
    assert "Traceback (most recent call last)" in body["traceback"]
    engine.study_version.side_effect = LookupError(
        "caffeine/Missing is not a study of this workspace"
    )
    status, _, data = request(
        server, "GET", "/local/studies/caffeine/Missing", headers=headers
    )
    body = error_body(data)
    assert (status, body["error"], body["code"], body["action"]) == (
        404,
        "caffeine/Missing is not a study of this workspace",
        "not_found",
        "Read the study (GET /local/studies/caffeine/Missing)",
    )
    engine.study_version.side_effect = None
    engine.study_version.return_value = "v1"
    engine.study_file.side_effect = FileNotFoundError(2, "No such file", "/x/a.png")
    status, _, data = request(
        server, "GET", "/local/studies/caffeine/Example/files/a.png", headers=headers
    )
    assert (status, error_body(data)["error"]) == (404, "/x/a.png does not exist")
    status, _, data = request(server, "GET", "/local/nothing", headers=headers)
    assert (status, error_body(data)["error"]) == (
        404,
        "Unknown resource /local/nothing",
    )


def test_a_metadata_error_answers_422_with_the_error_body(local_server):
    server, engine = local_server
    engine.write_metadata.side_effect = MetadataError(
        refusal("invalid_json", "study.json is not valid").issues
    )
    status, _, data = request(
        server,
        "POST",
        "/local/studies/metadata",
        {"study": "caffeine/Example", "revision": "r1", "metadata": {}},
        authenticate(server),
    )
    body = error_body(data)
    assert status == 422
    assert body["code"] == "invalid_document"
    assert body["detail"] is None
    assert body["action"] == "Save study.json (POST /local/studies/metadata)"
    assert [issue["code"] for issue in body["issues"]] == ["invalid_json"]
    engine.record_failure.assert_not_called()


def _raw(server, method, path, headers, body=b"", length=None):
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    connection.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
    for key, value in headers.items():
        connection.putheader(key, value)
    connection.putheader("Content-Length", str(len(body) if length is None else length))
    connection.endheaders(body)
    response = connection.getresponse()
    result = response.status, response.read()
    connection.close()
    return result


@pytest.mark.parametrize(
    ("case", "status", "code"),
    [
        ("host_refused", 403, "host_refused"),
        ("origin_refused", 403, "origin_refused"),
        ("cross_site_refused", 403, "cross_site_refused"),
        ("no_session", 401, "no_session"),
        ("action_token", 403, "action_token"),
        ("launch_token", 403, "launch_token"),
        ("body_too_large", 413, "body_too_large"),
        ("json_required", 415, "json_required"),
        ("not_found", 404, "not_found"),
    ],
)
def test_every_guard_refusal_has_the_error_body(local_server, case, status, code):
    server, engine = local_server
    headers = authenticate(server)
    host = server.origin.removeprefix("http://")
    base = {"Host": host, "Origin": server.origin, "Content-Type": "application/json"}
    session = {"Cookie": headers["Cookie"], "X-CSRF-Token": headers["X-CSRF-Token"]}
    if case == "host_refused":
        answered, data = _raw(
            server,
            "POST",
            "/local/settings",
            {**base, **session, "Host": "evil.test"},
            b"{}",
        )
    elif case == "origin_refused":
        answered, data = _raw(
            server,
            "POST",
            "/local/settings",
            {**base, **session, "Origin": "http://evil.test"},
            b"{}",
        )
    elif case == "cross_site_refused":
        answered, data = _raw(
            server,
            "POST",
            "/local/settings",
            {**base, **session, "Sec-Fetch-Site": "cross-site"},
            b"{}",
        )
    elif case == "no_session":
        answered, data = _raw(server, "POST", "/local/settings", base, b"{}")
    elif case == "action_token":
        answered, data = _raw(
            server,
            "POST",
            "/local/settings",
            {**base, "Cookie": session["Cookie"]},
            b"{}",
        )
    elif case == "launch_token":
        answered, data = _raw(
            server, "POST", "/local/session", base, b'{"token": "wrong"}'
        )
    elif case == "body_too_large":
        answered, data = _raw(
            server,
            "POST",
            "/local/settings",
            {**base, **session},
            b"",
            length=transport.MAX_BODY + 1,
        )
    elif case == "json_required":
        answered, data = _raw(
            server,
            "POST",
            "/local/settings",
            {**base, **session, "Content-Type": "text/plain"},
            b"{}",
        )
    else:
        answered, data = _raw(
            server, "GET", "/local/nothing", {"Host": host, "Cookie": session["Cookie"]}
        )
    body = error_body(data)
    assert (answered, body["code"]) == (status, code)
    assert isinstance(body["error"], str) and body["error"]
    assert body["detail"] is None
    assert body["action"].endswith(
        "(GET /local/nothing)" if case == "not_found" else ")"
    )
    assert "traceback" not in body
    engine.configure.assert_not_called()


def test_the_extra_fields_of_an_error_body_are_redacted(local_server):
    server, engine = local_server
    engine.write_metadata.side_effect = RevisionConflict(
        "study.json", "r1", "r2", '{"key": "secret-api-key"}'
    )
    status, _, data = request(
        server,
        "POST",
        "/local/studies/metadata",
        {"study": "caffeine/Example", "revision": "r1", "metadata": {}},
        authenticate(server),
    )
    assert status == 409
    assert b"secret-api-key" not in data
    assert error_body(data)["content"] == '{"key": "[redacted]"}'


@pytest.mark.parametrize(
    "gone",
    [BrokenPipeError(32, "Broken pipe"), TimeoutError("timed out")],
    ids=["disconnected", "timed out"],
)
def test_a_client_that_disconnects_before_the_reply_leaves_no_failure(
    local_server, monkeypatch, capsys, gone
):
    server, engine = local_server
    headers = authenticate(server)

    def send(self):
        raise gone

    monkeypatch.setattr(transport.Handler, "end_headers", send)
    engine.tables_action.return_value = {"ok": True}
    stream = serve_file(engine, b"%PDF-1.7\n")
    for method, path, body in [
        (
            "POST",
            "/local/studies/tables",
            {"study": "caffeine/Example", "action": "open"},
        ),
        ("GET", "/local/state", None),
        ("GET", FILE, None),
    ]:
        try:
            request(server, method, path, body, headers)
        except OSError, ValueError:
            pass  # http.client sees the closed connection; the server must stay silent
    engine.tables_action.assert_called_once()
    assert stream.closed_by_server.wait(3)
    engine.record_failure.assert_not_called()
    engine.log.failed.assert_not_called()
    engine.log.unexpected.assert_not_called()
    # Not even the traceback of socketserver for a request that failed.
    assert capsys.readouterr().err == ""


def test_a_result_that_is_not_json_is_an_unexpected_500_before_any_200(local_server):
    server, engine = local_server
    headers = authenticate(server)
    engine.tables_action.return_value = {"rows": {1, 2}}
    status, _, data = request(
        server,
        "POST",
        "/local/studies/tables",
        {"study": "caffeine/Example", "action": "open"},
        headers,
    )
    body = json.loads(data)
    assert (status, body["code"]) == (500, "unexpected")
    assert "Traceback (most recent call last)" in body["traceback"]
    assert "not JSON" in body["detail"]
    engine.log.unexpected.assert_called_once()
    engine.record_failure.assert_called_once()
    engine.snapshot.return_value = {"studies": {1}}
    status, _, data = request(server, "GET", "/local/state", headers=headers)
    assert (status, json.loads(data)["code"]) == (500, "unexpected")


def test_a_failing_open_command_names_its_program_exit_status_and_stderr(
    tmp_path, monkeypatch
):
    # A failure counts as early however slow the runner: wait returns when it exits.
    monkeypatch.setattr(launch, "EARLY_FAILURE_SECONDS", 30)
    file = tmp_path / "outputs.xlsx"
    file.write_text("x")
    monkeypatch.setenv("PKDB_OPEN_COMMAND", command_line(FAILING_OPENER))
    with pytest.raises(ActionFailed) as failed:
        open_path(file, subject="the tables of caffeine/Example")
    assert failed.value.message == "Could not open the tables of caffeine/Example."
    assert failed.value.code == "open_failed"
    cause = failed.value.cause
    assert isinstance(cause, subprocess.CalledProcessError)
    assert cause.returncode == 4 and cause.stderr == b"no method available for opening"


def test_a_folder_that_cannot_be_shown_says_so(tmp_path, monkeypatch):
    # A failure counts as early however slow the runner: wait returns when it exits.
    monkeypatch.setattr(launch, "EARLY_FAILURE_SECONDS", 30)
    file = tmp_path / "outputs.xlsx"
    file.write_text("x")
    monkeypatch.setenv("PKDB_OPEN_COMMAND", command_line(FAILING_OPENER))
    with pytest.raises(ActionFailed) as failed:
        open_path(file, reveal=True, subject="outputs.xlsx of caffeine/Example")
    assert failed.value.message == (
        "Could not show outputs.xlsx of caffeine/Example in its folder."
    )
    assert failed.value.code == "open_failed"
    # A folder has no folder to be shown in: it opens, and says so when it cannot.
    with pytest.raises(ActionFailed) as failed:
        open_path(tmp_path, reveal=True, subject="the folder of caffeine/Example")
    assert failed.value.message == "Could not open the folder of caffeine/Example."


def test_a_missing_opener_says_to_set_the_open_command(tmp_path, monkeypatch):
    file = tmp_path / "outputs.xlsx"
    file.write_text("x")
    monkeypatch.delenv("PKDB_OPEN_COMMAND", raising=False)
    monkeypatch.setattr("pkdb.curation.launch.sys.platform", "linux")
    runner = Mock(side_effect=FileNotFoundError(2, "No such file", "xdg-open"))
    monkeypatch.setattr("pkdb.curation.launch.subprocess.Popen", runner)
    with pytest.raises(ActionFailed) as failed:
        open_path(file)
    assert failed.value.code == "open_command_missing"
    assert failed.value.message == (
        "Could not open outputs.xlsx: xdg-open was not found. Set PKDB_OPEN_COMMAND "
        "to a command that opens files, such as 'gio open'."
    )


def test_a_missing_open_command_is_named(tmp_path, monkeypatch):
    file = tmp_path / "outputs.xlsx"
    file.write_text("x")
    monkeypatch.setenv("PKDB_OPEN_COMMAND", "pkdb-no-such-opener")
    with pytest.raises(ActionFailed) as failed:
        open_path(file)
    assert failed.value.code == "open_command_missing"
    assert "the command 'pkdb-no-such-opener' of PKDB_OPEN_COMMAND was not found" in (
        failed.value.message
    )


def test_an_opener_whose_program_keeps_its_streams_returns_at_once(
    tmp_path, monkeypatch
):
    # xdg-open starts LibreOffice and exits; LibreOffice keeps the streams of xdg-open.
    file = tmp_path / "outputs.xlsx"
    file.write_text("x")
    pid_file = tmp_path / "program.pid"
    monkeypatch.setenv("PKDB_OPEN_COMMAND", command_line(holding_opener(pid_file)))
    started = time.monotonic()
    try:
        open_path(file)
    finally:
        elapsed = time.monotonic() - started
        stop_program(pid_file)
    # At most the 2 seconds in which a command may fail, not the 30 of the program.
    assert elapsed < launch.EARLY_FAILURE_SECONDS + 1


def started_processes(monkeypatch) -> list[subprocess.Popen]:
    """The processes that open_path starts from now on, started by the real Popen."""
    processes = []
    popen = subprocess.Popen

    def recording(*arguments, **options):
        process = popen(*arguments, **options)
        processes.append(process)
        return process

    monkeypatch.setattr("pkdb.curation.launch.subprocess.Popen", recording)
    return processes


def test_an_opener_that_keeps_running_counts_as_started_and_is_waited_for(
    tmp_path, monkeypatch
):
    file = tmp_path / "outputs.xlsx"
    file.write_text("x")
    monkeypatch.setattr(launch, "EARLY_FAILURE_SECONDS", 0.2)
    monkeypatch.setenv("PKDB_OPEN_COMMAND", command_line(late_opener(2, 0)))
    processes = started_processes(monkeypatch)
    late = []
    started = time.monotonic()
    open_path(file, late_failure=late.append)
    assert time.monotonic() - started < 1.5
    [process] = processes
    assert process.returncode is None
    wait_for_open_commands()
    # Waited for: no zombie remains, and a success is no failure.
    assert process.returncode == 0
    assert late == []


def test_an_opener_that_fails_after_it_started_reports_the_failure_later(
    tmp_path, monkeypatch
):
    file = tmp_path / "outputs.xlsx"
    file.write_text("x")
    monkeypatch.setattr(launch, "EARLY_FAILURE_SECONDS", 0.2)
    monkeypatch.setenv(
        "PKDB_OPEN_COMMAND", command_line(late_opener(1, 3, "lost the display"))
    )
    late = []
    open_path(file, subject="the tables of caffeine/Example", late_failure=late.append)
    wait_for_open_commands()
    [failure] = late
    assert (failure.message, failure.code) == (
        "Could not open the tables of caffeine/Example.",
        "open_failed",
    )
    cause = failure.cause
    assert isinstance(cause, subprocess.CalledProcessError)
    assert (cause.returncode, cause.stderr) == (3, b"lost the display")


def test_a_later_failure_without_a_listener_is_dropped_quietly(tmp_path, monkeypatch):
    # pkdb tables open passes no late_failure: the waiting thread must not fail.
    file = tmp_path / "outputs.xlsx"
    file.write_text("x")
    monkeypatch.setattr(launch, "EARLY_FAILURE_SECONDS", 0.2)
    monkeypatch.setenv("PKDB_OPEN_COMMAND", command_line(late_opener(1, 3, "gone")))
    processes = started_processes(monkeypatch)
    errors = []
    monkeypatch.setattr(threading, "excepthook", errors.append)
    open_path(file)
    wait_for_open_commands()
    [process] = processes
    assert process.returncode == 3
    assert errors == []


def test_a_failed_opener_keeps_the_end_of_a_long_stderr(tmp_path, monkeypatch):
    # A failure counts as early however slow the runner: wait returns when it exits.
    monkeypatch.setattr(launch, "EARLY_FAILURE_SECONDS", 30)
    file = tmp_path / "outputs.xlsx"
    file.write_text("x")
    noisy = python_program(
        "import sys; sys.stderr.write('x' * 1000000 + 'the end'); sys.exit(4)"
    )
    monkeypatch.setenv("PKDB_OPEN_COMMAND", command_line(noisy))
    with pytest.raises(ActionFailed) as failed:
        open_path(file)
    cause = failed.value.cause
    assert isinstance(cause, subprocess.CalledProcessError)
    assert cause.returncode == 4
    assert len(cause.stderr) == STDERR_TAIL
    assert cause.stderr.endswith(b"the end")


FILE = "/local/studies/caffeine/Example/files/Example.pdf"


class Recorded(io.BytesIO):
    """A file of a study whose reads the test sees, and which says when the server closed it.

    With `fail_after`, the reads after that many fail as a disk would.
    """

    def __init__(self, data: bytes, *, fail_after: int | None = None):
        super().__init__(data)
        self.reads: list[int | None] = []
        self.closed_by_server = threading.Event()
        self.fail_after = fail_after

    def read(self, size: int | None = -1, /) -> bytes:
        if self.fail_after is not None and len(self.reads) >= self.fail_after:
            raise OSError(5, "Input/output error")
        self.reads.append(size)
        return super().read(size)

    def close(self) -> None:
        self.closed_by_server.set()
        super().close()


def finished_requests(monkeypatch):
    """An event that the server sets once it finished a request, after anything it logs."""
    finished = threading.Event()
    finish = transport.Handler.finish

    def finished_request(self):
        finish(self)
        finished.set()

    monkeypatch.setattr(transport.Handler, "finish", finished_request)
    return finished


def serve_file(
    engine, data, name="Example.pdf", media_type="application/pdf", **options
):
    """Let the mocked engine open `data` as the file `name` of caffeine/Example."""
    stream = Recorded(data, **options)
    engine.study_file.return_value = StudyFile(name, stream, len(data), media_type)
    return stream


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, None),
        ("bytes=0-9", (0, 10)),
        ("bytes=90-", (90, 100)),
        ("bytes=-5", (95, 100)),
        ("bytes=-500", (0, 100)),
        ("bytes=95-200", (95, 100)),
        ("Bytes=99-99", (99, 100)),
        # Several ranges, another unit and invalid ranges ask for the whole file.
        ("bytes=0-1,5-6", None),
        ("items=0-1", None),
        ("bytes=5-1", None),
        ("bytes=-", None),
        ("bytes=abc", None),
        ("bytes=١-٢", None),
    ],
)
def test_a_range_header_asks_for_one_byte_range_or_the_whole_file(header, expected):
    assert transport.byte_range(header, 100) == expected


@pytest.mark.parametrize(
    ("header", "size"),
    [("bytes=100-", 100), ("bytes=-0", 100), ("bytes=150-160", 100), ("bytes=0-", 0)],
)
def test_a_range_beyond_the_end_of_the_file_cannot_be_satisfied(header, size):
    with pytest.raises(transport.RangeNotSatisfiable):
        transport.byte_range(header, size)


@pytest.mark.parametrize(
    "header",
    [
        "bytes=-5-9",
        "bytes=+5-9",
        "bytes=0x10-0x20",
        "bytes=1e3-",
        "bytes=5-1-",
        "bytes=0-9,",
        "bytes=" + "9" * 5000 + "-",
        "bytes=0-" + "9" * 5000,
        "bytes=-" + "9" * 5000,
    ],
    ids=lambda header: header if len(header) < 20 else f"{header[:12]}...{len(header)}",
)
def test_a_malformed_range_never_reaches_outside_the_file(header):
    assert transport.byte_range(header, 100) is None


def test_the_last_bytes_of_an_empty_file_are_the_whole_empty_file():
    assert transport.byte_range("bytes=-5", 0) is None


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Example.pdf", 'inline; filename="Example.pdf"'),
        (
            "Müller 2020.pdf",
            "inline; filename=\"M_ller 2020.pdf\"; filename*=UTF-8''M%C3%BCller%202020.pdf",
        ),
        (
            'a"b\\c.pdf',
            "inline; filename=\"a_b_c.pdf\"; filename*=UTF-8''a%22b%5Cc.pdf",
        ),
        (
            "line\nbreak.pdf",
            "inline; filename=\"line_break.pdf\"; filename*=UTF-8''line%0Abreak.pdf",
        ),
    ],
)
def test_the_disposition_of_a_pdf_names_it_in_ascii_and_in_utf_8(name, expected):
    assert transport.content_disposition(name) == expected


def test_a_file_of_a_study_is_sent_in_pieces_of_64_kb(local_server):
    server, engine = local_server
    data = os.urandom(3 * transport.CHUNK + 5)
    stream = serve_file(engine, data)
    status, headers, body = request(server, "GET", FILE, headers=authenticate(server))
    assert (status, body) == (200, data)
    assert headers["Content-Length"] == str(len(data))
    assert headers["Accept-Ranges"] == "bytes"
    assert headers["Content-Type"] == "application/pdf"
    assert headers["Content-Disposition"] == 'inline; filename="Example.pdf"'
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert stream.closed_by_server.wait(3)
    assert stream.reads == [transport.CHUNK] * 3 + [5]
    engine.study_file.assert_called_once_with("caffeine/Example", "Example.pdf")


def test_one_byte_range_answers_206_with_its_content_range(local_server):
    server, engine = local_server
    data = bytes(range(256)) * 512
    serve_file(engine, data)
    headers = {**authenticate(server), "Range": "bytes=1000-70999"}
    status, answer, body = request(server, "GET", FILE, headers=headers)
    assert (status, body) == (206, data[1000:71000])
    assert answer["Content-Range"] == f"bytes 1000-70999/{len(data)}"
    assert answer["Content-Length"] == "70000"


def test_several_ranges_answer_the_whole_file(local_server):
    server, engine = local_server
    data = bytes(range(256)) * 4
    serve_file(engine, data)
    headers = {**authenticate(server), "Range": "bytes=0-1,5-6"}
    status, answer, body = request(server, "GET", FILE, headers=headers)
    assert (status, body) == (200, data)
    assert "Content-Range" not in answer


def test_a_range_beyond_the_end_answers_416_with_the_size(local_server):
    server, engine = local_server
    data = b"%PDF-1.7\n" * 10
    stream = serve_file(engine, data)
    headers = {**authenticate(server), "Range": "bytes=500-"}
    status, answer, body = request(server, "GET", FILE, headers=headers)
    assert status == 416
    assert answer["Content-Range"] == f"bytes */{len(data)}"
    assert error_body(body) == {
        "error": f"bytes=500- lies beyond the {len(data)} bytes of Example.pdf",
        "code": "range_not_satisfiable",
        "detail": None,
        "action": f"Read a file (GET {FILE})",
    }
    assert stream.closed_by_server.wait(3)


def test_an_image_has_ranges_too_and_no_disposition(local_server):
    server, engine = local_server
    headers = authenticate(server)
    data = b"\x89PNG" + bytes(5000)
    path = "/local/studies/caffeine/Example/files/Example_Fig1.png"
    serve_file(engine, data, name="Example_Fig1.png", media_type="image/png")
    status, answer, body = request(server, "GET", path, headers=headers)
    assert (status, body, answer["Content-Type"]) == (200, data, "image/png")
    assert answer["Accept-Ranges"] == "bytes"
    assert "Content-Disposition" not in answer
    serve_file(engine, data, name="Example_Fig1.png", media_type="image/png")
    status, _, body = request(
        server, "GET", path, headers={**headers, "Range": "bytes=0-3"}
    )
    assert (status, body) == (206, b"\x89PNG")


def test_a_browser_that_stops_reading_ends_the_answer_without_a_failure(
    local_server, monkeypatch
):
    server, engine = local_server
    headers = authenticate(server)
    stream = serve_file(engine, bytes(32 * 1024 * 1024))
    finished = finished_requests(monkeypatch)
    with socket.create_connection(
        ("127.0.0.1", server.server_port), timeout=3
    ) as client:
        client.sendall(
            (
                f"GET {FILE} HTTP/1.1\r\nHost: 127.0.0.1:{server.server_port}\r\n"
                f"Cookie: {headers['Cookie']}\r\n\r\n"
            ).encode()
        )
        assert client.recv(12).startswith(b"HTTP/1.")
    # The server notices on a later piece, stops and closes the file.
    assert stream.closed_by_server.wait(5)
    assert finished.wait(5)
    assert len(stream.reads) < 32 * 1024 * 1024 // transport.CHUNK
    engine.log.unexpected.assert_not_called()
    engine.log.failed.assert_not_called()
    assert request(server, "GET", "/local/state", headers=headers)[0] == 200


def test_a_file_that_fails_while_it_is_sent_is_logged_and_its_answer_ends_short(
    local_server,
):
    server, engine = local_server
    headers = authenticate(server)
    stream = serve_file(engine, bytes(3 * transport.CHUNK), fail_after=1)
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    connection.request("GET", FILE, headers={"Origin": server.origin, **headers})
    response = connection.getresponse()
    assert response.status == 200
    with pytest.raises(IncompleteRead):
        response.read()
    connection.close()
    assert stream.closed_by_server.wait(3)
    engine.log.unexpected.assert_called_once()
    body, error = engine.log.unexpected.call_args.args
    assert (body["code"], body["action"], type(error)) == (
        "file_error",
        f"Read a file (GET {FILE})",
        OSError,
    )
    assert engine.log.unexpected.call_args.kwargs == {"label": "Read a file"}


@pytest.mark.parametrize("grown", [1000, -1000], ids=["grew", "shrank"])
def test_a_file_whose_size_changed_since_it_was_opened_sends_its_size_and_ends(
    local_server, monkeypatch, grown
):
    server, engine = local_server
    headers = authenticate(server)
    finished = finished_requests(monkeypatch)
    data = os.urandom(2 * transport.CHUNK)
    # The size when the server opened the file, which then grew or shrank by `grown` bytes.
    size = len(data) - grown
    stream = Recorded(data)
    engine.study_file.return_value = StudyFile(
        "Example.pdf", stream, size, "application/pdf"
    )
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    connection.request("GET", FILE, headers={"Origin": server.origin, **headers})
    response = connection.getresponse()
    assert (response.status, response.headers["Content-Length"]) == (200, str(size))
    if grown > 0:
        # Never more than the size of the headers.
        assert response.read() == data[:size]
    else:
        # The answer ends short at once instead of waiting for bytes that never come.
        with pytest.raises(IncompleteRead) as short:
            response.read()
        assert short.value.partial == data
    connection.close()
    assert stream.closed_by_server.wait(3)
    assert finished.wait(3)
    engine.log.unexpected.assert_not_called()
    engine.log.failed.assert_not_called()


@pytest.mark.parametrize(
    "broken",
    [RuntimeError("The log is broken"), OSError(28, "No space left on device")],
    ids=["error", "os error"],
)
def test_a_failure_to_log_a_failed_file_sends_nothing_after_its_bytes(
    local_server, monkeypatch, broken
):
    server, engine = local_server
    headers = authenticate(server)
    data = os.urandom(3 * transport.CHUNK)
    stream = serve_file(engine, data, fail_after=1)
    # Only the first record fails, so that a second answer after the headers would be logged.
    engine.log.unexpected.side_effect = [broken, None]
    finished = finished_requests(monkeypatch)
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    connection.request("GET", FILE, headers={"Origin": server.origin, **headers})
    response = connection.getresponse()
    assert response.status == 200
    with pytest.raises(IncompleteRead) as short:
        response.read()
    # The bytes of the file and nothing else follow the headers: no second status line.
    assert short.value.partial == data[: transport.CHUNK]
    connection.close()
    assert stream.closed_by_server.wait(3)
    assert finished.wait(3)
    engine.log.unexpected.assert_called_once()
    engine.log.failed.assert_not_called()
    assert request(server, "GET", "/local/state", headers=headers)[0] == 200


def test_a_browser_that_stalls_frees_its_thread_and_the_file_after_a_timeout(
    local_server, monkeypatch
):
    server, engine = local_server
    headers = authenticate(server)
    monkeypatch.setattr(transport, "SEND_TIMEOUT", 0.5)
    stream = serve_file(engine, bytes(32 * 1024 * 1024))
    finished = finished_requests(monkeypatch)
    with socket.socket() as client:
        # A small window, so that the server soon has nothing more to send into.
        client.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 64 * 1024)
        client.settimeout(3)
        client.connect(("127.0.0.1", server.server_port))
        client.sendall(
            (
                f"GET {FILE} HTTP/1.1\r\nHost: 127.0.0.1:{server.server_port}\r\n"
                f"Cookie: {headers['Cookie']}\r\n\r\n"
            ).encode()
        )
        assert client.recv(12).startswith(b"HTTP/1.")
        # The browser keeps the connection open and reads no more.
        assert stream.closed_by_server.wait(5)
        assert finished.wait(5)
    assert len(stream.reads) < 32 * 1024 * 1024 // transport.CHUNK
    engine.log.unexpected.assert_not_called()
    engine.log.failed.assert_not_called()
    assert request(server, "GET", "/local/state", headers=headers)[0] == 200


def test_the_scripts_of_the_app_are_javascript_whatever_the_system_table_says(
    local_server, monkeypatch
):
    server, _ = local_server
    worker = transport.ASSETS / "pdfjs" / "pdf.worker.min.mjs"
    worker.parent.mkdir()
    worker.write_text("export {};")
    # The Windows registry can map .js to text/plain; a module worker runs only as JavaScript.
    monkeypatch.setattr(
        transport.mimetypes, "guess_type", lambda name: ("text/plain", None)
    )
    for path in ("/pdfjs/pdf.worker.min.mjs", "/static/app.js"):
        status, headers, _ = request(server, "GET", path)
        assert (status, headers["Content-Type"]) == (200, "text/javascript")
