"""Exercise the actual local HTTP boundary without launching desktop apps."""

import json
import re
import shlex
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from curation_http import authenticate, request

from pkdb.curation import server as transport
from pkdb.curation.engine import CurationEngine
from pkdb.curation.launch import open_path


@pytest.fixture
def local_server(tmp_path, monkeypatch):
    assets = tmp_path / "static"
    assets.mkdir()
    (assets / "index.html").write_text(
        '<h1>Local curation</h1><style nonce="__PKDB_NONCE__"></style>'
    )
    (assets / "app.js").write_text("console.log('loaded')")
    monkeypatch.setattr(transport, "ASSETS", assets)
    engine = Mock()
    engine.snapshot.return_value = {"studies": []}
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
    engine.enqueue.side_effect = RuntimeError("secret-api-key")
    status, _, body = request(
        server, "POST", "/local/jobs", {"ids": [], "action": "upload"}, headers
    )
    assert status == 500
    assert b"secret-api-key" not in body


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
    from pkdb.references import ReferenceError

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

    server = transport.create_server(Mock())
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


def test_open_path_runs_the_recording_command(tmp_path, monkeypatch):
    file = tmp_path / "outputs.xlsx"
    file.write_text("x")
    record = tmp_path / "record.txt"
    monkeypatch.setenv(
        "PKDB_OPEN_COMMAND",
        f"{shlex.quote(sys.executable)} -c "
        + shlex.quote(
            "import sys, pathlib; "
            f"pathlib.Path({str(record)!r}).write_text(sys.argv[1])"
        ),
    )
    open_path(file)
    assert record.read_text() == str(file)


def test_folder_browsing_and_recent_workspace_actions(local_server):
    from pkdb.curation.engine import WorkspaceError

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


def test_curate_cli_explains_missing_workspace(tmp_path, capsys):
    from pkdb.cli import main

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
    ("platform", "command", "expected"),
    [
        ("posix", "'/opt/my tools/rec' --flag", ["/opt/my tools/rec", "--flag"]),
        # Windows paths keep their backslashes.
        ("nt", r"C:\Tools\rec.exe --flag", [r"C:\Tools\rec.exe", "--flag"]),
    ],
)
def test_open_command_is_split_for_the_platform(
    tmp_path, monkeypatch, platform, command, expected
):
    file = tmp_path / "outputs.xlsx"
    file.write_text("x")
    runner = Mock()
    monkeypatch.setattr(
        "pkdb.curation.launch.os",
        SimpleNamespace(name=platform, environ={"PKDB_OPEN_COMMAND": command}),
    )
    monkeypatch.setattr("pkdb.curation.launch.subprocess.run", runner)
    open_path(file)
    assert runner.call_args.args[0] == [*expected, str(file)]
