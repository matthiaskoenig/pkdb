from pathlib import Path

import pytest

from pkdb.studyformat.issues import column_letter, make_issue
from pkdb.studyformat.layout import scan_folder, workbook_tables
from pkdb.studyformat.sync import _sheet_order


def codes(issues):
    return sorted(
        (issue.code, issue.source.file if issue.source else None) for issue in issues
    )


def test_column_letter():
    assert [column_letter(i) for i in (0, 25, 26, 701, 702)] == [
        "A",
        "Z",
        "AA",
        "ZZ",
        "AAA",
    ]


def test_make_issue_location_and_defaults():
    issue = make_issue(
        "invalid_number",
        "Expected a number",
        file="outputs_Tab2.tsv",
        line=3,
        column=13,
        header="mean",
    )
    assert issue.severity == "error"
    assert issue.category == "schema"
    assert issue.stage == "parse"
    assert issue.source is not None
    assert issue.source.sheet == "outputs_Tab2"
    assert (issue.source.row, issue.source.column, issue.source.cell) == (3, "N", "N3")
    assert issue.source.header == "mean"
    warning = make_issue("unused_subject", "unused", file="subjects.tsv", line=2)
    assert warning.severity == "warning"
    assert warning.stage == "validate"
    located = make_issue("missing_file", "x", file="study.json")
    assert located.source is not None
    assert located.source.sheet is None


def test_make_issue_suggestions():
    issue = make_issue("unknown_column", "x", file="a.tsv", candidates=["measurement"])
    assert issue.suggestions[0].candidates == ["measurement"]


def test_scan_valid_folder(make_study, valid_files):
    folder = make_study(
        {**valid_files, "Example.xlsx": b"wb", "~$Example.xlsx": b"lock"}
    )
    layout = scan_folder(folder)
    assert layout.issues == []
    assert (layout.study, layout.substance) == ("Example", "caffeine")
    assert [table.name for table in layout.tables] == [
        "subjects.tsv",
        "interventions.tsv",
        "characteristica.tsv",
        "outputs_Tab2.tsv",
        "timecourses_Fig1.tsv",
        "scatters_Fig2.tsv",
    ]
    assert layout.attachments == [
        "Example.pdf",
        "Example_Fig1.png",
        "Example_Fig2.png",
        "Example_Tab1.png",
        "Example_Tab2.png",
        "Example_TabA.png",
    ]
    assert "study.json" in layout.files and "Example.xlsx" not in layout.files


def test_scan_reports_unknown_legacy_and_missing_files(make_study):
    folder = make_study(
        {
            "study.json": "{}",
            "groups.tsv": "name\n",
            "outputs.tsv": "a\n",
            "data.csv": "a\n",
            "Other.xlsx": b"x",
            "notes.json": "{}",
            ".Example_Tab1.tsv": "a\n",
            ".gitkeep": "",
            "Example.docx": b"doc",
        }
    )
    (folder / "figures").mkdir()
    (folder / ".pkdb").mkdir()
    layout = scan_folder(folder)
    assert codes(layout.issues) == [
        ("legacy_file", ".Example_Tab1.tsv"),
        ("missing_file", "reference.json"),
        ("missing_file", "review.json"),
        ("missing_file", "subjects.tsv"),
        ("unknown_directory", "figures"),
        ("unknown_file", "Other.xlsx"),
        ("unknown_file", "data.csv"),
        ("unknown_file", "groups.tsv"),
        ("unknown_file", "notes.json"),
        ("unknown_file", "outputs.tsv"),
    ]
    assert layout.attachments == ["Example.docx"]


def test_scan_rejects_symlinks(make_study, valid_files, tmp_path):
    folder = make_study(valid_files)
    (tmp_path / "outside.png").write_bytes(b"png")
    (folder / "Example_Fig9.png").symlink_to(tmp_path / "outside.png")
    assert ("symlink", "Example_Fig9.png") in codes(scan_folder(folder).issues)


def test_scan_relative_folder_resolves_study_and_substance(
    make_study, valid_files, monkeypatch
):
    folder = make_study(valid_files)
    monkeypatch.chdir(folder)
    layout = scan_folder(Path("."))
    assert (layout.study, layout.substance) == ("Example", "caffeine")
    assert layout.folder == folder.resolve()


@pytest.mark.parametrize("name", ["publication", "validate"])
def test_reserved_study_names(make_study, valid_files, name):
    layout = scan_folder(make_study(valid_files, name=name))
    [issue] = [issue for issue in layout.issues if issue.code == "reserved_name"]
    assert (issue.severity, issue.category) == ("error", "layout")
    assert repr(name) in issue.message


def test_names_containing_reserved_words_are_allowed(make_study, valid_files):
    layout = scan_folder(make_study(valid_files, name="Publication2020"))
    assert "reserved_name" not in {issue.code for issue in layout.issues}


def table_issues(layout, code):
    return [issue for issue in layout.issues if issue.code == code]


def test_table_names_of_at_most_31_characters_fit_an_excel_sheet(
    make_study, valid_files
):
    exact = "timecourses_Fig1_plasma_conc_ab"
    assert len(exact) == 31
    folder = make_study({**valid_files, f"{exact}.tsv": "a\n"})
    layout = scan_folder(folder)
    assert table_issues(layout, "table_name_too_long") == []
    assert f"{exact}.tsv" in [table.name for table in layout.tables]


def test_long_table_names_are_reported(make_study, valid_files):
    name = "timecourses_Fig1_plasma_concentrations.tsv"
    assert len(name.removesuffix(".tsv")) == 38
    folder = make_study({**valid_files, name: "a\n"})
    [issue] = table_issues(scan_folder(folder), "table_name_too_long")
    assert (issue.severity, issue.category, issue.stage) == (
        "error",
        "layout",
        "parse",
    )
    assert issue.source is not None
    assert issue.source.file == name
    assert "Excel limits sheet names to 31 characters" in issue.message
    assert issue.suggestions
    assert "shorter source" in issue.suggestions[0].message


def test_table_names_equal_ignoring_case_are_duplicates(make_study, valid_files):
    folder = make_study(
        {**valid_files, "outputs_TabA.tsv": "a\n", "outputs_Taba.tsv": "a\n"}
    )
    [issue] = table_issues(scan_folder(folder), "duplicate_table_name")
    assert (issue.severity, issue.category) == ("error", "layout")
    assert issue.source is not None
    assert issue.source.file == "outputs_Taba.tsv"
    # Both tables are named alike, as files.
    assert issue.message.startswith(
        "The table file 'outputs_Taba.tsv' equals 'outputs_TabA.tsv' ignoring case"
    )


def test_distinct_table_names_are_not_duplicates(make_study, valid_files):
    folder = make_study(valid_files)
    assert table_issues(scan_folder(folder), "duplicate_table_name") == []


def test_workbook_tables_follow_the_sheets_of_the_workbook(make_study, valid_files):
    folder = make_study(
        {
            **valid_files,
            "outputs_Tab10.tsv": valid_files["outputs_Tab2.tsv"],
            "Example_Tab2.tsv": "cmax\t2.5\n",
        }
    )
    tables = workbook_tables(scan_folder(folder))
    assert tables == [
        ("subjects.tsv", "subjects"),
        ("interventions.tsv", "interventions"),
        ("characteristica.tsv", "characteristica"),
        ("outputs_Tab2.tsv", "outputs"),
        ("outputs_Tab10.tsv", "outputs"),
        ("timecourses_Fig1.tsv", "timecourses"),
        ("scatters_Fig2.tsv", "scatters"),
        ("Example_Tab2.tsv", "raw"),
    ]
    # The order is the sheet order of the sync.
    files = [file for file, _ in tables]
    assert files == sorted(files, key=lambda file: _sheet_order(file, "Example"))
