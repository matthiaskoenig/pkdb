"""Automatic client updates from PyPI, triggered by newer releases or servers."""

import json
import sys

import httpx2
import pytest

from pkdb import __version__, update


def pypi(version=None, *, fail=False, calls=None):
    def handler(request):
        if calls is not None:
            calls.append(request.url)
        if fail:
            raise httpx2.ConnectError("offline", request=request)
        return httpx2.Response(200, json={"info": {"version": version}})

    return httpx2.Client(transport=httpx2.MockTransport(handler))


def bump(version=__version__):
    parts = [int(part) for part in version.split(".")]
    parts[-1] += 1
    return ".".join(map(str, parts))


@pytest.mark.parametrize(
    "candidate,current,expected",
    [
        ("0.12.0", "0.11.1", True),
        ("0.11.10", "0.11.9", True),
        ("0.11.1", "0.11.1", False),
        ("0.11", "0.11.0", False),
        ("0.10.9", "0.11.1", False),
        ("0.12.0rc1", "0.11.1", False),
        ("test", "0.11.1", False),
        (None, "0.11.1", False),
    ],
)
def test_only_newer_final_releases_count(candidate, current, expected):
    assert update.newer(candidate, current) is expected


def test_release_checks_are_throttled_and_cached(tmp_path):
    state = update.UpdateState(tmp_path / "update.json")
    assert state.due(now=1000)
    with pypi(bump()) as transport:
        assert state.latest(transport=transport, now=1000) == bump()
    assert not state.due(now=1000 + update.CHECK_INTERVAL - 1)
    assert state.due(now=1000 + update.CHECK_INTERVAL)
    # Offline checks keep the previous answer and wait for the next interval.
    with pypi(fail=True) as transport:
        assert state.latest(transport=transport, now=5000) == bump()
    assert json.loads(state.path.read_text())["checked_at"] == 5000
    assert not state.due(now=5001)


def test_newer_server_triggers_one_immediate_check(tmp_path):
    state = update.UpdateState(tmp_path / "update.json")
    with pypi(__version__) as transport:
        state.latest(transport=transport, now=1)
    state.note_server_version(__version__)
    assert not state.due(now=2)
    state.note_server_version(bump())
    assert state.due(now=2)
    with pypi(__version__) as transport:
        state.latest(transport=transport)
    assert not state.due()


def test_target_version_requires_newer_pypi_release(tmp_path):
    state = update.UpdateState(tmp_path / "update.json")
    with pypi(__version__) as transport:
        assert update.target_version(state, transport=transport) is None
    calls = []
    with pypi(bump(), calls=calls) as transport:
        assert update.target_version(state, transport=transport) is None
        assert update.target_version(state, force=True, transport=transport) == bump()
    assert len(calls) == 1


def test_installation_detects_tool_installers(tmp_path, monkeypatch):
    monkeypatch.setattr(update, "_direct_url", lambda: {})
    monkeypatch.setattr(update.shutil, "which", lambda name: f"/usr/bin/{name}")
    (tmp_path / "uv-receipt.toml").write_text("")
    assert update.installation(tmp_path).command == ("uv", "tool", "upgrade", "pkdb")
    (tmp_path / "uv-receipt.toml").unlink()
    (tmp_path / "pipx_metadata.json").write_text("{}")
    assert update.installation(tmp_path).command == ("pipx", "upgrade", "pkdb")
    monkeypatch.setattr(
        update, "_direct_url", lambda: {"url": "file:///src", "dir_info": {}}
    )
    assert update.installation(tmp_path).kind == "development"
    monkeypatch.setattr(
        update, "_direct_url", lambda: {"url": "https://x", "vcs_info": {}}
    )
    assert update.installation(tmp_path).kind == "development"
    monkeypatch.setattr(update, "_direct_url", lambda: {"dir_info": {"editable": True}})
    assert update.installation(tmp_path).command is None


@pytest.mark.parametrize(
    "argv,environment",
    [
        (["upload", "x", "--no-update"], {}),
        (["upload", "x"], {"PKDB_NO_UPDATE": "1"}),
        (["update"], {}),
        (["--version"], {}),
        (["upload", "--help"], {}),
        ([], {}),
    ],
)
def test_automatic_update_can_be_skipped(argv, environment, monkeypatch, tmp_path):
    monkeypatch.delenv("PKDB_NO_UPDATE", raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(
        update, "installation", lambda: pytest.fail("Installation inspected")
    )
    assert update.automatic_update(argv) is None


def test_development_checkouts_are_never_updated(monkeypatch, tmp_path):
    monkeypatch.delenv("PKDB_NO_UPDATE", raising=False)
    monkeypatch.setattr(
        update, "installation", lambda: update.Installation("development", None)
    )
    state = update.UpdateState(tmp_path / "update.json")
    with pypi(fail=True) as transport:
        assert (
            update.automatic_update(["validate"], state=state, transport=transport)
            is None
        )
    assert not state.path.exists()


def test_outdated_installation_upgrades_and_reruns(monkeypatch, tmp_path):
    monkeypatch.delenv("PKDB_NO_UPDATE", raising=False)
    install = update.Installation("uv tool", ("uv", "tool", "upgrade", "pkdb"))
    monkeypatch.setattr(update, "installation", lambda: install)
    monkeypatch.setattr(update, "installed_version", lambda: bump())
    commands = []

    def run(command, **kwargs):
        commands.append((command, kwargs.get("env")))
        return type("Completed", (), {"returncode": 7})()

    monkeypatch.setattr(update.subprocess, "run", run)
    state = update.UpdateState(tmp_path / "update.json")
    with pypi(bump()) as transport:
        code = update.automatic_update(
            ["upload", "x"], state=state, transport=transport
        )
    assert code == 7
    assert commands[0][0] == ("uv", "tool", "upgrade", "pkdb")
    assert commands[1][0] == [sys.executable, "-m", "pkdb", "upload", "x"]
    assert commands[1][1]["PKDB_NO_UPDATE"] == "1"


def test_failed_upgrade_continues_with_installed_release(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("PKDB_NO_UPDATE", raising=False)
    install = update.Installation("pipx", ("pipx", "upgrade", "pkdb"))
    monkeypatch.setattr(update, "installation", lambda: install)

    def run(command, **kwargs):
        raise update.subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(update.subprocess, "run", run)
    state = update.UpdateState(tmp_path / "update.json")
    with pypi(bump()) as transport:
        assert (
            update.automatic_update(["validate"], state=state, transport=transport)
            is None
        )
    assert "pipx upgrade pkdb" in capsys.readouterr().err


def test_unmanaged_installation_prints_instructions(capsys):
    assert not update.upgrade("99.0.0", install=update.Installation("unmanaged", None))
    assert "pip install --upgrade pkdb" in capsys.readouterr().out
