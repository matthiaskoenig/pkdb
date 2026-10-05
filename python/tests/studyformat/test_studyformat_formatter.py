import json
from pathlib import Path

from pkdb.studyformat.formatter import format_folder, subject_order
from pkdb.studyformat.load import load_table
from pkdb.studyformat.tables import TABLES


def read(folder, name):
    return (folder / name).read_text(encoding="utf-8")


def test_valid_study_is_stable(valid_study):
    assert format_folder(valid_study).changes == []


def test_owned_columns_are_filled(valid_study):
    lines = read(valid_study, "outputs_Tab2.tsv").splitlines()
    assert lines[1].startswith("Example\tTab2\tall\tD1\tcmax")
    assert (
        read(valid_study, "subjects.tsv").splitlines()[1].startswith("Example\tall\t")
    )


def test_messy_spreadsheet_export_is_normalized(make_study, valid_files):
    # Review focus 1: CRLF, BOM, quoted cells, dropped trailing tabs, NBSP, NA,
    # reordered and missing columns, wrong owned values, unsorted rows.
    messy = (
        f"{chr(0xFEFF)}mean\tsubjects\tstudy\tinterventions\tmeasurement\tunit\r\n"
        '2.50\tS2\tWrong\t"D1"\tcmax\tmg/l\r\n'
        f"{chr(0xA0)}3.0\tall\t\tD1\tcmax\tmg/l\r\n"
        "NA\tS1\t\tD1\tcmax\r\n"
        "\t\t\t\t\t\r\n"
    )
    folder = make_study({**valid_files, "outputs_Tab2.tsv": messy})
    result = format_folder(folder)
    assert result.ok
    lines = read(folder, "outputs_Tab2.tsv").splitlines()
    assert lines[0].split("\t") == list(TABLES["outputs"].names)
    rows = [line.split("\t") for line in lines[1:]]
    names = TABLES["outputs"].names
    assert [row[names.index("subjects")] for row in rows] == ["all", "S1", "S2"]
    assert [row[names.index("mean")] for row in rows] == ["3", "", "2.5"]
    assert {row[names.index("study")] for row in rows} == {"Example"}
    assert {row[names.index("source")] for row in rows} == {"Tab2"}
    assert b"\r" not in (folder / "outputs_Tab2.tsv").read_bytes()
    assert format_folder(folder).changes == []


def test_check_mode_writes_nothing(make_study, valid_files):
    # The valid study.json is already canonical; a compact copy needs rewriting.
    compact = json.dumps(json.loads(valid_files["study.json"]))
    folder = make_study({**valid_files, "study.json": compact})
    before = {path.name: path.read_bytes() for path in folder.iterdir()}
    result = format_folder(folder, check=True)
    assert {change.file for change in result.changes} >= {"subjects.tsv", "study.json"}
    assert {path.name: path.read_bytes() for path in folder.iterdir()} == before


def test_empty_optional_tables_are_removed(make_study, valid_files, tsv):
    folder = make_study(
        {
            **valid_files,
            "outputs_Tab9.tsv": tsv("outputs"),
            "characteristica.tsv": tsv("characteristica"),
        }
    )
    result = format_folder(folder)
    assert {(c.file, c.action) for c in result.changes} >= {
        ("outputs_Tab9.tsv", "delete"),
        ("characteristica.tsv", "delete"),
    }
    assert not (folder / "outputs_Tab9.tsv").exists()


def test_empty_subjects_table_keeps_its_header(make_study, valid_files, tsv):
    folder = make_study({**valid_files, "subjects.tsv": tsv("subjects")})
    format_folder(folder)
    assert read(folder, "subjects.tsv") == "\t".join(TABLES["subjects"].names) + "\n"


def test_unformattable_file_is_left_unchanged(make_study, valid_files):
    folder = make_study({**valid_files, "outputs_Tab2.tsv": "group\tmean\nall\t1\n"})
    result = format_folder(folder)
    assert not result.ok
    assert [issue.code for issue in result.issues] == ["unknown_column"]
    assert read(folder, "outputs_Tab2.tsv") == "group\tmean\nall\t1\n"
    assert "outputs_Tab2.tsv" not in {change.file for change in result.changes}


def test_json_files_are_canonical(make_study, valid_files):
    folder = make_study(
        {
            **valid_files,
            "reference.json": json.dumps(
                {"sid": "123", "name": "Example", "pmid": "123"}, indent=4
            ),
            "review.json": '{"status": "draft", "reviewers": []}',
        }
    )
    format_folder(folder)
    assert read(folder, "reference.json") == (
        '{\n  "sid": "123",\n  "name": "Example",\n  "pmid": "123"\n}\n'
    )
    assert read(folder, "review.json") == '{\n  "status": "draft"\n}\n'
    assert json.loads(read(folder, "study.json"))["curators"] == [
        {"user": "curator", "rating": 3.0}
    ]


def test_invalid_json_is_not_touched(make_study, valid_files):
    folder = make_study({**valid_files, "study.json": '{"reference":,}'})
    result = format_folder(folder)
    assert [issue.code for issue in result.issues] == ["invalid_json"]
    assert read(folder, "study.json") == '{"reference":,}'


def test_subject_order_is_depth_first_with_all_first():
    data = (
        b"name\tparent\n"
        b"b2\tb\nS10\ta\nb\tall\na\tall\nS2\ta\nall\t\norphan\tmissing\nx\ty\ny\tx\n"
    )
    table, _ = load_table("subjects.tsv", data, TABLES["subjects"], None)
    order = subject_order(table)
    assert sorted(order, key=order.__getitem__) == [
        "all",
        "a",
        "S2",
        "S10",
        "b",
        "b2",
        "orphan",
        "x",
        "y",
    ]


def test_timecourse_points_sort_by_label_then_numeric_time(
    make_study, valid_files, tsv
):
    base = {"subjects": "all", "measurement": "concentration", "time_unit": "h"}
    rows = [
        {**base, "label": "b", "time": "1"},
        {**base, "label": "a", "time": "10"},
        {**base, "label": "a", "time": "2"},
        {**base, "label": "a", "time": "NR"},
    ]
    folder = make_study(
        {**valid_files, "timecourses_Fig1.tsv": tsv("timecourses", *rows)}
    )
    format_folder(folder)
    names = TABLES["timecourses"].names
    body = [
        line.split("\t")
        for line in read(folder, "timecourses_Fig1.tsv").splitlines()[1:]
    ]
    assert [(r[names.index("label")], r[names.index("time")]) for r in body] == [
        ("a", "2"),
        ("a", "10"),
        ("a", "NR"),
        ("b", "1"),
    ]


def test_duplicate_subject_names_do_not_make_formatting_unstable(
    make_study, valid_files, tsv
):
    rows = [
        {"name": "all", "count": "2", "source": "Tab1"},
        {"name": "a", "parent": "all", "source": "Tab1"},
        {"name": "b", "parent": "all", "source": "Tab1"},
        {"name": "x", "parent": "b", "source": "Tab1"},
        {"name": "x", "parent": "a", "source": "Tab1"},
    ]
    folder = make_study({**valid_files, "subjects.tsv": tsv("subjects", *rows)})
    format_folder(folder)
    assert format_folder(folder).changes == []


def test_formatting_the_current_folder_keeps_the_study_name(valid_study, monkeypatch):
    monkeypatch.chdir(valid_study)
    assert format_folder(Path(".")).changes == []
    names = TABLES["outputs"].names
    row = read(valid_study, "outputs_Tab2.tsv").splitlines()[1].split("\t")
    assert row[names.index("study")] == "Example"
