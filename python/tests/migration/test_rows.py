import pytest
from migration_fixtures import IMAGES, SHEETS, STUDY, v1_example, v1_study

from pkdb.importers.folder import load_folder, parse_bundle
from pkdb.migration.model import NotConverted
from pkdb.migration.rows import render, study_tables, used_sources

INTERVENTION = STUDY["interventionset"]["interventions"][0]
OUTPUT = STUDY["outputset"]["outputs"][0]


def parsed(folder):
    return parse_bundle(load_folder(folder))


def cells(text):
    """The non-empty cells of each row but `study`, as sorted pairs, in sorted rows."""
    header, *rows = [line.split("\t") for line in text.splitlines()]
    return sorted(
        sorted((k, v) for k, v in zip(header, row, strict=True) if k != "study" and v)
        for row in rows
    )


@pytest.mark.parametrize("workbook", [True, False])
def test_rows_equal_the_rows_of_the_format_2_twin(tmp_path, valid_study, workbook):
    folder = v1_example(tmp_path / "v1", workbook=workbook)
    tables, decisions = study_tables(parsed(folder), "Example")
    rendered = render(tables)
    assert set(rendered) == {
        "subjects.tsv",
        "characteristica.tsv",
        "interventions.tsv",
        "outputs_Tab2.tsv",
        "timecourses_Fig1.tsv",
    }
    for name, text in rendered.items():
        assert cells(text) == cells((valid_study / name).read_text()), name
    assert decisions == []
    assert used_sources(tables) == {"Tab1", "TabA", "Tab2", "Fig1", "Text"}


def test_comments_lose_line_breaks_and_tabs(tmp_path):
    study = {
        **STUDY,
        "interventionset": {
            "interventions": [
                {
                    **INTERVENTION,
                    "descriptions": ["Given\twith water.\nFasted."],
                    "comments": [["curator", "Dose from\nTab1"]],
                }
            ]
        },
        "outputset": {},
    }
    folder = v1_study(tmp_path, study, {}, ("Tab1", "TabA"))
    tables, _ = study_tables(parsed(folder), "Example")
    [row] = tables["interventions.tsv"]
    assert row["comment"] == "Given with water. Fasted. / curator: Dose from Tab1"


def test_percent_statistics_are_written_in_percent(tmp_path):
    study = {
        **STUDY,
        "outputset": {"outputs": [{**OUTPUT, "sd": None, "cv": 0.123}]},
    }
    folder = v1_study(
        tmp_path, study, {"Tab2": [["mean"], [2.5]]}, ("Tab1", "TabA", "Tab2")
    )
    tables, _ = study_tables(parsed(folder), "Example")
    [row] = tables["outputs_Tab2.tsv"]
    assert row["cv"] == "12.3"


def test_times_not_reported_are_written_as_nr(tmp_path):
    output = {**OUTPUT, "time": "NR", "time_unit": "NR"}
    study = {**STUDY, "outputset": {"outputs": [output]}}
    folder = v1_study(tmp_path, study, SHEETS, IMAGES)
    tables, _ = study_tables(parsed(folder), "Example")
    [row] = tables["outputs_Tab2.tsv"]
    assert (row["time"], row["time_unit"]) == ("NR", "NR")


def test_schedules_and_dose_lists_are_decisions(tmp_path):
    intervention = {
        **INTERVENTION,
        "time": "S0T12R3",
        "application": "multiple dose",
    }
    study = {
        **STUDY,
        "interventionset": {"interventions": [intervention]},
        "outputset": {},
    }
    folder = v1_study(tmp_path, study, {}, ("Tab1", "TabA"))
    tables, decisions = study_tables(parsed(folder), "Example")
    [row] = tables["interventions.tsv"]
    assert (row["time"], row["interval"], row["doses"]) == ("0", "12", "3")
    assert [(d.kind, d.detail) for d in decisions] == [
        ("schedule", "D1: time 0, interval 12, doses 3")
    ]


def test_a_dose_list_is_a_semicolon_list_and_a_decision(tmp_path):
    intervention = {**INTERVENTION, "time": "0|12|40", "application": "multiple dose"}
    study = {
        **STUDY,
        "interventionset": {"interventions": [intervention]},
        "outputset": {},
    }
    folder = v1_study(tmp_path, study, {}, ("Tab1", "TabA"))
    tables, decisions = study_tables(parsed(folder), "Example")
    [row] = tables["interventions.tsv"]
    assert (row["time"], row["interval"], row["doses"]) == ("0;12;40", "", "")
    assert [(d.kind, d.detail) for d in decisions] == [("schedule", "D1: time 0;12;40")]


def test_the_interventions_of_a_row_are_a_comma_list(tmp_path):
    interventions = [INTERVENTION, {**INTERVENTION, "name": "D2", "time": 12}]
    study = {
        **STUDY,
        "interventionset": {"interventions": interventions},
        "outputset": {"outputs": [{**OUTPUT, "interventions": "D1, D2"}]},
    }
    folder = v1_study(tmp_path, study, SHEETS, IMAGES)
    tables, _ = study_tables(parsed(folder), "Example")
    [row] = tables["outputs_Tab2.tsv"]
    assert row["interventions"] == "D1,D2"


def test_characteristica_without_an_image_take_the_image_of_their_subject(tmp_path):
    group = {
        "name": "all",
        "count": 2,
        "image": "Tab1",
        "characteristica": [{"measurement_type": "sex", "choice": "M"}],
    }
    study = {
        **STUDY,
        "groupset": {"groups": [group]},
        "individualset": {},
        "interventionset": {},
        "outputset": {},
    }
    folder = v1_study(tmp_path, study, {}, ("Tab1",))
    tables, _ = study_tables(parsed(folder), "Example")
    [row] = tables["characteristica.tsv"]
    assert (row["subjects"], row["source"]) == ("all", "Tab1")


def test_a_group_with_count_one_becomes_an_individual_and_a_decision(tmp_path):
    groups = [{"name": "all", "count": 1, "image": "Tab1"}]
    study = {
        **STUDY,
        "groupset": {"groups": groups},
        "individualset": {},
        "outputset": {},
    }
    folder = v1_study(tmp_path, study, {}, ("Tab1",))
    tables, decisions = study_tables(parsed(folder), "Example")
    assert tables["subjects.tsv"] == [
        {"name": "all", "parent": "", "count": "1", "source": "Tab1", "comment": ""}
    ]
    assert ("group_count_1", "all") in {(d.kind, d.detail) for d in decisions}


@pytest.mark.parametrize(
    ("groups", "individuals", "code"),
    [
        ([{"name": "a;b", "count": 2}], [], "subject_name"),
        ([{"name": "S1", "count": 2}], [{"name": "S1", "group": "S1"}], "subject_name"),
    ],
)
def test_subject_names_that_format_2_cannot_hold_refuse_the_study(
    tmp_path, groups, individuals, code
):
    study = {
        **STUDY,
        "groupset": {"groups": groups},
        "individualset": {"individuals": individuals},
        "outputset": {},
        "interventionset": {},
    }
    folder = v1_study(tmp_path, study, {}, ())
    with pytest.raises(NotConverted) as error:
        study_tables(parsed(folder), "Example")
    assert error.value.code == code


def test_render_refuses_a_cell_without_a_column():
    with pytest.raises(ValueError, match="label"):
        render({"subjects.tsv": [{"name": "all", "label": "x"}]})
