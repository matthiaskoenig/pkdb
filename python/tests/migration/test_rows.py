import pytest
from migration_fixtures import (
    DATASET,
    IMAGES,
    SCATTER_OUTPUTS,
    SCATTER_SHEET,
    SHEETS,
    STUDY,
    v1_example,
    v1_full_example,
    v1_study,
)

from pkdb.importers.folder import load_folder, parse_bundle
from pkdb.migration.model import NotConverted
from pkdb.migration.rows import render, study_tables, used_sources
from pkdb.preparation import prepare

INTERVENTION = STUDY["interventionset"]["interventions"][0]
OUTPUT = STUDY["outputset"]["outputs"][0]
X_OUTPUT, Y_OUTPUT = SCATTER_OUTPUTS


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


@pytest.mark.parametrize("workbook", [True, False])
def test_the_full_twin_with_scatters(tmp_path, valid_study, sf_vocabulary, workbook):
    folder = v1_full_example(tmp_path / "v1", workbook=workbook)
    issues = prepare(folder, vocabulary=sf_vocabulary).report.issues
    assert not [i for i in issues if i.severity == "error"]
    tables, decisions = study_tables(parsed(folder), "Example")
    rendered = render(tables)
    assert set(rendered) == {path.name for path in valid_study.glob("*.tsv")}
    assert "scatters_Fig2.tsv" in rendered
    for name, text in rendered.items():
        assert cells(text) == cells((valid_study / name).read_text()), name
    assert decisions == []
    assert "Fig2" in used_sources(tables)


def test_array_outputs_become_outputs_or_timecourses(tmp_path):
    array = {**STUDY["outputset"]["outputs"][0], "output_type": "array"}
    labelled = {**STUDY["outputset"]["outputs"][1], "output_type": "array"}
    study = {**STUDY, "outputset": {"outputs": [array, labelled]}}
    folder = v1_study(tmp_path, study, SHEETS, IMAGES)
    tables, decisions = study_tables(parsed(folder), "Example")
    assert len(tables["outputs_Tab2.tsv"]) == 1
    assert [row["label"] for row in tables["timecourses_Fig1.tsv"]] == [
        "drug_plasma"
    ] * 3
    assert {d.kind for d in decisions} == {"array_output"}
    assert [d.detail for d in decisions] == [
        "1 array output in outputs_Tab2.tsv",
        "3 array outputs in timecourses_Fig1.tsv",
    ]


def test_a_geometric_mean_moves_to_gmean(tmp_path):
    output = {**STUDY["outputset"]["outputs"][0], "calculation_type": "geometric mean"}
    study = {**STUDY, "outputset": {"outputs": [output]}}
    folder = v1_study(tmp_path, study, SHEETS, IMAGES)
    tables, decisions = study_tables(parsed(folder), "Example")
    [row] = tables["outputs_Tab2.tsv"]
    assert (row["mean"], row["gmean"], row["calculation"]) == (
        "",
        "2.5",
        "geometric mean",
    )
    # It also has sd: arithmetic or geometric is unclear.
    assert [d.kind for d in decisions] == ["geometric_spread"]


def test_a_geometric_mean_of_a_characteristic_moves_to_gmean(tmp_path):
    age = {"measurement_type": "age", "mean": 35, "unit": "yr"}
    group = {
        **STUDY["groupset"]["groups"][0],
        "characteristica": [{**age, "calculation_type": "geometric mean"}],
    }
    study = {
        **STUDY,
        "groupset": {"groups": [group]},
        "individualset": {},
        "outputset": {},
    }
    folder = v1_study(tmp_path, study, {}, ("Tab1",))
    tables, decisions = study_tables(parsed(folder), "Example")
    [row] = tables["characteristica.tsv"]
    assert (row["mean"], row["gmean"]) == ("", "35")
    assert decisions == []


def scatter_study(root, *, x=None, y=None, dataset=None, sheets=None):
    """The scatter of the twin, with changed outputs, datasets or sheets."""
    study = {
        **STUDY,
        "outputset": {
            "outputs": [{**X_OUTPUT, **(x or {})}, {**Y_OUTPUT, **(y or {})}]
        },
        "dataset": dataset or DATASET,
    }
    sheets = {**SCATTER_SHEET, **(sheets or {})}
    return v1_study(root, study, sheets, (*IMAGES, "Fig2", "Fig3"))


def scatter(name, *labels, shared=("individual",)):
    subset = {"name": name, "dimensions": list(labels), "shared": list(shared)}
    return {"name": name, "data_type": "scatter", "image": "Fig2", "subsets": [subset]}


def test_a_scatter_is_named_by_its_subset_and_takes_the_source_of_its_points(
    tmp_path,
):
    # The dataset is named and illustrated by another figure than its points.
    named = scatter("age_vs_cmax", "x_age", "y_cmax")
    dataset = {"data": [{**named, "name": "Fig3", "image": "Fig3"}]}
    folder = scatter_study(
        tmp_path,
        x={"label": "x_age", "comments": [["curator", "Read from Fig2"]]},
        y={"label": "y_cmax"},
        dataset=dataset,
    )
    tables, decisions = study_tables(parsed(folder), "Example")
    rows = tables["scatters_Fig2.tsv"]
    assert [(row["name"], row["subjects"]) for row in rows] == [
        ("age_vs_cmax", "S1"),
        ("age_vs_cmax", "S2"),
    ]
    assert {row["comment"] for row in rows} == {"curator: Read from Fig2"}
    assert [(d.kind, d.detail) for d in decisions] == [
        (
            "scatter_label",
            "age_vs_cmax: x_age, y_cmax become age_vs_cmax_x, age_vs_cmax_y",
        )
    ]


def test_array_points_of_a_scatter_are_a_decision(tmp_path):
    array = {"output_type": "array"}
    folder = scatter_study(tmp_path, x=array, y=array)
    tables, decisions = study_tables(parsed(folder), "Example")
    assert len(tables["scatters_Fig2.tsv"]) == 2
    assert [(d.kind, d.detail) for d in decisions] == [
        ("array_output", "4 array outputs in scatters_Fig2.tsv")
    ]


TWICE = {"Fig2": [["subject", "age", "cmax"], ["S1", 30, 2], ["S1", 40, 3]]}
LABELS = ("age_vs_cmax_x", "age_vs_cmax_y")
BY_TIME = scatter("age_vs_cmax", *LABELS, shared=["time"])


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        pytest.param({"sheets": TWICE}, "scatter_pairs", id="subject twice"),
        pytest.param({"y": {"subset": "subject==S1"}}, "scatter_pairs", id="unpaired"),
        pytest.param(
            {"x": {"time": 1, "time_unit": "h"}, "dataset": {"data": [BY_TIME]}},
            "scatter_pairs",
            id="paired by time",
        ),
        pytest.param({"y": {"sd": 0.5}}, "scatter_statistics", id="sd"),
        pytest.param({"x": {"choice": "M"}}, "scatter_statistics", id="choice"),
        pytest.param(
            {"y": {"calculation_type": "geometric mean"}},
            "scatter_statistics",
            id="calculation",
        ),
        pytest.param(
            {"dataset": {"data": [*DATASET["data"], scatter("other", *LABELS)]}},
            "scatter_outputs",
            id="output in two scatters",
        ),
        pytest.param(
            {"x": {"output_type": "timecourse"}},
            "scatter_outputs",
            id="timecourse in a scatter",
        ),
        pytest.param(
            {"y": {"source": "Fig3"}, "sheets": {"Fig3": SCATTER_SHEET["Fig2"]}},
            "scatter_source",
            id="two sources",
        ),
        pytest.param(
            {"dataset": {"data": [*DATASET["data"], *DATASET["data"]]}},
            "scatter_name",
            id="two names",
        ),
        pytest.param(
            {"dataset": {"data": [scatter("age_vs_cmax", LABELS[0])]}},
            "scatter_dimensions",
            id="one dimension",
        ),
    ],
)
def test_scatters_that_format_2_cannot_hold_refuse_the_study(tmp_path, changes, code):
    folder = scatter_study(tmp_path, **changes)
    with pytest.raises(NotConverted) as error:
        study_tables(parsed(folder), "Example")
    assert error.value.code == code
