import json

import httpx2
import pytest


def folder(tmp_path, name="Example", sid="TEST1"):
    root = tmp_path / name
    root.mkdir()
    (root / "study.json").write_text(json.dumps({"name": name, "sid": sid}))
    (root / "reference.json").write_text(json.dumps({"sid": "REF1"}))
    (root / "table.tsv").write_text("value\n1\n")
    return root


@pytest.mark.parametrize(
    "command,method,path",
    [
        ("upload", "PUT", "/api/v2/studies/TEST1"),
        ("validate", "POST", "/api/v2/studies/validate"),
    ],
)
def test_complete_bundle_one_request_no_source_edits(
    tmp_path, monkeypatch, capsys, command, method, path
):
    from pkdb_server.cli import main

    root = folder(tmp_path)
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    monkeypatch.setenv("PKDB_API_TOKEN", "private-token")
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == method and request.url.path == path
        assert request.headers["authorization"] == "Token private-token"
        body = request.read()
        assert b'name="study"' in body and b'name="reference"' in body
        assert b'filename="table.tsv"' in body
        return httpx2.Response(
            200,
            json={"valid": True}
            if command == "validate"
            else {"sid": "TEST1", "created": True},
        )

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as client:
        assert (
            main(
                [command, str(root), "--api-url", "http://example.test"], client=client
            )
            == 0
        )
    assert len(calls) == 1
    assert {p.name: p.read_bytes() for p in root.iterdir()} == before
    assert "private-token" not in capsys.readouterr().out


def test_all_studies_reported_and_failures_are_nonzero(tmp_path, monkeypatch, capsys):
    from pkdb_server.cli import main

    folder(tmp_path, "First", "FIRST")
    folder(tmp_path, "Second", "SECOND")
    monkeypatch.setenv("PKDB_API_TOKEN", "private-token")
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return (
            httpx2.Response(422, json={"detail": "invalid"})
            if "FIRST" in request.url.path
            else httpx2.Response(201, json={"sid": "SECOND", "created": True})
        )

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as client:
        assert (
            main(
                ["upload", str(tmp_path), "--api-url", "http://example.test"],
                client=client,
            )
            == 1
        )
    assert len(calls) == 2
    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [record["ok"] for record in records] == [False, True]


def test_missing_token_and_empty_folder_do_not_report_success(tmp_path, monkeypatch):
    from pkdb_server.cli import main

    monkeypatch.delenv("PKDB_API_TOKEN", raising=False)
    assert main(["upload", str(tmp_path), "--api-url", "http://example.test"]) == 1
    monkeypatch.setenv("PKDB_API_TOKEN", "private-token")
    assert main(["upload", str(tmp_path), "--api-url", "http://example.test"]) == 1


@pytest.mark.parametrize("failure", ["timeout", "html", "wrong_sid", "redirect"])
def test_failed_or_ambiguous_responses_are_not_retried(
    tmp_path, monkeypatch, capsys, failure
):
    from pkdb_server.cli import main

    root = folder(tmp_path)
    monkeypatch.setenv("PKDB_API_TOKEN", "private-token")
    calls = []

    def handler(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx2.ReadTimeout("timeout", request=request)
        if failure == "html":
            return httpx2.Response(502, text="private-token debug page")
        if failure == "redirect":
            return httpx2.Response(307, headers={"location": "https://other.test"})
        return httpx2.Response(201, json={"sid": "unexpected"})

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as client:
        assert (
            main(
                ["upload", str(root), "--api-url", "http://example.test/api/v1"],
                client=client,
            )
            == 1
        )
    assert len(calls) == 1
    assert calls[0].url.path == "/api/v2/studies/TEST1"
    output = capsys.readouterr().out
    assert "private-token" not in output
    assert json.loads(output)["ok"] is False


def test_integer_study_sid_is_uploaded_as_canonical_text(tmp_path):
    from pkdb_server.commands.upload import send_folder

    root = folder(tmp_path, sid=123)
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx2.Response(201, json={"sid": "123"})

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as client:
        result = send_folder(
            root,
            client=client,
            api_url="http://example.test/api/v2",
            token="test-token",
        )
    assert result["ok"]
    assert result["sid"] == "123"
    assert calls == ["/api/v2/studies/123"]


@pytest.mark.parametrize("token", ["false", 'test"secret', "test\\secret"])
def test_redaction_preserves_json_types_and_hides_escaped_tokens(
    tmp_path, monkeypatch, capsys, token
):
    from pkdb_server.cli import main

    root = folder(tmp_path)
    monkeypatch.setenv("PKDB_API_TOKEN", token)

    def handler(request):
        return httpx2.Response(
            422,
            json={"issues": [{"message": "Rejected " + token, "retry": False}]},
        )

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as client:
        assert (
            main(
                ["upload", str(root), "--api-url", "http://example.test"], client=client
            )
            == 1
        )
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is False
    assert result["issues"] == [{"message": "Rejected [redacted]", "retry": False}]
