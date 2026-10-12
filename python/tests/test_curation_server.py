"""Exercise the actual local HTTP boundary without launching desktop apps."""

import json
import os
import re
import shlex
import socket
import subprocess
import sys
import threading
from http.client import HTTPConnection
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from curation_http import authenticate, error_body, request

from pkdb.curation import server as transport
from pkdb.curation.engine import CurationEngine, WorkspaceError
from pkdb.curation.errors import ActionFailed, MissingField
from pkdb.curation.jobs import ResumeRefused
from pkdb.curation.launch import open_path, windows_quoted
from pkdb.curation.studies import AmbiguousStudy, UnsafeFile
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


def test_open_default_app_uses_argument_array(tmp_path, monkeypatch):
    file = tmp_path / "study; echo secret.xlsx"
    file.touch()
    runner = Mock()
    monkeypatch.setattr("pkdb.curation.launch.sys.platform", "linux")
    monkeypatch.setattr("pkdb.curation.launch.subprocess.run", runner)
    open_path(file)
    assert runner.call_args.args[0] == ["xdg-open", str(file)]
    assert "shell" not in runner.call_args.kwargs
    open_path(file, reveal=True)
    assert runner.call_args.args[0] == ["xdg-open", str(tmp_path)]


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
    opener.assert_called_once_with(target, reveal=True)


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
    runner = Mock()
    monkeypatch.setattr(
        "pkdb.curation.launch.os",
        SimpleNamespace(name="posix", environ={"PKDB_OPEN_COMMAND": command}),
    )
    monkeypatch.setattr("pkdb.curation.launch.subprocess.run", runner)
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
    runner = Mock()
    monkeypatch.setattr(
        "pkdb.curation.launch.os",
        SimpleNamespace(name="nt", environ={"PKDB_OPEN_COMMAND": command}),
    )
    monkeypatch.setattr("pkdb.curation.launch.subprocess.run", runner)
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
    # The settings belong to no study: no entry in an activity.
    assert "activity_id" not in body
    engine.record_failure.assert_not_called()


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
    engine.study_image.side_effect = FileNotFoundError(2, "No such file", "/x/a.png")
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


def test_a_client_that_disconnects_before_the_reply_leaves_no_failure(
    local_server, monkeypatch
):
    server, engine = local_server
    headers = authenticate(server)

    def gone(self):
        raise BrokenPipeError(32, "Broken pipe")

    monkeypatch.setattr(transport.Handler, "end_headers", gone)
    engine.tables_action.return_value = {"ok": True}
    try:
        request(
            server,
            "POST",
            "/local/studies/tables",
            {"study": "caffeine/Example", "action": "open"},
            headers,
        )
    except OSError, ValueError:
        pass  # http.client sees the closed connection; the server must stay silent
    engine.tables_action.assert_called_once()
    engine.record_failure.assert_not_called()
    engine.log.failed.assert_not_called()
    engine.log.unexpected.assert_not_called()
