"""Exercise the actual local HTTP boundary without launching desktop apps."""

import json
import threading
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import Mock

import pytest

from pkdb.curation import server as transport
from pkdb.curation.launch import open_path


@pytest.fixture
def local_server(tmp_path, monkeypatch):
    assets = tmp_path / "static"
    assets.mkdir()
    (assets / "index.html").write_text("<h1>Local curation</h1>")
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


def request(server, method, path, body=None, headers=None):
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    defaults = {"Origin": server.origin, "Content-Type": "application/json"}
    defaults.update(headers or {})
    connection.request(
        method,
        path,
        body=json.dumps(body) if body is not None else None,
        headers=defaults,
    )
    response = connection.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    connection.close()
    return result


def authenticate(server):
    status, headers, data = request(
        server, "POST", "/local/session", {"token": server.bootstrap_token}
    )
    assert status == 200
    assert "HttpOnly" in headers["Set-Cookie"]
    assert "SameSite=Strict" in headers["Set-Cookie"]
    return {
        "Cookie": headers["Set-Cookie"].split(";", 1)[0],
        "X-CSRF-Token": json.loads(data)["csrf_token"],
    }


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
