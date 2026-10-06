import json
import re

import pytest
from digitize_fixtures import GOOD, png, project

import pkdb.studyformat.metadata as metadata
from pkdb.cli import main
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.review_edit import read_review
from pkdb.studyformat.validation import validate_folder


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


def test_review_commands(valid_study, sf_vocabulary, tmp_path, capsys, monkeypatch):
    lock = tmp_path / "vocabulary.json"
    sf_vocabulary.save(lock)
    monkeypatch.setenv("PKDB_USER", "curator")
    monkeypatch.delenv("PKDB_AGENT", raising=False)
    add = ["review", "add", str(valid_study), "--kind", "question", "--text", "Why?"]
    add += ["--file", "timecourses_Fig1.tsv", "--rows", "label=drug_plasma"]
    assert main([*add, "--format", "json"]) == 0
    item = json.loads(capsys.readouterr().out)["item"]
    resolve = ["review", "resolve", str(valid_study), item["id"], "--text", "Fine."]
    assert main([*resolve, "--format", "json"]) == 0
    capsys.readouterr()
    assert main(["review", "show", str(valid_study), "--format", "json"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["items"][0]["state"] == "resolved" and shown["items"][0]["matches"] > 0
    status = [
        "review",
        "status",
        str(valid_study),
        "approved",
        "--vocabulary",
        str(lock),
    ]
    assert main([*status, "--agent", "claude", "--format", "json"]) == 1
    assert json.loads(capsys.readouterr().out)["error"] == "approval_refused"
    assert main([*status, "--format", "json"]) == 0
    capsys.readouterr()
    monkeypatch.delenv("PKDB_USER")
    assert (
        main(["review", "reopen", str(valid_study), item["id"], "--format", "json"])
        == 1
    )
    assert json.loads(capsys.readouterr().out)["error"] == "no_user"


def test_review_acknowledge_without_matching_warning(
    valid_study, sf_vocabulary, tmp_path, capsys, monkeypatch
):
    lock = tmp_path / "vocabulary.json"
    sf_vocabulary.save(lock)
    monkeypatch.setenv("PKDB_USER", "curator")
    command = ["review", "acknowledge", str(valid_study), "outside_range"]
    command += ["--file", "timecourses_Fig1.tsv", "--text", "x"]
    assert main([*command, "--vocabulary", str(lock), "--format", "json"]) == 1
    assert json.loads(capsys.readouterr().out)["error"] == "no_such_warning"


@pytest.fixture
def reviewer(sf_vocabulary, tmp_path, monkeypatch):
    """The vocabulary lock file of `pkdb review status|acknowledge`, run by a person."""
    lock = tmp_path / "vocabulary.json"
    sf_vocabulary.save(lock)
    monkeypatch.setenv("PKDB_USER", "curator")
    monkeypatch.delenv("PKDB_AGENT", raising=False)
    return lock


def test_review_add_and_status_refusal_in_human_output(valid_study, reviewer, capsys):
    add = ["review", "add", str(valid_study), "--kind", "question", "--text", "Why?"]
    add += ["--file", "timecourses_Fig1.tsv", "--rows", "label=drug_plasma"]
    assert main([*add, "--format", "human"]) == 0
    out = capsys.readouterr().out
    assert re.fullmatch(r"caffeine/Example: added review item [0-9A-Z]{26}\n", out)
    status = ["review", "status", str(valid_study), "approved"]
    status += ["--vocabulary", str(reviewer), "--format", "human"]
    assert main([*status, "--agent", "claude"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "A person must approve a study" in captured.err
    assert main(status) == 1
    assert "1 review items are open" in capsys.readouterr().err


def test_review_refuses_writes_that_would_fail_validation(
    valid_study, reviewer, capsys
):
    add = ["review", "add", str(valid_study), "--kind", "issue", "--text", "Hm."]
    assert main([*add, "--file", "Example_Fig9.png", "--format", "json"]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["error"] == "invalid"
    assert [issue["code"] for issue in output["issues"]] == ["unknown_review_target"]
    status = ["review", "status", str(valid_study), "approved"]
    assert main([*status, "--vocabulary", str(reviewer), "--format", "json"]) == 0
    capsys.readouterr()
    assert main([*add, "--format", "human"]) == 1
    assert "The study is approved; set the status to in_review" in (
        capsys.readouterr().err
    )


def test_review_revision_conflict(valid_study, reviewer, capsys):
    assert main(["review", "show", str(valid_study), "--format", "json"]) == 0
    revision = json.loads(capsys.readouterr().out)["revision"]
    add = ["review", "add", str(valid_study), "--kind", "question"]
    add += ["--revision", revision]
    assert main([*add, "--text", "One?", "--format", "json"]) == 0
    written = json.loads(capsys.readouterr().out)["revision"]
    assert main([*add, "--text", "Two?", "--format", "json"]) == 1
    output = json.loads(capsys.readouterr().out)
    assert (output["error"], output["revision"]) == ("revision_conflict", written)
    assert main([*add, "--text", "Two?", "--format", "human"]) == 1
    assert capsys.readouterr().err == (
        f"review.json changed on disk since revision {revision}; "
        "show it again and retry\n"
    )


def test_review_status_without_approval_needs_no_vocabulary(
    valid_study, reviewer, tmp_path, capsys
):
    status = ["review", "status", str(valid_study), "in_review"]
    status += ["--vocabulary", str(tmp_path / "missing.json"), "--format", "json"]
    assert main(status) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_review_show_lists_target_matches(valid_study, reviewer, capsys):
    add = ["review", "add", str(valid_study), "--kind", "question", "--text", "Why?"]
    add += ["--file", "timecourses_Fig1.tsv", "--rows", "label=drug_plasma"]
    assert main([*add, "--column", "mean", "--format", "json"]) == 0
    item = json.loads(capsys.readouterr().out)["item"]
    note = ["review", "add", str(valid_study), "--kind", "issue", "--text", "Blurry."]
    assert main([*note, "--file", "Example_Fig1.png", "--format", "json"]) == 0
    capsys.readouterr()
    assert main(["review", "show", str(valid_study), "--format", "human"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[3] == (
        f"{item['id']} open question timecourses_Fig1.tsv label=drug_plasma "
        "column mean (3 matching rows): Why?"
    )
    assert lines[4].endswith(" open issue Example_Fig1.png: Blurry.")


def test_review_acknowledge_one_row(valid_study, reviewer, capsys):
    timecourses = valid_study / "timecourses_Fig1.tsv"
    lines = timecourses.read_text().splitlines()
    header = lines[0].split("\t")
    for index in (2, 3):  # the means at times 1 and 2 lie outside their range
        row = lines[index].split("\t")
        row[header.index("min")], row[header.index("max")] = "3", "4"
        lines[index] = "\t".join(row)
    timecourses.write_text("\n".join(lines) + "\n")
    command = ["review", "acknowledge", str(valid_study), "outside_range"]
    command += ["--file", "timecourses_Fig1.tsv", "--text", "As printed."]
    command += ["--vocabulary", str(reviewer)]
    assert main([*command, "--format", "json"]) == 1
    message = json.loads(capsys.readouterr().out)["message"]
    assert message == (
        "2 warnings [outside_range] match in timecourses_Fig1.tsv; "
        "narrow them with --line (3, 4)"
    )
    assert main([*command, "--line", "3", "--format", "human"]) == 0
    out = capsys.readouterr().out
    assert re.fullmatch(
        r"caffeine/Example: acknowledged outside_range with review item "
        r"[0-9A-Z]{26}\n",
        out,
    )
    assert main([*command, "--format", "json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["item"]["target"]["rows"] == {"label": "drug_plasma", "time": "2"}
    assert output["warnings"] == 1


def test_review_acknowledge_file_warnings_that_share_a_code(
    make_study, valid_files, reviewer, sf_vocabulary, capsys
):
    folder = make_study(
        {
            **valid_files,
            "Example_Fig1.png": png(100, 100),
            "Example_Fig1.wpd.json": json.dumps(
                project(GOOD, extra=("legend", "axis labels"))
            ),
        }
    )
    assert format_folder(folder).ok
    command = ["review", "acknowledge", str(folder), "unknown_dataset"]
    command += ["--file", "Example_Fig1.wpd.json", "--text", "Not data."]
    command += ["--vocabulary", str(reviewer), "--format", "human"]
    assert main(command) == 0
    assert capsys.readouterr().out.endswith("; the item covers 2 warnings\n")
    codes = [issue.code for issue in validate_folder(folder, sf_vocabulary).issues]
    assert "unknown_dataset" not in codes
    [item] = read_review(folder).review.items
    assert item.target is not None and item.target.file == "Example_Fig1.wpd.json"
    assert not item.target.rows and item.target.column is None


def test_study_patch_revision_conflict_in_human_output(valid_study, capsys):
    patch = ["study", "patch", str(valid_study), "--revision", "0" * 64]
    assert main([*patch, "--json", '{"licence": "closed"}', "--format", "human"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        f"study.json changed on disk since revision {'0' * 64}; "
        "show it again and retry\n"
    )


def test_study_patch_of_an_identifier_refreshes_the_reference(
    valid_study, tmp_path, capsys, monkeypatch
):
    calls = []

    def fake_sync(folder, resolver):
        calls.append((resolver.offline, resolver.cache_dir))
        return "replaced reference.json"

    monkeypatch.setattr(metadata, "sync_reference", fake_sync)
    patch = ["study", "patch", str(valid_study), "--offline", "--format", "json"]
    patch += ["--cache-dir", str(tmp_path / "cache")]
    assert main([*patch, "--json", '{"licence": "closed"}']) == 0
    assert json.loads(capsys.readouterr().out)["reference"] is None
    assert calls == []
    assert main([*patch, "--json", '{"reference": {"pmid": "456"}}']) == 0
    assert json.loads(capsys.readouterr().out)["reference"] == (
        "replaced reference.json"
    )
    assert calls == [(True, tmp_path / "cache" / "references")]


def test_study_reference_refreshes_unchanged_identifiers(
    valid_study, capsys, monkeypatch
):
    monkeypatch.setattr(metadata, "sync_reference", lambda folder, resolver: "saved")
    args = ["study", "reference", str(valid_study), "--offline", "--format", "json"]
    assert main([*args, "--pmid", "123"]) == 0
    assert json.loads(capsys.readouterr().out)["reference"] == "saved"
