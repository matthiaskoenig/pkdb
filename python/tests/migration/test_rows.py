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
from vocabulary_fixtures import studyformat_vocabulary

from pkdb.importers.folder import load_folder, parse_bundle
from pkdb.migration.model import DroppedRow, NotConverted
from pkdb.migration.rows import render, study_tables, used_sources
from pkdb.migration.sources import image_sources
from pkdb.preparation import prepare

INTERVENTION = STUDY["interventionset"]["interventions"][0]
OUTPUT, TIMECOURSE = STUDY["outputset"]["outputs"]
X_OUTPUT, Y_OUTPUT = SCATTER_OUTPUTS


def tables_of(folder):
    """The format 2 tables of the v1 study `Example` and the decisions to check."""
    study = parse_bundle(load_folder(folder))
    return study_tables(
        study,
        "Example",
        images=image_sources(folder, "Example"),
        vocabulary=studyformat_vocabulary(),
    )


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
    tables, decisions = tables_of(folder)
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
    tables, _ = tables_of(folder)
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
    tables, _ = tables_of(folder)
    [row] = tables["outputs_Tab2.tsv"]
    assert row["cv"] == "12.3"


def test_times_not_reported_are_written_as_nr(tmp_path):
    output = {**OUTPUT, "time": "NR", "time_unit": "NR"}
    study = {**STUDY, "outputset": {"outputs": [output]}}
    folder = v1_study(tmp_path, study, SHEETS, IMAGES)
    tables, _ = tables_of(folder)
    [row] = tables["outputs_Tab2.tsv"]
    assert (row["time"], row["time_unit"]) == ("NR", "NR")


def test_characteristica_of_measurements_with_a_time_have_time_nr(tmp_path):
    # Format 1 characteristica have no time; format 2 needs one for concentration.
    group = {
        **STUDY["groupset"]["groups"][0],
        "characteristica": [
            {
                "measurement_type": "concentration",
                "substance": "drug",
                "tissue": "plasma",
                "mean": 5,
                "unit": "mg/l",
            },
            {"measurement_type": "age", "mean": 30, "unit": "yr"},
        ],
    }
    study = {**STUDY, "groupset": {"groups": [group]}, "outputset": {}}
    folder = v1_study(tmp_path, study, {}, IMAGES)
    tables, decisions = tables_of(folder)
    times = {
        row["measurement"]: (row["time"], row["time_unit"])
        for row in tables["characteristica.tsv"]
    }
    assert times == {"concentration": ("NR", ""), "age": ("", "")}
    assert decisions == []


# Tab2 rows 3 to 6 of the workbook: a value, a row without any value, its
# repeat, and a row with only an sd. The parser skips rows without any cell.
VALUELESS_TAB2 = [
    ["group", "mean", "sd"],
    ["all", 2.5, 0.5],
    ["all", "NA", "NA"],
    ["all", "NA", "NA"],
    ["all", "NA", 0.3],
]
# Fig1 rows 3 to 6: three points and a point without any value.
VALUELESS_FIG1 = [["time", "mean"], [0, 0], [1, 2], [2, 1], [3, "NA"]]


def valueless_study(root):
    """The twin with rows without any value in Tab2, Fig1 and a characteristic.

    Individual S2 has an age without value, individual S1 an age with only a
    count, and the group a choice without statistics.
    """
    s1, s2 = STUDY["individualset"]["individuals"]
    individuals = [
        {**s1, "characteristica": [{"measurement_type": "age", "count": 1}]},
        {
            **s2,
            "characteristica": [
                {
                    "measurement_type": "age",
                    "unit": "yr",
                    "comments": [["curator", "Age not given"]],
                }
            ],
        },
    ]
    study = {
        **STUDY,
        "individualset": {"individuals": individuals},
        "outputset": {"outputs": [{**OUTPUT, "group": "col==group"}, TIMECOURSE]},
    }
    sheets = {"Tab2": VALUELESS_TAB2, "Fig1": VALUELESS_FIG1}
    return v1_study(root, study, sheets, IMAGES)


def test_rows_without_any_value_are_dropped_and_listed(tmp_path):
    folder = valueless_study(tmp_path)
    tables, decisions = tables_of(folder)
    assert [(row["mean"], row["sd"]) for row in tables["outputs_Tab2.tsv"]] == [
        ("2.5", "0.5"),
        ("", "0.3"),
    ]
    assert [row["time"] for row in tables["timecourses_Fig1.tsv"]] == ["0", "1", "2"]
    ages = [
        (row["subjects"], row["count"])
        for row in tables["characteristica.tsv"]
        if row["measurement"] == "age"
    ]
    assert ages == [("S1", "1")]
    assert {d.kind for d in decisions} == {"valueless_row"}
    assert [d.detail for d in decisions] == [
        "characteristica.tsv: study.json individualset.individuals.1, subject S2, age, "
        "comment curator: Age not given",
        "outputs_Tab2.tsv: Example.xlsx Tab2 row 4, subject all, cmax, "
        "substance drug, tissue plasma",
        "outputs_Tab2.tsv: Example.xlsx Tab2 row 5, subject all, cmax, "
        "substance drug, tissue plasma",
        "timecourses_Fig1.tsv: Example.xlsx Fig1 row 6, label drug_plasma, "
        "subject all, concentration, substance drug, tissue plasma",
    ]
    # The place of each row, from which the Markdown report lists row ranges.
    assert decisions[1].dropped == DroppedRow(
        table="outputs_Tab2.tsv",
        file="Example.xlsx",
        sheet="Tab2",
        row=4,
        subject="all",
        measurement="cmax",
        substance="drug",
        tissue="plasma",
    )


def test_choice_rows_statements_and_unknown_measurements_are_kept(tmp_path):
    group = {
        **STUDY["groupset"]["groups"][0],
        "characteristica": [
            {"measurement_type": "sex", "choice": "M"},
            {"measurement_type": "kinetics"},
            {"measurement_type": "unknown"},
            # Its existence is the information: the group abstained.
            {"measurement_type": "abstinence"},
        ],
    }
    study = {**STUDY, "groupset": {"groups": [group]}, "outputset": {}}
    folder = v1_study(tmp_path, study, {}, IMAGES)
    tables, decisions = tables_of(folder)
    measurements = [
        row["measurement"]
        for row in tables["characteristica.tsv"]
        if row["subjects"] == "all"
    ]
    assert measurements == ["sex", "kinetics", "unknown", "abstinence"]
    assert "valueless_row" not in {d.kind for d in decisions}


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
    tables, decisions = tables_of(folder)
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
    tables, decisions = tables_of(folder)
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
    tables, _ = tables_of(folder)
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
    tables, _ = tables_of(folder)
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
    tables, decisions = tables_of(folder)
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
        tables_of(folder)
    assert error.value.code == code


def test_render_refuses_a_cell_without_a_column():
    with pytest.raises(ValueError, match="label"):
        render({"subjects.tsv": [{"name": "all", "label": "x"}]})


@pytest.mark.parametrize("workbook", [True, False])
def test_the_full_twin_with_scatters(tmp_path, valid_study, sf_vocabulary, workbook):
    folder = v1_full_example(tmp_path / "v1", workbook=workbook)
    issues = prepare(folder, vocabulary=sf_vocabulary).report.issues
    assert not [i for i in issues if i.severity == "error"]
    tables, decisions = tables_of(folder)
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
    tables, decisions = tables_of(folder)
    assert len(tables["outputs_Tab2.tsv"]) == 1
    assert [row["label"] for row in tables["timecourses_Fig1.tsv"]] == [
        "drug_plasma"
    ] * 3
    assert {d.kind for d in decisions} == {"array_output"}
    assert [d.detail for d in decisions] == [
        "1 array output in outputs_Tab2.tsv",
        "3 array outputs in timecourses_Fig1.tsv",
    ]


# A labelled array output: a series only with a time per row and one subject.
ARRAY = {
    "source": "Tab3",
    "image": "Tab3",
    "output_type": "array",
    "label": "drug_individuals",
    "individual": "col==subject",
    "interventions": ["D1"],
    "measurement_type": "concentration",
    "substance": "drug",
    "tissue": "plasma",
    "mean": "col==mean",
    "unit": "mg/l",
}


@pytest.mark.parametrize(
    ("timed", "rows", "series"),
    [
        (True, [["S1", 0, 1], ["S1", 1, 2]], True),
        (False, [["S1", 0, 1], ["S1", 1, 2]], False),
        (True, [["S1", 0, 1], ["S2", 1, 2]], False),
        (True, [["S1", 1, 1], ["S1", 1, 2]], False),
    ],
    ids=["series", "no time", "two subjects", "time twice"],
)
def test_labelled_array_outputs_are_timecourses_only_as_valid_series(
    tmp_path, timed, rows, series
):
    array = {**ARRAY, "time": "col==time", "time_unit": "h"} if timed else ARRAY
    study = {**STUDY, "outputset": {"outputs": [array]}}
    sheet = [["subject", "time", "mean"], *rows]
    folder = v1_study(tmp_path, study, {"Tab3": sheet}, (*IMAGES, "Tab3"))
    tables, decisions = tables_of(folder)
    file = "timecourses_Tab3.tsv" if series else "outputs_Tab3.tsv"
    assert [table for table in tables if table.endswith("_Tab3.tsv")] == [file]
    assert [row.get("label") for row in tables[file]] == (
        ["drug_individuals"] * 2 if series else [None] * 2
    )
    details = [f"2 array outputs in {file}"]
    if not series:
        details.append(f"2 output labels dropped in {file}")
    assert [d.detail for d in decisions] == details


def test_outputs_take_the_source_of_their_image(tmp_path):
    # Sheets Tab2A and Tab2B hold rows of the paper's Tab2; a row of sheet
    # Tab2 shows Fig1, and a row without image keeps its sheet.
    no_image = {key: value for key, value in OUTPUT.items() if key != "image"}
    outputs = [
        {**OUTPUT, "source": "Tab2A"},
        {**OUTPUT, "source": "Tab2B"},
        {**OUTPUT, "image": "Fig1"},
        no_image,
    ]
    sheets = {
        "Tab2A": [["mean", "sd"], [2.5, 0.5]],
        "Tab2B": [["mean", "sd"], [3.5, 0.5]],
        "Tab2": [["mean", "sd"], [4.5, 0.5]],
    }
    study = {**STUDY, "outputset": {"outputs": outputs}}
    folder = v1_study(tmp_path, study, sheets, IMAGES)
    tables, decisions = tables_of(folder)
    assert {
        file: [row["mean"] for row in rows]
        for file, rows in tables.items()
        if file.startswith("outputs")
    } == {
        "outputs_Tab2.tsv": ["2.5", "3.5", "4.5"],
        "outputs_Fig1.tsv": ["4.5"],
    }
    assert {row["source"] for row in tables["outputs_Fig1.tsv"]} == {"Fig1"}
    assert decisions == []


def test_labels_of_outputs_are_dropped_and_a_decision(tmp_path):
    outputs = [{**OUTPUT, "label": "cmax_all"}, {**OUTPUT, "label": "cmax_2"}]
    study = {**STUDY, "outputset": {"outputs": [*outputs, TIMECOURSE]}}
    folder = v1_study(tmp_path, study, SHEETS, IMAGES)
    tables, decisions = tables_of(folder)
    assert len(tables["outputs_Tab2.tsv"]) == 2
    assert all("label" not in row for row in tables["outputs_Tab2.tsv"])
    assert [(d.kind, d.detail) for d in decisions] == [
        ("output_label", "2 output labels dropped in outputs_Tab2.tsv")
    ]


def test_a_geometric_mean_moves_to_gmean(tmp_path):
    output = {**STUDY["outputset"]["outputs"][0], "calculation_type": "geometric mean"}
    study = {**STUDY, "outputset": {"outputs": [output]}}
    folder = v1_study(tmp_path, study, SHEETS, IMAGES)
    tables, decisions = tables_of(folder)
    [row] = tables["outputs_Tab2.tsv"]
    # Format 2 retired the calculation `geometric mean`.
    assert (row["mean"], row["gmean"], row["calculation"]) == ("", "2.5", "")
    # It also has sd: arithmetic or geometric is unclear.
    assert [d.kind for d in decisions] == ["geometric_spread"]


def test_a_retired_calculation_without_a_mean_is_left_empty(tmp_path):
    median = {key: v for key, v in OUTPUT.items() if key not in ("mean", "sd")}
    output = {**median, "median": "col==mean", "calculation_type": "geometric mean"}
    study = {**STUDY, "outputset": {"outputs": [output]}}
    folder = v1_study(tmp_path, study, SHEETS, IMAGES)
    tables, decisions = tables_of(folder)
    [row] = tables["outputs_Tab2.tsv"]
    assert (row["median"], row["gmean"], row["calculation"]) == ("2.5", "", "")
    assert decisions == []


def test_timecourse_labels_that_format_2_cannot_hold_are_renamed(tmp_path):
    timecourse = {**TIMECOURSE, "label": "drug, plasma;\tfasted"}
    study = {**STUDY, "outputset": {"outputs": [OUTPUT, timecourse]}}
    folder = v1_study(tmp_path, study, SHEETS, IMAGES)
    tables, decisions = tables_of(folder)
    labels = {row["label"] for row in tables["timecourses_Fig1.tsv"]}
    assert labels == {"drug_plasma_fasted"}
    assert [(d.kind, d.detail) for d in decisions] == [
        (
            "label_renamed",
            "timecourses_Fig1.tsv: 'drug, plasma;\\tfasted' to drug_plasma_fasted",
        )
    ]


def test_a_renamed_label_that_another_label_has_refuses_the_study(tmp_path):
    outputs = [{**TIMECOURSE, "label": label} for label in ("a,b", "a_b")]
    study = {**STUDY, "outputset": {"outputs": outputs}}
    folder = v1_study(tmp_path, study, SHEETS, IMAGES)
    with pytest.raises(NotConverted) as error:
        tables_of(folder)
    assert error.value.code == "label_name"
    assert "a_b" in error.value.message


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
    tables, decisions = tables_of(folder)
    [row] = tables["characteristica.tsv"]
    assert (row["mean"], row["gmean"], row["calculation"]) == ("", "35", "")
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
    tables, decisions = tables_of(folder)
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
    tables, decisions = tables_of(folder)
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
            {
                "y": {"source": "Fig3", "image": "Fig3"},
                "sheets": {"Fig3": SCATTER_SHEET["Fig2"]},
            },
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
        tables_of(folder)
    assert error.value.code == code
