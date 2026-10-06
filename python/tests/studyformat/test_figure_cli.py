import json

from digitize_fixtures import GOOD, png, project

from pkdb.cli import main


def test_digitize_import_json_output(make_study, valid_files, tmp_path, capsys):
    folder = make_study({**valid_files, "Example_Fig1.png": png(100, 100)})
    file = tmp_path / "wpd.json"
    file.write_text(json.dumps(project(GOOD)))
    assert (
        main(["digitize", "import", str(folder), "Fig1", str(file), "--format", "json"])
        == 0
    )
    entry = json.loads(capsys.readouterr().out)
    assert entry["file"] == "Example_Fig1.wpd.json" and entry["ok"] is True


def test_digitize_import_human_output(make_study, valid_files, tmp_path, capsys):
    folder = make_study({**valid_files, "Example_Fig1.png": png(100, 100)})
    file = tmp_path / "wpd.json"
    file.write_text(json.dumps(project(GOOD)))
    command = ["digitize", "import", str(folder), "Fig1", str(file)]
    assert main([*command, "--format", "human"]) == 0
    assert capsys.readouterr().out == "caffeine/Example: wrote Example_Fig1.wpd.json\n"
    file.write_text(json.dumps(project([*GOOD, (150, 50)])))
    assert main([*command, "--format", "human"]) == 1
    assert capsys.readouterr().out == (
        "caffeine/Example: not imported\n"
        "  Example_Fig1.wpd.json: The pixel (150, 50) lies outside the 100 x 100 "
        "image [digitization_outside_image]\n"
    )


def test_digitize_import_of_a_log_axis_that_overflows(
    make_study, valid_files, tmp_path, capsys
):
    folder = make_study({**valid_files, "Example_Fig1.png": png(100, 100)})
    data = project(GOOD)
    axes = data["axesColl"][0]
    axes["isLogY"] = True
    axes["calibrationPoints"][2] |= {"py": 100, "dy": "1"}
    axes["calibrationPoints"][3] |= {"py": 99.95, "dy": "10"}
    file = tmp_path / "wpd.json"
    file.write_text(json.dumps(data))
    command = ["digitize", "import", str(folder), "Fig1", str(file)]
    assert main([*command, "--format", "json"]) == 1
    entry = json.loads(capsys.readouterr().out)
    assert entry["ok"] is False
    assert [issue["code"] for issue in entry["issues"]] == ["digitization_invalid"]
    assert not (folder / "Example_Fig1.wpd.json").exists()


def test_digitize_import_needs_a_study_format_2_folder(tmp_path, capsys):
    project_file = tmp_path / "wpd.json"
    project_file.write_text(json.dumps(project(GOOD)))
    command = ["digitize", "import", str(tmp_path), "Fig1", str(project_file)]
    assert main(command) == 1
    assert "no study.json" in capsys.readouterr().err
    (tmp_path / "study.json").write_text(json.dumps({"name": "Old"}))
    assert main(command) == 1
    assert "pkdb digitize needs study format 2" in capsys.readouterr().err
