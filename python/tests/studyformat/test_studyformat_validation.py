import time

from pkdb.studyformat import is_v2_folder, validate_folder
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.jsonio import dump_json

CMAX = {
    "subjects": "all",
    "interventions": "D1",
    "measurement": "cmax",
    "substance": "drug",
    "tissue": "plasma",
    "mean": "2.5",
    "sd": "0.5",
    "unit": "mg/l",
}
ITEM = {
    "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2AB",
    "kind": "issue",
    "state": "resolved",
    "text": "The paper reports two values.",
    "author": "curator",
    "created": "2026-10-05T10:12:00Z",
    "resolved_by": "curator",
    "resolved": "2026-10-05T11:00:00Z",
}


def codes(report):
    return {issue.code for issue in report.issues}


def test_valid_study(valid_study, sf_vocabulary):
    report = validate_folder(valid_study, sf_vocabulary)
    assert report.issues == []
    assert report.valid


def test_unformatted_study_is_invalid(make_study, valid_files, sf_vocabulary):
    report = validate_folder(make_study(valid_files), sf_vocabulary)
    assert codes(report) == {"not_formatted"}
    assert not report.valid


def test_all_layers_are_collected(make_study, valid_files, tsv, sf_vocabulary):
    files = {
        **valid_files,
        "notes.csv": "x\n",
        "outputs_Tab2.tsv": tsv(
            "outputs",
            {**CMAX, "subjects": "S9", "measurement": "cmaxx", "count": "x"},
        ),
    }
    folder = make_study(files)
    format_folder(folder)
    found = codes(validate_folder(folder, sf_vocabulary))
    assert {
        "unknown_file",
        "invalid_integer",
        "unknown_reference",
        "unknown_measurement",
    } <= found


def test_warnings_can_be_acknowledged(valid_study, tsv, sf_vocabulary):
    (valid_study / "outputs_Tab2.tsv").write_text(
        tsv("outputs", CMAX, {**CMAX, "mean": "3"}), encoding="utf-8"
    )
    format_folder(valid_study)
    assert codes(validate_folder(valid_study, sf_vocabulary)) == {
        "duplicate_observation"
    }
    item = {
        **ITEM,
        "acknowledges": "duplicate_observation",
        "target": {
            "file": "outputs_Tab2.tsv",
            "rows": {"subjects": "all", "measurement": "cmax"},
        },
    }
    (valid_study / "review.json").write_text(
        dump_json({"status": "draft", "items": [item]}), encoding="utf-8"
    )
    format_folder(valid_study)
    assert validate_folder(valid_study, sf_vocabulary).issues == []


def test_errors_cannot_be_acknowledged(valid_study, tsv, sf_vocabulary):
    (valid_study / "outputs_Tab2.tsv").write_text(
        tsv("outputs", {**CMAX, "subjects": "S9"}), encoding="utf-8"
    )
    format_folder(valid_study)
    item = {**ITEM, "acknowledges": "unknown_reference"}
    (valid_study / "review.json").write_text(
        dump_json({"status": "draft", "items": [item]}), encoding="utf-8"
    )
    format_folder(valid_study)
    assert "unknown_reference" in codes(validate_folder(valid_study, sf_vocabulary))


def test_non_ascii_names(make_study, valid_files, sf_vocabulary):
    # Review focus 4.
    files = {}
    for name, content in valid_files.items():
        name = name.replace("Example", "Dahlström2007")
        if isinstance(content, str) and name.endswith(".tsv"):
            content = content.replace("S1", "Gruppe Ä")
        if name.startswith("outputs_"):
            content = content.replace("mg/l", "µg/l")
        files[name] = content
    folder = make_study(files, name="Dahlström2007")
    assert format_folder(folder).ok
    report = validate_folder(folder, sf_vocabulary)
    assert report.issues == []


def test_large_study_is_fast(valid_study, tsv, sf_vocabulary):
    # Review focus 5: 200 series with 100 points each.
    base = {
        "subjects": "all",
        "interventions": "D1",
        "measurement": "concentration",
        "substance": "drug",
        "tissue": "plasma",
        "time_unit": "h",
        "unit": "mg/l",
    }
    rows = [
        {**base, "label": f"series{label}", "time": str(t), "mean": str(t + 1)}
        for label in range(200)
        for t in range(100)
    ]
    (valid_study / "timecourses_Fig1.tsv").write_text(
        tsv("timecourses", *rows), encoding="utf-8"
    )
    start = time.monotonic()
    report = validate_folder(valid_study, sf_vocabulary)
    assert time.monotonic() - start < 10
    assert codes(report) <= {"not_formatted"}


def test_max_issues(make_study, valid_files, tsv, sf_vocabulary):
    rows = [{**CMAX, "mean": "bad", "comment": str(i)} for i in range(30)]
    folder = make_study({**valid_files, "outputs_Tab2.tsv": tsv("outputs", *rows)})
    report = validate_folder(folder, sf_vocabulary, max_issues=5)
    assert len(report.issues) == 5
    assert report.truncated


def test_is_v2_folder(valid_study, tmp_path):
    assert is_v2_folder(valid_study)
    old = tmp_path / "old"
    old.mkdir()
    (old / "study.json").write_text('{"sid": "X", "groupset": {}}')
    assert not is_v2_folder(old)
    (old / "study.json").write_text("{")
    assert not is_v2_folder(old)
    assert not is_v2_folder(tmp_path / "missing")
