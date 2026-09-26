import hashlib
import importlib.util
from pathlib import Path
from urllib.error import URLError

import pytest

spec = importlib.util.spec_from_file_location(
    "dataset_check",
    Path(__file__).resolve().parents[2] / "scripts/check_dataset_releases.py",
)
assert spec is not None and spec.loader is not None
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


@pytest.mark.parametrize(
    ("provider", "payload", "status"),
    [
        ("frdb", b'<a href="frdb-v2024-12-30.zip">download</a>', "current"),
        ("frdb", b"frdb-v2024-12-30.zip frdb-v2025-01-01.zip", "update_available"),
        ("cvtdb", b"Package: invivoPKfit\nVersion: 2.0.2\n", "current"),
        ("cvtdb", b"Version: 2.0.3\n", "update_available"),
    ],
)
def test_version_detection(provider, payload, status):
    assert checker.check(provider, read=lambda url: payload)["status"] == status


@pytest.mark.parametrize("provider", ["frdb", "cvtdb"])
def test_page_failure_is_not_no_new_releases(provider):
    with pytest.raises(ValueError, match="unknown"):
        checker.check(provider, read=lambda url: b"error page")


def test_warfarin_checks_data_not_repository_revision(monkeypatch):
    pin = {**checker.PINS["warfarin"], "sha256": hashlib.sha256(b"data").hexdigest()}
    monkeypatch.setitem(checker.PINS, "warfarin", pin)
    assert checker.check("warfarin", read=lambda url: b"data")["status"] == "current"
    assert (
        checker.check("warfarin", read=lambda url: b"new data")["status"]
        == "update_available"
    )


def test_failure_is_distinguished_and_other_checks_continue(
    monkeypatch, tmp_path, capsys
):
    visited = []

    def check(provider):
        visited.append(provider)
        if provider == "frdb":
            raise URLError("offline")
        return dict(provider=provider, status="current", pinned="1", latest="1")

    monkeypatch.setattr(checker, "check", check)
    path = tmp_path / "summary.md"
    assert checker.main(["--summary", str(path)]) == 1
    assert len(visited) == 3
    assert "Availability unknown" in path.read_text()
    assert "check_failed" in capsys.readouterr().out
