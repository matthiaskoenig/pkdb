import json

from pkdb.cli import main


def lines(capsys):
    return [
        json.loads(line)
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("{")
    ]


def test_format_command(make_study, valid_files, capsys):
    folder = make_study(valid_files)
    assert main(["format", str(folder), "--check", "--format", "json"]) == 1
    entry = lines(capsys)[0]
    assert entry["ok"] and "subjects.tsv" in {
        change["file"] for change in entry["changes"]
    }
    assert main(["format", str(folder), "--format", "json"]) == 0
    capsys.readouterr()
    assert main(["format", str(folder), "--check", "--format", "json"]) == 0
    assert lines(capsys)[0]["changes"] == []


def test_format_skips_format_1(tmp_path, capsys):
    folder = tmp_path / "Old"
    folder.mkdir()
    (folder / "study.json").write_text('{"sid": "X"}')
    assert main(["format", str(folder), "--format", "json"]) == 0
    assert "format 1" in lines(capsys)[0]["skipped"]


def test_format_reports_problems_for_people(make_study, valid_files, capsys):
    folder = make_study({**valid_files, "outputs_Tab2.tsv": "group\nall\n"})
    assert main(["format", str(folder), "--format", "human"]) == 1
    out = capsys.readouterr().out
    assert "caffeine/Example" in out
    assert "unknown_column" in out and "subjects" in out


def test_validate_format_2(valid_study, sf_vocabulary, tmp_path, capsys):
    lock = tmp_path / "vocabulary.json"
    sf_vocabulary.save(lock)
    args = [
        "validate",
        str(valid_study),
        "--offline",
        "--vocabulary",
        str(lock),
        "--format",
        "json",
    ]
    assert main(args) == 0
    result = lines(capsys)[-1]
    assert result["ok"] and result["study_format"] == 2
    assert result["sid"] == "caffeine/Example"
    assert result["report"]["issues"] == []


def test_validate_format_2_failure(valid_study, sf_vocabulary, tmp_path, capsys):
    (valid_study / "notes.csv").write_text("x\n")
    lock = tmp_path / "vocabulary.json"
    sf_vocabulary.save(lock)
    args = [
        "validate",
        str(valid_study),
        "--offline",
        "--vocabulary",
        str(lock),
        "--format",
        "json",
    ]
    assert main(args) == 1
    result = lines(capsys)[-1]
    assert not result["ok"]
    assert [issue["code"] for issue in result["report"]["issues"]] == ["unknown_file"]


def test_prepare_and_upload_refuse_format_2(valid_study, capsys, monkeypatch):
    assert main(["prepare", str(valid_study), "--offline", "--format", "json"]) == 1
    assert "study format 2" in capsys.readouterr().err
    monkeypatch.setenv("PKDB_API_KEY", "test-key")
    args = [
        "upload",
        str(valid_study),
        "--endpoint",
        "http://127.0.0.1:9",
        "--format",
        "json",
    ]
    assert main(args) == 1
    assert "study format 2" in capsys.readouterr().err


def test_schema_commands(tmp_path, capsys):
    assert main(["schema", "export", "--output", str(tmp_path / "schemas")]) == 0
    assert (tmp_path / "schemas" / "outputs.row.schema.json").is_file()
    assert main(["schema", "docs", "--output", str(tmp_path / "reference.md")]) == 0
    assert "# Study format" in (tmp_path / "reference.md").read_text(encoding="utf-8")


def snapshot(folder):
    return {path.name: path.read_bytes() for path in folder.iterdir()}


def test_prepare_refuses_format_2_before_touching_files(
    make_study, valid_files, tmp_path, capsys
):
    folder = make_study(valid_files)
    before = snapshot(folder)
    old = tmp_path / "caffeine" / "Old"
    old.mkdir()
    (old / "study.json").write_text('{"sid": "X"}')
    assert main(["prepare", str(tmp_path / "caffeine"), "--offline"]) == 1
    assert "1 folder(s) use study format 2" in capsys.readouterr().err
    assert snapshot(folder) == before


def test_format_walks_a_parent_directory(make_study, valid_files, capsys):
    folder = make_study(valid_files)
    old = folder.parent / "Old"
    old.mkdir()
    (old / "study.json").write_text('{"sid": "X"}')
    assert main(["format", str(folder.parent), "--format", "json"]) == 0
    entries = {entry["path"]: entry for entry in lines(capsys)}
    assert "format 1" in entries[str(old)]["skipped"]
    assert entries[str(folder)]["changes"]


def test_format_human_output(make_study, valid_files, capsys):
    folder = make_study(valid_files)
    assert main(["format", str(folder), "--check", "--format", "human"]) == 1
    out = capsys.readouterr().out
    assert "caffeine/Example: would rewrite subjects.tsv" in out
    assert main(["format", str(folder), "--format", "human"]) == 0
    assert "caffeine/Example: rewrote subjects.tsv" in capsys.readouterr().out
    assert main(["format", str(folder), "--format", "human"]) == 0
    assert "caffeine/Example: already formatted" in capsys.readouterr().out


def test_format_without_study_folder(tmp_path, capsys):
    assert main(["format", str(tmp_path), "--format", "json"]) == 1
    assert "No study.json files found" in capsys.readouterr().err


def test_format_reports_unwritable_folder(make_study, valid_files, capsys, monkeypatch):
    def fail(*args, **kwargs):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr("pkdb.studyformat.formatter.atomic_text", fail)
    folder = make_study(valid_files)
    assert main(["format", str(folder), "--format", "json"]) == 1
    entry = lines(capsys)[0]
    assert not entry["ok"] and "Permission denied" in entry["error"]


def test_schema_export_reports_unwritable_output(tmp_path, capsys):
    target = tmp_path / "file"
    target.write_text("x")
    assert main(["schema", "export", "--output", str(target)]) == 1
    assert "Cannot write" in capsys.readouterr().err
