import itertools

import pytest

from pkdb.schemas.validation import StudyValidationError
from pkdb.studyformat import load
from pkdb.studyformat.load import RowLimit, load_study, load_table
from pkdb.studyformat.tables import TABLES
from pkdb.studyformat.text import read_tsv

OUT = TABLES["outputs"]


def codes(issues):
    return [issue.code for issue in issues]


def test_load_valid_study(make_study, valid_files):
    study = load_study(make_study(valid_files))
    assert study.issues == []
    assert study.name == "Example"
    assert [table.file for table in study.tables][:2] == [
        "subjects.tsv",
        "interventions.tsv",
    ]
    outputs = study.of_kind("outputs")[0]
    assert outputs.source == "Tab2"
    row = outputs.rows[0]
    assert row.line == 2
    assert row.values["mean"] == 2.5
    assert row.values["interventions"] == ("D1",)
    assert row.cells["sd"] == "0.5"
    interventions = study.table("interventions.tsv")
    assert interventions is not None
    assert interventions.rows[0].values["time"] == (0.0,)
    assert study.metadata is not None and study.metadata.creator == "curator"
    assert study.review is not None and study.review.status == "draft"
    assert study.reference is not None and study.reference["pmid"] == "123"
    assert [row.cells["name"] for _, row in study.rows("subjects")] == [
        "all",
        "S1",
        "S2",
    ]


def test_legacy_column_names_suggest_replacements():
    data = b"measurement_type\tgroup\tvalue\tmean_pm\nauc\tall\t1\t2\n"
    table, issues = load_table("outputs_Tab1.tsv", data, OUT, "Tab1", study="Example")
    assert table is None
    found = {}
    for issue in issues:
        assert issue.source is not None
        found[issue.source.header] = issue.suggestions[0].candidates
    assert found == {
        "measurement_type": ["measurement"],
        "group": ["subjects"],
        "value": ["mean"],
        "mean_pm": ["error_bar"],
    }
    assert {issue.code for issue in issues} == {"unknown_column"}


def test_unknown_column_close_match():
    table, issues = load_table(
        "outputs_Tab1.tsv", b"subject\tmeasurment\n", OUT, "Tab1", study="Example"
    )
    assert table is None
    assert [issue.suggestions[0].candidates for issue in issues] == [
        ["subjects"],
        ["measurement"],
    ]


def test_structural_problems():
    _, duplicate = load_table(
        "outputs_Tab1.tsv", b"mean\tmean\n1\t2\n", OUT, "Tab1", study="Example"
    )
    assert codes(duplicate) == ["duplicate_column"]
    _, extra = load_table(
        "outputs_Tab1.tsv", b"subjects\tmean\nall\t1\tx\n", OUT, "Tab1", study="Example"
    )
    assert codes(extra) == ["extra_cells"]
    assert extra[0].source is not None
    assert (extra[0].source.row, extra[0].source.column) == (2, "C")
    _, empty = load_table("outputs_Tab1.tsv", b"", OUT, "Tab1", study="Example")
    assert codes(empty) == ["missing_header"]
    _, latin = load_table(
        "outputs_Tab1.tsv",
        "subjects\nä".encode("latin-1"),
        OUT,
        "Tab1",
        study="Example",
    )
    assert codes(latin) == ["invalid_encoding"]


def test_trailing_empty_columns_and_reordered_columns_load():
    data = b"mean\tsubjects\t\t\n2.50\tall\t\t\n"
    table, issues = load_table("outputs_Tab1.tsv", data, OUT, "Tab1", study="Example")
    assert issues == []
    assert table is not None
    assert table.rows[0].cells["mean"] == "2.5"
    assert table.rows[0].cells["measurement"] == ""
    assert table.column_index("subjects") == 1
    assert table.column_index("measurement") is None


def test_cell_problems_keep_the_table():
    data = b"subjects\tmean\tcount\nall\t2,5\t1.5\n"
    table, issues = load_table("outputs_Tab1.tsv", data, OUT, "Tab1", study="Example")
    assert table is not None and table.rows[0].values["mean"] is None
    # Issues follow the template column order, where count precedes mean.
    assert [(i.code, i.source.cell, i.source.header) for i in issues if i.source] == [
        ("invalid_integer", "C2", "count"),
        ("invalid_number", "B2", "mean"),
    ]


def test_owned_cells_are_not_judged_and_blank_rows_are_skipped():
    data = b"study\tsource\tsubjects\nOther\tweird source\tall\nExample\tTab1\t\n"
    table, issues = load_table("outputs_Tab1.tsv", data, OUT, "Tab1", study="Example")
    assert issues == []
    assert table is not None
    assert [row.line for row in table.rows] == [2]


def test_merge_conflict_markers_stop_loading():
    data = (
        b"subjects\tmean\n<<<<<<< HEAD\nall\t1\n||||||| base\nall\t0\n"
        b"=======\nall\t2\n>>>>>>> feature\n"
    )
    table, issues = load_table("outputs_Tab1.tsv", data, OUT, "Tab1", study="Example")
    assert table is None
    assert codes(issues) == ["merge_conflict"]
    assert issues[0].source is not None and issues[0].source.row == 2
    assert "resolve the git conflict" in issues[0].message
    _, header = load_table(
        "outputs_Tab1.tsv", b"<<<<<<< HEAD\nsubjects\n", OUT, "Tab1", study="Example"
    )
    assert codes(header) == ["merge_conflict"]


@pytest.mark.parametrize(
    "line",
    [
        "second line of a comment",
        "Other\tTab1",
        "Example\tTab9",
        "\tTab9",
    ],
)
def test_text_only_in_owned_columns_stops_loading(line):
    data = f"study\tsource\tsubjects\tcomment\nExample\tTab1\tall\t\n{line}\n"
    table, issues = load_table(
        "outputs_Tab1.tsv", data.encode(), OUT, "Tab1", study="Example"
    )
    assert table is None
    assert codes(issues) == ["stray_text"]
    issue = issues[0]
    assert issue.severity == "error" and issue.category == "format"
    assert issue.source is not None and issue.source.row == 3
    assert "only in" in issue.message


def test_owned_cells_of_a_shared_table_are_compared_with_the_study_only():
    data = b"study\tsource\tsubjects\nExample\nOther\n"
    spec = TABLES["characteristica"]
    _, issues = load_table("characteristica.tsv", data, spec, None, study="Example")
    assert codes(issues) == ["stray_text"]
    assert issues[0].source is not None and issues[0].source.row == 3


def test_broken_files_are_reported(make_study, valid_files):
    folder = make_study(
        {
            **valid_files,
            "study.json": '{"format": 2, "creator": "x", "licence": "open"}',
            "review.json": "{",
            "reference.json": '{"pmid": "123"}',
            "outputs_Tab2.tsv": "group\nall\n",
        }
    )
    study = load_study(folder)
    assert study.metadata is None and study.review is None
    assert "outputs" in study.broken
    assert study.of_kind("outputs") == []
    found = sorted(
        {(issue.code, issue.source.file) for issue in study.issues if issue.source}
    )
    assert found == [
        ("invalid_json", "review.json"),
        ("invalid_reference_json", "reference.json"),
        ("invalid_study_json", "study.json"),
        ("unknown_column", "outputs_Tab2.tsv"),
    ]
    study_issue = next(i for i in study.issues if i.code == "invalid_study_json")
    assert study_issue.field == "access"


def test_null_json_files_are_reported(make_study, valid_files):
    folder = make_study(
        {
            **valid_files,
            "study.json": "null",
            "review.json": "null",
            "reference.json": "null",
        }
    )
    study = load_study(folder)
    assert study.metadata is None and study.review is None
    assert study.reference is None
    found = sorted(
        {(issue.code, issue.source.file) for issue in study.issues if issue.source}
    )
    assert found == [
        ("invalid_reference_json", "reference.json"),
        ("invalid_review_json", "review.json"),
        ("invalid_study_json", "study.json"),
    ]


def test_symlinked_json_is_not_read(make_study, valid_files, tmp_path):
    outside = tmp_path / "outside.json"
    outside.write_text(valid_files["study.json"], encoding="utf-8")
    files = {name: data for name, data in valid_files.items() if name != "study.json"}
    folder = make_study(files)
    (folder / "study.json").symlink_to(outside)
    study = load_study(folder)
    assert study.metadata is None
    assert sorted(
        issue.code
        for issue in study.issues
        if issue.source and issue.source.file == "study.json"
    ) == ["missing_file", "symlink"]


@pytest.mark.parametrize("doi", ["10.1234/a%20b", "10.1234/a%0Ab"])
def test_identifiers_without_normalized_form_are_refused(make_study, valid_files, doi):
    # The server matches publications by normalized identifiers.
    import json

    study_json = json.loads(valid_files["study.json"])
    study_json["reference"] = {"doi": doi}
    reference = {"sid": "x", "name": "Example", "doi": doi}
    study = load_study(
        make_study(
            {
                **valid_files,
                "study.json": json.dumps(study_json),
                "reference.json": json.dumps(reference),
            }
        )
    )
    assert study.metadata is None and study.reference is None
    found = sorted(
        (issue.code, issue.source.file, issue.field)
        for issue in study.issues
        if issue.source
    )
    assert found == [
        ("invalid_reference_json", "reference.json", "doi"),
        ("invalid_study_json", "study.json", "reference.doi"),
    ]
    assert all("not a valid DOI" in issue.message for issue in study.issues)


def test_identifiers_keep_their_spelling(make_study, valid_files):
    import json

    study_json = json.loads(valid_files["study.json"])
    study_json["reference"] = {"doi": "10.1234/ABC%2Fdef"}
    reference = {"sid": "x", "name": "Example", "doi": "https://doi.org/10.1234/ABC"}
    study = load_study(
        make_study(
            {
                **valid_files,
                "study.json": json.dumps(study_json),
                "reference.json": json.dumps(reference),
            }
        )
    )
    assert study.metadata is not None and study.metadata.reference is not None
    assert study.metadata.reference.doi == "10.1234/ABC%2Fdef"
    assert study.reference is not None
    assert study.reference["doi"] == "https://doi.org/10.1234/ABC"


def test_load_table_stops_reading_at_the_row_limit():
    read = []

    def lines():
        yield b"subjects\tmean\n"
        for number in itertools.count():
            read.append(number)
            yield b"all\t1\n"

    with pytest.raises(StudyValidationError) as error:
        load_table(
            "outputs_Tab1.tsv", lines(), OUT, "Tab1", study="Example", limit=RowLimit(5)
        )
    [issue] = error.value.report.issues
    assert (issue.code, issue.message) == (
        "row_limit",
        "The study tables have more than 5 rows",
    )
    # The generator never ends, so the reader stopped at the sixth row.
    assert len(read) == 6


def test_row_limit_counts_the_rows_of_all_tables(make_study, valid_files):
    folder = make_study(valid_files)
    assert (
        sum(len(table.rows) for table in load_study(folder, max_rows=15).tables) == 15
    )
    with pytest.raises(StudyValidationError) as error:
        load_study(folder, max_rows=14)
    assert codes(error.value.report.issues) == ["row_limit"]


def test_study_reading_stops_at_the_row_limit(
    make_study, valid_files, tsv, monkeypatch
):
    rows = [{"subjects": "all", "measurement": "cmax", "mean": "1"}] * 100_000
    folder = make_study({**valid_files, "outputs_Tab2.tsv": tsv("outputs", *rows)})
    read = []

    def counting(chunks):
        for line in read_tsv(chunks):
            read.append(line)
            yield line

    monkeypatch.setattr(load, "read_tsv", counting)
    with pytest.raises(StudyValidationError) as error:
        load_study(folder, max_rows=20)
    assert codes(error.value.report.issues) == ["row_limit"]
    # Headers and the rows up to the first one beyond the limit.
    assert len(read) < 30
    monkeypatch.undo()
    assert len(load_study(folder).of_kind("outputs")[0].rows) == 100_000


def test_file_limit_counts_files_besides_study_and_reference_json(
    make_study, valid_files
):
    folder = make_study(valid_files)
    files = len(valid_files) - 2
    assert load_study(folder, max_files=files).issues == []
    with pytest.raises(StudyValidationError) as error:
        load_study(folder, max_files=files - 1)
    assert codes(error.value.report.issues) == ["file_limit"]
