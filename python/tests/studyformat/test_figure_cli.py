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
