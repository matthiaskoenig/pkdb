"""A study folder is sufficient for the offline command-line workflow."""

import json

import httpx2
import pytest

from pkdb.cli import main


@pytest.mark.parametrize("command", ["prepare", "validate"])
def test_local_commands_are_offline_and_emit_json(
    study_folder, vocabulary, tmp_path, capsys, monkeypatch, command
):
    lock = tmp_path / "vocabulary.lock.json"
    vocabulary.save(lock)
    monkeypatch.delenv("PKDB_API_KEY", raising=False)

    def handler(request):
        pytest.fail("Local preparation and validation must not use HTTP")

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        assert (
            main(
                [command, str(study_folder), "--vocabulary", str(lock), "--offline"],
                client=transport,
            )
            == 0
        )
    assert isinstance(json.loads(capsys.readouterr().out), dict)


def test_cli_validation_failure_is_structured_and_nonzero(
    study_folder, vocabulary, tmp_path, capsys
):
    lock = tmp_path / "vocabulary.lock.json"
    vocabulary.save(lock)
    path = study_folder / "study.json"
    data = json.loads(path.read_text())
    data["outputset"]["outputs"][0]["mean"] = "col==missing"
    path.write_text(json.dumps(data))
    assert main(["validate", str(study_folder), "--vocabulary", str(lock)]) == 1
    output = json.loads(capsys.readouterr().out)
    assert "unknown_column" in json.dumps(output)
    assert "Results" in json.dumps(output)


def test_preparation_artifact_is_written_outside_source(
    study_folder, vocabulary, tmp_path
):
    lock = tmp_path / "vocabulary.lock.json"
    vocabulary.save(lock)
    output = tmp_path / "prepared.json"
    assert (
        main(
            [
                "prepare",
                str(study_folder),
                "--vocabulary",
                str(lock),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert isinstance(json.loads(output.read_text()), dict)


@pytest.mark.parametrize("output_format", ["human", "json"])
def test_cli_upload_is_complete_folder_workflow(
    study_folder, vocabulary, tmp_path, capsys, monkeypatch, output_format
):
    from pkdb import prepare
    from pkdb.domain.validation import PROCESSING_VERSION

    lock = tmp_path / "vocabulary.lock.json"
    vocabulary.save(lock)
    prepared = prepare(study_folder, vocabulary=vocabulary)
    monkeypatch.setenv("PKDB_API_KEY", "pkdb_live_secret")
    monkeypatch.setenv("PKDB_ENDPOINT", "https://example.test")
    calls = []

    def handler(request):
        calls.append(request.method)
        assert request.headers["authorization"] == "Bearer pkdb_live_secret"
        if request.method == "GET":
            return httpx2.Response(
                200,
                json={
                    "schema_version": 1,
                    "server_version": "0.10.2",
                    "processing_version": PROCESSING_VERSION,
                    "vocabulary_version": vocabulary.version,
                    "vocabulary_hash": prepared.vocabulary_hash,
                    "upload_limits": {
                        "max_rows": 1_000_000,
                        "max_files": 256,
                        "max_upload_bytes": 100_000_000,
                        "max_attachment_bytes": 100_000_000,
                    },
                },
            )
        return httpx2.Response(
            201,
            json={
                "sid": "TEST1",
                "created": True,
                "digest": "digest",
                "counts": {"groups": 3, "individuals": 0, "measurements": 12},
            },
        )

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        assert (
            main(
                [
                    "upload",
                    str(study_folder),
                    "--vocabulary",
                    str(lock),
                    "--format",
                    output_format,
                ],
                client=transport,
            )
            == 0
        )
    output = capsys.readouterr().out
    if output_format == "json":
        result = json.loads(output)
        assert result["sid"] == "TEST1"
        assert result["relative_path"] == study_folder.name
        assert result["counts"] == {"groups": 3, "individuals": 0, "measurements": 12}
    else:
        assert f"[1/1] {study_folder.name}" in output
        assert "groups=3, individuals=0, measurements=12" in output
    assert "pkdb_live_secret" not in output
    assert calls == ["GET", "PUT"]


def test_output_inside_study_is_rejected(study_folder, vocabulary, tmp_path, capsys):
    lock = tmp_path / "vocabulary.lock.json"
    vocabulary.save(lock)
    output = study_folder / "prepared.json"
    assert (
        main(
            [
                "prepare",
                str(study_folder),
                "--vocabulary",
                str(lock),
                "--output",
                str(output),
            ]
        )
        == 1
    )
    assert not output.exists()
    assert json.loads(capsys.readouterr().err)["ok"] is False
