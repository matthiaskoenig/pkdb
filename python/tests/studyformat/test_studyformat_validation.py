import time

import pytest

from pkdb.domain.vocabulary import SubstanceDefinition
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


def duplicate_study(folder, tsv, *items):
    """Make the study contain a duplicate observation and the given review items."""
    (folder / "outputs_Tab2.tsv").write_text(
        tsv("outputs", CMAX, {**CMAX, "mean": "3"}), encoding="utf-8"
    )
    review = {"status": "draft", "items": [{**ITEM, **item} for item in items]}
    (folder / "review.json").write_text(dump_json(review), encoding="utf-8")
    format_folder(folder)
    return folder


DUPLICATE = "duplicate_observation"
OUTPUTS = "outputs_Tab2.tsv"


def test_study_wide_acknowledgement(valid_study, tsv, sf_vocabulary):
    duplicate_study(valid_study, tsv, {"acknowledges": DUPLICATE})
    assert validate_folder(valid_study, sf_vocabulary).issues == []


def test_acknowledgement_of_another_code_keeps_the_warning(
    valid_study, tsv, sf_vocabulary
):
    duplicate_study(valid_study, tsv, {"acknowledges": "unknown_unit"})
    assert codes(validate_folder(valid_study, sf_vocabulary)) == {DUPLICATE}


def test_acknowledgement_without_a_code_keeps_the_warning(
    valid_study, tsv, sf_vocabulary
):
    target = {"file": OUTPUTS, "rows": {"measurement": "cmax"}}
    duplicate_study(valid_study, tsv, {"target": target})
    assert codes(validate_folder(valid_study, sf_vocabulary)) == {DUPLICATE}


def test_acknowledgement_of_another_file_keeps_the_warning(
    valid_study, tsv, sf_vocabulary
):
    item = {"acknowledges": DUPLICATE, "target": {"file": "interventions.tsv"}}
    duplicate_study(valid_study, tsv, item)
    assert codes(validate_folder(valid_study, sf_vocabulary)) == {DUPLICATE}


def test_acknowledgement_of_the_file_suppresses_the_warning(
    valid_study, tsv, sf_vocabulary
):
    item = {"acknowledges": DUPLICATE, "target": {"file": OUTPUTS}}
    duplicate_study(valid_study, tsv, item)
    assert validate_folder(valid_study, sf_vocabulary).issues == []


def test_acknowledgement_of_another_column_keeps_the_warning(
    valid_study, tsv, sf_vocabulary
):
    target = {"file": OUTPUTS, "column": "mean"}
    duplicate_study(valid_study, tsv, {"acknowledges": DUPLICATE, "target": target})
    assert codes(validate_folder(valid_study, sf_vocabulary)) == {DUPLICATE}


def test_acknowledgement_of_no_row_keeps_the_warning(valid_study, tsv, sf_vocabulary):
    target = {"file": OUTPUTS, "rows": {"measurement": "dosing"}}
    duplicate_study(valid_study, tsv, {"acknowledges": DUPLICATE, "target": target})
    assert codes(validate_folder(valid_study, sf_vocabulary)) == {
        DUPLICATE,
        "review_target_unmatched",
    }


def test_acknowledgement_reaches_only_the_rows_it_names(
    valid_study, tsv, sf_vocabulary
):
    # The warning belongs to the second row of the pair, which is the one with mean 3.
    first = {"file": OUTPUTS, "rows": {"mean": "2.5"}}
    second = {"file": OUTPUTS, "rows": {"mean": "3"}}
    duplicate_study(valid_study, tsv, {"acknowledges": DUPLICATE, "target": first})
    assert codes(validate_folder(valid_study, sf_vocabulary)) == {DUPLICATE}
    duplicate_study(valid_study, tsv, {"acknowledges": DUPLICATE, "target": second})
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
    # Non-ASCII study, subject and unit names validate without issues.
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
    # 20,000 timecourse rows (200 series with 100 points each) validate within 10 seconds.
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


def test_decimal_comma_is_only_an_invalid_number(
    make_study, valid_files, tsv, sf_vocabulary
):
    rows = [{**CMAX, "mean": "2,5"}]
    folder = make_study({**valid_files, "outputs_Tab2.tsv": tsv("outputs", *rows)})
    assert format_folder(folder).ok
    assert [issue.code for issue in validate_folder(folder, sf_vocabulary).issues] == [
        "invalid_number"
    ]


def timecourse_rows(count, **change):
    base = {
        "subjects": "all",
        "interventions": "D1",
        "measurement": "concentration",
        "substance": "drug",
        "tissue": "plasma",
        "time_unit": "h",
        "unit": "mg/l",
        **change,
    }
    return [
        {
            **base,
            "label": f"series{index // 100}",
            "time": str(index % 100),
            "mean": "1",
        }
        for index in range(count)
    ]


def test_misspelled_substance_in_a_large_study_is_fast(valid_study, tsv, sf_vocabulary):
    # Close matches are computed once per misspelled value, not once per row.
    substances = tuple(
        SubstanceDefinition(name=f"substance {index}", sid=f"s{index}")
        for index in range(2000)
    )
    vocabulary = sf_vocabulary.model_copy(
        update={"substances": (*sf_vocabulary.substances, *substances)}
    )
    (valid_study / "timecourses_Fig1.tsv").write_text(
        tsv("timecourses", *timecourse_rows(20_000, substance="drugg")),
        encoding="utf-8",
    )
    start = time.monotonic()
    report = validate_folder(valid_study, vocabulary)
    assert time.monotonic() - start < 10
    assert "unknown_substance" in codes(report)


def test_many_acknowledged_warnings_are_fast(valid_study, tsv, sf_vocabulary):
    # 20,000 duplicate observations, acknowledged by one review item with a row filter.
    rows = [{**CMAX, "mean": str(index + 1)} for index in range(20_001)]
    (valid_study / "outputs_Tab2.tsv").write_text(
        tsv("outputs", *rows), encoding="utf-8"
    )
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
    assert format_folder(valid_study).ok
    start = time.monotonic()
    report = validate_folder(valid_study, sf_vocabulary)
    assert time.monotonic() - start < 10
    assert report.issues == []


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


@pytest.mark.parametrize(
    "text",
    [
        '{\n<<<<<<< HEAD\n  "format": 2,\n=======\n  "format": 2,\n>>>>>>> b\n}\n',
        '{"format": 2, "format": 2}',
        '{"format":2,',
    ],
    ids=["conflict", "duplicate_key", "truncated"],
)
def test_broken_study_json_still_declares_format_2(tmp_path, text):
    folder = tmp_path / "Broken"
    folder.mkdir()
    (folder / "study.json").write_text(text, encoding="utf-8")
    assert is_v2_folder(folder)


def test_format_2_files_declare_format_2(tmp_path):
    folder = tmp_path / "Broken"
    folder.mkdir()
    (folder / "study.json").write_text('{"sid": "X"}', encoding="utf-8")
    assert not is_v2_folder(folder)
    for name in ("subjects.tsv", "review.json"):
        (folder / name).write_text("", encoding="utf-8")
        assert is_v2_folder(folder)
        (folder / name).unlink()
    (folder / "study.json").write_text('["format", 2]', encoding="utf-8")
    assert not is_v2_folder(folder)
    (folder / "study.json").write_text('[{"format": 2}]', encoding="utf-8")
    assert is_v2_folder(folder)


def test_empty_optional_table_is_not_formatted(valid_study, tsv, sf_vocabulary):
    (valid_study / "outputs_Tab9.tsv").write_text(tsv("outputs"), encoding="utf-8")
    (valid_study / "Example_Tab9.png").write_bytes(b"png")
    issues = validate_folder(valid_study, sf_vocabulary).issues
    assert [issue.code for issue in issues] == ["not_formatted"]
    assert issues[0].source is not None
    assert issues[0].source.file == "outputs_Tab9.tsv"
    assert "has no rows" in issues[0].message


def break_nothing(folder):
    for path in folder.iterdir():
        path.unlink()


def break_study_json(folder):
    (folder / "study.json").write_text("{", encoding="utf-8")


def break_encoding(folder):
    (folder / "outputs_Tab2.tsv").write_bytes(b"subjects\xff\xfe\n")


def break_first_line(folder):
    path = folder / "outputs_Tab2.tsv"
    path.write_text("\n" + path.read_text(encoding="utf-8"), encoding="utf-8")


@pytest.mark.parametrize(
    "break_folder",
    [break_nothing, break_study_json, break_encoding, break_first_line],
    ids=["empty", "invalid_json", "invalid_utf8", "empty_first_line"],
)
def test_broken_folders_are_reported(break_folder, valid_study, sf_vocabulary):
    break_folder(valid_study)
    report = validate_folder(valid_study, sf_vocabulary)
    assert report.issues
    assert not report.valid
