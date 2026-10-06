from io import BytesIO

import pytest

from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.layout import scan_folder
from pkdb.studyformat.load import load_study
from pkdb.studyformat.raw import load_raw, parse_raw_file, raw_file, render_raw


@pytest.mark.parametrize(
    ("name", "study", "source"),
    [
        ("Example_Tab2.tsv", "Example", "Tab2"),
        ("Smith_2020_Tab1_a.tsv", "Smith_2020", "Tab1_a"),
        ("Example_Fig1.tsv", "Example", None),
        ("Example_Text.tsv", "Example", None),
        ("Other_Tab2.tsv", "Example", None),
        ("outputs_Tab2.tsv", "outputs", None),
        ("Example_Tab2.csv", "Example", None),
    ],
)
def test_parse_raw_file(name, study, source):
    assert parse_raw_file(name, study) == source


def test_raw_file_name():
    assert raw_file("Example", "Tab2") == "Example_Tab2.tsv"


def test_render_raw_keeps_order_and_text():
    data = "Group\tAge\t\t\n\t\t\t\nmen\t 1.50 \t007\t\nwomen\t12 ± 3\t=A1\n"
    raw, issues = load_raw("Example_Tab1.tsv", BytesIO(data.encode()), "Tab1")
    assert issues == []
    assert raw is not None
    assert render_raw(raw) == "Group\tAge\t\nmen\t1.50\t007\nwomen\t12 ± 3\t=A1\n"
    assert [row.line for row in raw.rows] == [1, 3, 4]


def test_render_raw_of_empty_grid_removes_the_file():
    raw, _ = load_raw("Example_Tab1.tsv", BytesIO(b"\t\n\n"), "Tab1")
    assert raw is not None
    assert render_raw(raw) is None


def test_merge_conflict_markers_stop_loading():
    data = b"a\tb\n<<<<<<< HEAD\nc\td\n=======\nc\te\n>>>>>>> other\n"
    raw, issues = load_raw("Example_Tab1.tsv", BytesIO(data), "Tab1")
    assert raw is None
    assert [issue.code for issue in issues] == ["merge_conflict"]


def test_layout_lists_raw_tables(make_study, valid_files):
    folder = make_study({**valid_files, "Example_Tab2.tsv": "a\tb\n"})
    layout = scan_folder(folder)
    assert [(raw.name, raw.source) for raw in layout.raw_tables] == [
        ("Example_Tab2.tsv", "Tab2")
    ]
    assert not [issue for issue in layout.issues if issue.code == "unknown_file"]


def test_reserved_kind_names(make_study, valid_files):
    folder = make_study(valid_files, name="outputs")
    codes = [issue.code for issue in scan_folder(folder).issues]
    assert "reserved_name" in codes


def test_formatter_writes_canonical_raw_table(make_study, valid_files):
    folder = make_study({**valid_files, "Example_Tab2.tsv": "x\t 1 \t\r\n\r\ny\t2\r\n"})
    result = format_folder(folder)
    assert result.ok
    assert (folder / "Example_Tab2.tsv").read_text() == "x\t1\ny\t2\n"
    raw = load_study(folder).raw("Example_Tab2.tsv")
    assert raw is not None
    assert raw.source == "Tab2"


def test_raw_table_needs_its_image(make_study, valid_files, sf_vocabulary):
    from pkdb.studyformat.validation import validate_folder

    files = {**valid_files, "Example_Tab9.tsv": "a\n"}
    folder = make_study(files)
    format_folder(folder)
    issues = validate_folder(folder, sf_vocabulary).issues
    assert any(
        issue.code == "missing_image"
        and issue.source is not None
        and issue.source.file == "Example_Tab9.tsv"
        for issue in issues
    )


def test_raw_sheet_name_length_is_checked(make_study, valid_files):
    name = "A" * 26
    folder = make_study({**valid_files, f"{name}_Tab12.tsv": "a\n"}, name=name)
    codes = [issue.code for issue in scan_folder(folder).issues]
    assert "table_name_too_long" in codes
