from pathlib import Path

import pytest

from pkdb.studyformat.issues import column_letter, make_issue
from pkdb.studyformat.layout import scan_folder


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
