"""Release monitoring must not confuse API failures with an up-to-date import."""

import importlib.util
import io
import json
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError

import pytest

spec = importlib.util.spec_from_file_location(
    "osp_check", Path(__file__).resolve().parents[2] / "scripts/check_osp_release.py"
)
assert spec is not None and spec.loader is not None
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def response(tag="v1.9", **fields):
    return io.BytesIO(
        json.dumps(dict(tag_name=tag, draft=False, prerelease=False, **fields)).encode()
    )


@pytest.mark.parametrize(
    ("tag", "status"),
    [
        ("v1.9", "current"),
        ("v1.9.0", "current"),
        ("v1.10", "update_available"),
        ("v2.0", "update_available"),
    ],
)
def test_compare_versions_numerically(tag, status):
    def opener(request, timeout):
        assert request.full_url.endswith("/releases/latest")
        assert request.get_header("Authorization") == "Bearer test-token"
        assert timeout == 30
        return response(tag)

    report = checker.check_release(opener=opener, token="test-token")
    assert report["status"] == status
    assert "test-token" not in json.dumps(report)


@pytest.mark.parametrize(
    "payload",
    [
        dict(tag_name="v1.8", draft=False, prerelease=False),
        dict(tag_name="vNext", draft=False, prerelease=False),
        dict(tag_name="v2.0", draft=True, prerelease=False),
        {},
        [],
    ],
)
def test_invalid_or_older_release_is_not_reported_current(payload):
    with pytest.raises(ValueError):
        checker.check_release(
            opener=lambda *args, **kwargs: io.BytesIO(json.dumps(payload).encode())
        )


@pytest.mark.parametrize(
    ("status", "exit_code"), [("current", 0), ("update_available", 2)]
)
def test_exit_status_and_action_summary(
    monkeypatch, tmp_path, capsys, status, exit_code
):
    monkeypatch.setattr(
        checker,
        "check_release",
        lambda **kwargs: dict(
            ok=True,
            status=status,
            pinned_release="v1.9",
            latest_release="v1.10" if exit_code else "v1.9",
            release_url="https://example.org/release",
        ),
    )
    summary = tmp_path / "summary.md"
    assert checker.main(["--summary", str(summary)]) == exit_code
    assert json.loads(capsys.readouterr().out)["status"] == status
    assert (
        "New release available" if exit_code else "No new release available"
    ) in summary.read_text()


def test_failed_request_fails_check(monkeypatch, tmp_path, capsys):
    def unavailable(**kwargs):
        raise HTTPError("https://api.github.com/", 403, "rate limited", Message(), None)

    monkeypatch.setattr(checker, "check_release", unavailable)
    summary = tmp_path / "summary.md"
    assert checker.main(["--summary", str(summary)]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "check_failed"
    assert "availability is unknown" in summary.read_text()
