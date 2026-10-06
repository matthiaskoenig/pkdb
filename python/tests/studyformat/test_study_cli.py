import json

import pkdb.studyformat.metadata as metadata
from pkdb.cli import main


def test_study_show_and_patch(valid_study, capsys):
    assert main(["study", "show", str(valid_study), "--format", "json"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["study"] == "caffeine/Example"
    assert shown["metadata"]["licence"] == "open"
    patch = ["study", "patch", str(valid_study), "--revision", shown["revision"]]
    patch += ["--format", "json"]
    assert main([*patch, "--json", '{"licence": "closed"}']) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
    assert main([*patch, "--json", '{"licence": "open"}']) == 1
    assert json.loads(capsys.readouterr().out)["error"] == "revision_conflict"


def test_study_patch_reports_invalid_input(valid_study, capsys):
    base = ["study", "patch", str(valid_study), "--format", "json"]
    assert main([*base, "--json", '{"licence": "maybe"}']) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["error"] == "invalid" and output["issues"]
    assert main([*base, "--json", "[1]"]) == 1
    assert json.loads(capsys.readouterr().out)["error"] == "invalid_patch"
    assert main([*base, "--json", "{"]) == 1
    assert json.loads(capsys.readouterr().out)["error"] == "invalid_patch"


def test_study_patch_from_file_and_human_output(valid_study, tmp_path, capsys):
    patch = tmp_path / "patch.json"
    patch.write_text('{"licence": "closed"}')
    assert (
        main(
            [
                "study",
                "patch",
                str(valid_study),
                "--file",
                str(patch),
                "--format",
                "human",
            ]
        )
        == 0
    )
    assert "wrote study.json" in capsys.readouterr().out
    assert main(["study", "show", str(valid_study), "--format", "human"]) == 0
    assert "caffeine/Example" in capsys.readouterr().out


def test_study_reference_patches_given_identifiers(valid_study, capsys, monkeypatch):
    monkeypatch.setattr(metadata, "sync_reference", lambda folder, resolver: "saved")
    args = ["study", "reference", str(valid_study), "--offline", "--format", "json"]
    assert main([*args, "--doi", "10.1000/xyz"]) == 0
    assert json.loads(capsys.readouterr().out)["reference"] == "saved"
    reference = metadata.read_metadata(valid_study).metadata.reference
    assert reference is not None
    assert reference.pmid == "123" and reference.doi == "10.1000/xyz"


def test_study_rejects_a_non_study_folder(tmp_path, capsys):
    assert main(["study", "show", str(tmp_path)]) == 1
    assert "no study.json" in capsys.readouterr().err


def test_study_reference_failed_refresh_exits_1_after_writing(
    valid_study, capsys, monkeypatch
):
    def failing_sync(folder, resolver):
        raise metadata.ReferenceError("PubMed is unreachable")

    monkeypatch.setattr(metadata, "sync_reference", failing_sync)
    args = ["study", "reference", str(valid_study), "--offline", "--format", "json"]
    assert main([*args, "--pmid", "456"]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True and output["reference"] is None
    assert "unreachable" in output["reference_error"]
    reference = metadata.read_metadata(valid_study).metadata.reference
    assert reference is not None and reference.pmid == "456"
