"""Hidden TSV tables generated from a study's Excel workbook."""

import openpyxl
import pytest

from pkdb.tsv import sync_tsvs


def workbook(folder, sheets):
    book = openpyxl.Workbook()
    book.remove(book.active)
    for name, rows in sheets.items():
        sheet = book.create_sheet(name)
        for row in rows:
            sheet.append(row)
    book.save(folder / f"{folder.name}.xlsx")


@pytest.fixture
def folder(tmp_path):
    folder = tmp_path / "Example2020"
    folder.mkdir()
    (folder / "study.json").write_text('{"name": "Example2020"}')
    workbook(
        folder,
        {
            "Tab1": [
                ["Description row is skipped"],
                ["study", "group", "count", "mean", None],
                ["Example2020", "all", 12, 1.5, None],
                ["# a comment row"],
                [None, None, None, None, None],
                ["Example2020", "young", None, 2, None],
            ],
            "Fig2": [["notes"], ["study", "time"], ["Example2020", 0.5]],
            "Notes": [["ignored"], ["a"], [1]],
            "FigEmpty": [["only a description"]],
        },
    )
    return folder


def test_sheets_are_exported_like_the_legacy_upload(folder):
    change = sync_tsvs(folder)
    assert change == "Created 2 TSV files from Example2020.xlsx"
    assert (folder / ".Example2020_Tab1.tsv").read_text() == (
        "study\tgroup\tcount\tmean\n"
        "Example2020\tall\t12.0\t1.5\n"
        "Example2020\tyoung\tNA\t2.0\n"
    )
    assert (folder / ".Example2020_Fig2.tsv").read_text() == (
        "study\ttime\nExample2020\t0.5\n"
    )
    assert sorted(p.name for p in folder.glob(".*.tsv")) == [
        ".Example2020_Fig2.tsv",
        ".Example2020_Tab1.tsv",
    ]
    before = {p.name: p.stat().st_mtime_ns for p in folder.iterdir()}
    assert sync_tsvs(folder) is None
    assert {p.name: p.stat().st_mtime_ns for p in folder.iterdir()} == before


def test_changed_and_orphaned_tables_are_updated_and_removed(folder):
    sync_tsvs(folder)
    (folder / ".Example2020_Tab1.tsv").write_text("stale\n")
    (folder / ".Example2020_TabOld.tsv").write_text("orphan\n")
    (folder / ".Example2020_TabUsed.tsv").write_text("referenced\n")
    (folder / ".Example2020_TabSheet.tsv").write_text("sheet deleted\n")
    (folder / "study.json").write_text(
        '{"name": "Example2020", "outputset": {"outputs": '
        '[{"source": ".Example2020_TabUsed.tsv"}, {"source": "TabSheet"}]}}'
    )
    assert sync_tsvs(folder) == (
        "Updated 1 and removed 1 TSV files from Example2020.xlsx"
    )
    assert (folder / ".Example2020_Tab1.tsv").read_text().startswith("study\t")
    assert not (folder / ".Example2020_TabOld.tsv").exists()
    assert (folder / ".Example2020_TabUsed.tsv").exists()
    assert (folder / ".Example2020_TabSheet.tsv").exists()


def test_folders_without_workbook_are_untouched(tmp_path):
    (tmp_path / ".Other_Tab1.tsv").write_text("kept\n")
    assert sync_tsvs(tmp_path) is None
    assert (tmp_path / ".Other_Tab1.tsv").read_text() == "kept\n"


def test_unreadable_workbook_is_reported(tmp_path):
    folder = tmp_path / "Broken2020"
    folder.mkdir()
    (folder / "Broken2020.xlsx").write_bytes(b"not a workbook")
    with pytest.raises(ValueError, match="Cannot read Broken2020.xlsx"):
        sync_tsvs(folder)


@pytest.mark.parametrize("study_folder", ["xlsx"], indirect=True)
def test_validate_creates_tsv_tables_before_validation(
    study_folder, vocabulary, tmp_path, capsys
):
    import json

    from pkdb.cli import main

    book = openpyxl.load_workbook(study_folder / "Example.xlsx")
    book.copy_worksheet(book["Results"]).title = "TabResults"
    book.save(study_folder / "Example.xlsx")
    lock = tmp_path / "vocabulary.lock.json"
    vocabulary.save(lock)
    args = ["validate", str(study_folder), "--vocabulary", str(lock), "--offline"]
    assert main([*args, "--format", "json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["tables_updated"] == "Created 1 TSV files from Example.xlsx"
    assert (
        (study_folder / ".Example_TabResults.tsv")
        .read_text()
        .startswith("time\tmean\n")
    )
    assert main([*args, "--format", "json"]) == 0
    assert "tables_updated" not in json.loads(capsys.readouterr().out)
