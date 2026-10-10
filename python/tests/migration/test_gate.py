import json

import pytest
from migration_fixtures import (
    DATASET,
    IMAGES,
    SCATTER_OUTPUTS,
    SCATTER_SHEET,
    SHEETS,
    STUDY,
    Formula,
    v1_full_example,
    v1_study,
)
from PIL import Image
from vocabulary_fixtures import studyformat_vocabulary

from pkdb.importers.folder import load_folder, parse_bundle
from pkdb.migration import gate, rows
from pkdb.migration.convert import convert_study
from pkdb.migration.gate import MAX_DIFFERENCES, compare, judge
from pkdb.migration.model import NotConverted
from pkdb.migration.registry import Registry
from pkdb.preparation import prepare
from pkdb.references import ReferenceResolver

OUTPUT, TIMECOURSE = STUDY["outputset"]["outputs"]
X_OUTPUT, Y_OUTPUT = SCATTER_OUTPUTS


def converted(tmp_path, v1):
    target = tmp_path / "v2" / v1.parent.name / v1.name
    convert_study(
        v1,
        target,
        registry=Registry(),
        approver=None,
        resolver=ReferenceResolver(offline=True),
        vocabulary=studyformat_vocabulary(),
    )
    return target


def with_outputs(*outputs, **changes):
    return {**STUDY, "outputset": {"outputs": list(outputs)}, **changes}


def rewrite(table, column, value, row=0):
    """Set one cell of a converted table."""
    header, *rows = table.read_text().splitlines()
    names = header.split("\t")
    cells = rows[row].split("\t")
    cells[names.index(column)] = value
    rows[row] = "\t".join(cells)
    table.write_text("\n".join([header, *rows]) + "\n")


def test_an_exact_conversion_is_identical(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert (result.study, result.outcome, result.differences) == (
        "caffeine/Example",
        "identical",
        [],
    )
    assert result.changes == []


def test_a_conversion_from_hidden_tables_is_identical(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1", workbook=False)
    assert judge(v1, converted(tmp_path, v1), sf_vocabulary).outcome == "identical"


def test_the_gate_changes_neither_folder(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)

    def files():
        return {p: p.read_bytes() for p in sorted(tmp_path.rglob("*")) if p.is_file()}

    before = files()
    judge(v1, v2, sf_vocabulary)
    assert files() == before


def test_a_group_with_count_one_is_an_intended_change(tmp_path, sf_vocabulary):
    # A single subject has no sd in format 2, so the output reports a mean only.
    output = {key: value for key, value in OUTPUT.items() if key != "sd"}
    group = {**STUDY["groupset"]["groups"][0], "count": 1}
    study = with_outputs(
        output, TIMECOURSE, groupset={"groups": [group]}, individualset={}
    )
    v1 = v1_study(tmp_path / "v1", study, SHEETS, IMAGES)
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert result.outcome == "intended", result.differences
    assert [(c.kind, c.count, c.examples) for c in result.changes] == [
        ("group_count_1", 1, ["all"])
    ]


def test_a_changed_value_is_a_mismatch(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)
    table = v2 / "outputs_Tab2.tsv"
    table.write_text(table.read_text().replace("\t0.5\t", "\t0.6\t"))
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "mismatch"
    [difference] = result.differences
    assert difference.path.endswith(".sd") and (difference.a, difference.b) == (
        "0.5",
        "0.6",
    )
    assert difference.path.startswith("measurements[Example_Tab2.png output all D1")


def test_a_difference_within_the_tolerance_is_identical(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)
    table = v2 / "outputs_Tab2.tsv"
    table.write_text(table.read_text().replace("\t0.5\t", "\t0.5000000000001\t"))
    assert judge(v1, v2, sf_vocabulary).outcome == "identical"


def test_a_difference_beyond_the_tolerance_is_a_mismatch(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)
    table = v2 / "outputs_Tab2.tsv"
    table.write_text(table.read_text().replace("\t0.5\t", "\t0.500000001\t"))
    assert judge(v1, v2, sf_vocabulary).outcome == "mismatch"


def test_a_missing_record_is_a_mismatch(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)
    table = v2 / "characteristica.tsv"
    lines = table.read_text().splitlines()
    table.write_text("\n".join(line for line in lines if "\tS2\t" not in line) + "\n")
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "mismatch"
    [difference] = result.differences
    assert difference.path == "characteristica[Example_TabA.png S2 age yr]"
    assert (difference.a, difference.b) == ("mean 40, count 1", "missing")


def test_a_changed_key_is_a_mismatch(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)
    rewrite(v2 / "timecourses_Fig1.tsv", "time", "0.5")
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "mismatch"
    paths = [d.path for d in result.differences]
    assert any(" time 0 h " in path for path in paths)
    assert any(" time 0.5 h " in path for path in paths)
    assert "timecourses[drug_plasma]" in paths


def test_a_changed_subject_is_a_mismatch(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)
    subjects = v2 / "subjects.tsv"
    subjects.write_text(subjects.read_text().replace("\tall\t\t2\t", "\tall\t\t3\t"))
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "mismatch"
    assert [(d.a, d.b) for d in result.differences if d.path == "subjects[all]"] == [
        ("group, count 2", "group, count 3")
    ]


def test_a_changed_scatter_pairing_is_a_mismatch(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    a = prepare(v1, vocabulary=sf_vocabulary).study
    b = prepare(converted(tmp_path, v1), vocabulary=sf_vocabulary).study
    # The same records, with x of S1 paired to y of S2 and x of S2 to y of S1.
    [subset] = b.scatters[0].subsets
    (x1, y1), (x2, y2) = subset.points
    subset.points = [[x1, y2], [x2, y1]]
    changes, differences = compare(a, b)
    assert changes == []
    assert [(d.path, d.a, d.b) for d in differences] == [
        ("scatters[age_vs_cmax]", "scatter of 2 points", "scatter of 2 points")
    ]


def test_an_unformatted_converted_study_is_a_mismatch(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)
    (v2 / "subjects.tsv").write_text((v2 / "subjects.tsv").read_text() + "\n")
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "mismatch"
    assert result.differences[0].path == "format"


def test_an_invalid_converted_study_is_a_mismatch(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)
    rewrite(v2 / "outputs_Tab2.tsv", "measurement", "unknown")
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "mismatch"
    # The curator reads what to fix: the code, the cell and the message.
    assert result.issues == ["unknown_measurement"]
    assert [(d.path, d.a, d.b) for d in result.differences] == [
        (
            "validation outputs_Tab2.tsv:E2 unknown_measurement [subjects=all "
            "interventions=D1 measurement=unknown substance=drug tissue=plasma]",
            "valid",
            "Unknown measurement: unknown",
        )
    ]


def test_a_missing_value_names_the_row_of_the_converted_study(tmp_path, sf_vocabulary):
    # A spread without a value stays for the curator, unlike a row without any value.
    group = STUDY["groupset"]["groups"][0]
    sd_only = {"measurement_type": "age", "sd": 2, "unit": "yr", "image": "Tab1"}
    groups = [{**group, "characteristica": [*group["characteristica"], sd_only]}]
    study = {**STUDY, "groupset": {"groups": groups}}
    v1 = v1_study(tmp_path / "v1", study, SHEETS, IMAGES)
    v2 = converted(tmp_path, v1)
    lines = (v2 / "characteristica.tsv").read_text().splitlines()
    [row] = [n for n, line in enumerate(lines, 1) if "\tall\tage\t" in line]
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "mismatch"
    assert [d.path for d in result.differences] == [
        f"validation characteristica.tsv:{row} missing_value [subjects=all measurement=age]"
    ]


def test_a_characteristic_without_time_is_an_intended_change(tmp_path, sf_vocabulary):
    # Format 1 characteristica have no time; format 2 needs one for concentration.
    group = STUDY["groupset"]["groups"][0]
    concentration = {
        "measurement_type": "concentration",
        "substance": "drug",
        "tissue": "plasma",
        "mean": 5,
        "unit": "mg/l",
        "image": "Tab1",
    }
    groups = [{**group, "characteristica": [*group["characteristica"], concentration]}]
    study = {**STUDY, "groupset": {"groups": groups}}
    v1 = v1_study(tmp_path / "v1", study, SHEETS, IMAGES)
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert result.outcome == "intended", result.differences
    assert [(c.kind, c.examples) for c in result.changes] == [
        (
            "time_not_reported",
            [
                "characteristica[Example_Tab1.png all concentration sample mean "
                "drug plasma mg/l]"
            ],
        )
    ]


def test_rows_without_any_value_are_an_intended_change(tmp_path, sf_vocabulary):
    individuals = [
        STUDY["individualset"]["individuals"][0],
        {
            **STUDY["individualset"]["individuals"][1],
            "characteristica": [{"measurement_type": "age", "unit": "yr"}],
        },
    ]
    study = {
        **with_outputs({**OUTPUT, "group": "col==group"}, TIMECOURSE),
        "individualset": {"individuals": individuals},
    }
    tab2 = [["group", "mean", "sd"], ["all", 2.5, 0.5], *[["all", "NA", "NA"]] * 2]
    sheets = {"Tab2": tab2, "Fig1": [*SHEETS["Fig1"], [3, "NA"]]}
    v1 = v1_study(tmp_path / "v1", study, sheets, IMAGES)
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert result.outcome == "intended", result.differences
    assert [(c.kind, c.count) for c in result.changes] == [("valueless_row", 4)]


def test_a_timecourse_without_any_value_is_an_intended_change(tmp_path, sf_vocabulary):
    sheets = {**SHEETS, "Fig1": [["time", "mean"], [0, "NA"], [1, "NA"]]}
    v1 = v1_study(tmp_path / "v1", STUDY, sheets, IMAGES)
    v2 = converted(tmp_path, v1)
    assert not (v2 / "timecourses_Fig1.tsv").exists()
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "intended", result.differences
    assert [(c.kind, c.count) for c in result.changes] == [("valueless_row", 2)]


@pytest.mark.parametrize(
    ("repeat", "outcome", "found"),
    [
        (["all", 2.5, 0.5], "mismatch", ["duplicate_row"]),
        (["all", "NA", "NA"], "intended", ["valueless_row"]),
    ],
    ids=["repeat with data", "empty row"],
)
def test_only_an_empty_row_of_a_repeated_key_is_dropped(
    tmp_path, sf_vocabulary, repeat, outcome, found
):
    study = with_outputs({**OUTPUT, "group": "col==group"}, TIMECOURSE)
    tab2 = [["group", "mean", "sd"], ["all", 2.5, 0.5], repeat]
    v1 = v1_study(tmp_path / "v1", study, {**SHEETS, "Tab2": tab2}, IMAGES)
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert result.outcome == outcome
    assert (result.issues or [c.kind for c in result.changes]) == found


@pytest.mark.parametrize(
    "row",
    [
        {"measurement_type": "age", "count": 2, "unit": "yr"},
        {"measurement_type": "abstinence"},
    ],
    ids=["only a count", "a statement"],
)
def test_rows_that_carry_information_without_value_stay_a_mismatch(
    tmp_path, sf_vocabulary, row
):
    # A count, or the existence of an abstinence row, is information to curate.
    group = STUDY["groupset"]["groups"][0]
    kept = {**row, "image": "Tab1"}
    groups = [{**group, "characteristica": [*group["characteristica"], kept]}]
    v1 = v1_study(
        tmp_path / "v1", {**STUDY, "groupset": {"groups": groups}}, SHEETS, IMAGES
    )
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert (result.outcome, result.issues) == ("mismatch", ["missing_value"])


def test_labelled_array_outputs_with_a_dropped_row_are_an_intended_series(
    tmp_path, sf_vocabulary
):
    # Without the empty row, time 1 appears once and the rows form a series.
    array = {
        **TIMECOURSE,
        "source": "Tab3",
        "image": "Tab3",
        "output_type": "array",
        "label": "drug_individuals",
        "group": None,
        "individual": "col==subject",
    }
    array = {key: value for key, value in array.items() if value is not None}
    study = with_outputs(OUTPUT, TIMECOURSE, array)
    tab3 = [["subject", "time", "mean"], ["S1", 0, 1], ["S1", 1, 2], ["S1", 1, "NA"]]
    v1 = v1_study(tmp_path / "v1", study, {**SHEETS, "Tab3": tab3}, (*IMAGES, "Tab3"))
    v2 = converted(tmp_path, v1)
    assert (v2 / "timecourses_Tab3.tsv").exists()
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "intended", result.differences
    assert [(c.kind, c.count) for c in result.changes] == [
        ("array_output", 2),
        ("valueless_row", 1),
    ]


def test_a_dropped_record_with_data_is_a_mismatch(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)
    [cmax] = [
        record
        for record in parse_bundle(load_folder(v1)).measurements
        if record.measurement_type == "cmax" and not record.label
    ]
    a = prepare(v1, vocabulary=sf_vocabulary).study
    b = prepare(v2, vocabulary=sf_vocabulary).study
    changes, differences = compare(a, b, dropped={cmax.key: cmax})
    assert "valueless_row" not in [change.kind for change in changes]
    assert (differences[0].a, differences[0].b) == (
        "mean 2.5, sd 0.5",
        "dropped record with data",
    )
    assert differences[0].path.startswith("measurements[Example_Tab2.png output")


def test_the_gate_refuses_a_converter_rule_that_drops_data(
    tmp_path, sf_vocabulary, monkeypatch
):
    # A wrong rule shared by the converter and the gate must still fail the gate.
    def outputs(study, vocabulary):
        return frozenset(
            record.key
            for record in study.measurements
            if record.output_type == "output" and not record.label
        )

    monkeypatch.setattr(rows, "valueless", outputs)
    monkeypatch.setattr(gate, "valueless", outputs)
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)
    assert not (v2 / "outputs_Tab2.tsv").exists()
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "mismatch"
    assert [d.b for d in result.differences] == ["dropped record with data"]


def test_whitespace_of_text_cells_is_an_intended_change(tmp_path, sf_vocabulary):
    # The converter writes text cells on one line; a blank cell is no value.
    output = {**OUTPUT, "unit": "col==unit", "method": "col==method"}
    sheets = {
        **SHEETS,
        "Tab2": [["mean", "sd", "unit", "method"], [2.5, 0.5, "mg  / l", " "]],
    }
    v1 = v1_study(tmp_path / "v1", with_outputs(output, TIMECOURSE), sheets, IMAGES)
    v2 = converted(tmp_path, v1)
    assert "\tmg / l\t" in (v2 / "outputs_Tab2.tsv").read_text()
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "intended", result.differences
    assert [(c.kind, c.count) for c in result.changes] == [("whitespace", 1)]


def test_a_v1_study_that_cannot_be_prepared_is_invalid_v1(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)
    study = json.loads((v1 / "study.json").read_text())
    study["outputset"]["outputs"][0]["group"] = "nobody"
    (v1 / "study.json").write_text(json.dumps(study))
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "invalid_v1"
    assert result.issues


def test_an_error_bar_formula_is_an_intended_change(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)
    table = v2 / "outputs_Tab2.tsv"
    header, row = table.read_text().splitlines()
    names, cells = header.split("\t"), row.split("\t")
    cells[names.index("sd")] = ""
    cells[names.index("error_bar")] = "3"
    cells[names.index("error_type")] = "sd"
    table.write_text("\t".join(names) + "\n" + "\t".join(cells) + "\n")
    result = judge(v1, v2, sf_vocabulary)
    assert (result.outcome, [c.kind for c in result.changes]) == (
        "intended",
        ["error_bar"],
    )


def test_a_converted_abs_formula_is_an_intended_change(tmp_path, sf_vocabulary):
    sheets = {
        **SHEETS,
        "Tab2": [["mean", "sd", "upper"], [2.5, Formula("=ABS(C3-A3)", 0.75), 3.25]],
    }
    v1 = v1_study(tmp_path / "v1", STUDY, sheets, IMAGES)
    v2 = converted(tmp_path, v1)
    assert "\t3.25\tsd\t" in (v2 / "outputs_Tab2.tsv").read_text()
    result = judge(v1, v2, sf_vocabulary)
    assert (result.outcome, [c.kind for c in result.changes]) == (
        "intended",
        ["error_bar"],
    )


def test_an_error_bar_that_does_not_give_the_spread_is_a_mismatch(
    tmp_path, sf_vocabulary
):
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)
    rewrite(v2 / "outputs_Tab2.tsv", "sd", "")
    rewrite(v2 / "outputs_Tab2.tsv", "error_bar", "3.1")
    rewrite(v2 / "outputs_Tab2.tsv", "error_type", "sd")
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "mismatch"
    assert result.changes == []
    assert {d.path.rpartition(".")[2] for d in result.differences} == {
        "sd",
        "error_bar",
        "error_type",
    }


def test_array_outputs_are_an_intended_change(tmp_path, sf_vocabulary):
    study = with_outputs(
        {**OUTPUT, "output_type": "array"}, {**TIMECOURSE, "output_type": "array"}
    )
    v1 = v1_study(tmp_path / "v1", study, SHEETS, IMAGES)
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert result.outcome == "intended", result.differences
    assert [(c.kind, c.count) for c in result.changes] == [("array_output", 4)]


def test_labelled_array_outputs_that_form_no_series_are_intended_outputs(
    tmp_path, sf_vocabulary
):
    # Correlation data: cmax of each individual, without time, under one label.
    array = {
        **OUTPUT,
        "source": "Tab3",
        "image": "Tab3",
        "output_type": "array",
        "label": "cmax_individuals",
        "group": None,
        "individual": "col==subject",
        "sd": None,
    }
    array = {key: value for key, value in array.items() if value is not None}
    study = with_outputs(OUTPUT, TIMECOURSE, array)
    sheets = {**SHEETS, "Tab3": [["subject", "mean"], ["S1", 2], ["S2", 3]]}
    v1 = v1_study(tmp_path / "v1", study, sheets, (*IMAGES, "Tab3"))
    v2 = converted(tmp_path, v1)
    assert not (v2 / "timecourses_Tab3.tsv").exists()
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "intended", result.differences
    assert [(c.kind, c.count) for c in result.changes] == [
        ("array_output", 2),
        ("output_label", 2),
    ]


def test_array_points_of_a_scatter_are_an_intended_change(tmp_path, sf_vocabulary):
    study = with_outputs(
        OUTPUT,
        TIMECOURSE,
        {**X_OUTPUT, "output_type": "array"},
        {**Y_OUTPUT, "output_type": "array"},
        dataset=DATASET,
    )
    sheets = {**SHEETS, **SCATTER_SHEET}
    v1 = v1_study(tmp_path / "v1", study, sheets, (*IMAGES, "Fig2"))
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert result.outcome == "intended", result.differences
    assert [(c.kind, c.count) for c in result.changes] == [("array_output", 4)]


def test_scatter_labels_are_an_intended_change(tmp_path, sf_vocabulary):
    subset = {"name": "age_vs_cmax", "dimensions": ["x_age", "y_cmax"]}
    dataset = {
        "data": [
            {**DATASET["data"][0], "subsets": [{**subset, "shared": ["individual"]}]}
        ]
    }
    study = with_outputs(
        OUTPUT,
        TIMECOURSE,
        {**X_OUTPUT, "label": "x_age"},
        {**Y_OUTPUT, "label": "y_cmax"},
        dataset=dataset,
    )
    sheets = {**SHEETS, **SCATTER_SHEET}
    v1 = v1_study(tmp_path / "v1", study, sheets, (*IMAGES, "Fig2"))
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert result.outcome == "intended", result.differences
    assert [(c.kind, c.examples) for c in result.changes] == [
        ("scatter_label", ["x_age to age_vs_cmax_x", "y_cmax to age_vs_cmax_y"])
    ]


def test_a_jpg_image_is_an_intended_change(tmp_path, sf_vocabulary):
    study = with_outputs({**OUTPUT, "image": "Example_Tab2.jpg"}, TIMECOURSE)
    v1 = v1_study(tmp_path / "v1", study, SHEETS, ("Tab1", "TabA", "Fig1"))
    Image.new("RGB", (4, 3), "red").save(v1 / "Example_Tab2.jpg")
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert result.outcome == "intended", result.differences
    assert [(c.kind, c.examples) for c in result.changes] == [
        ("image_converted", ["Example_Tab2.jpg to Example_Tab2.png"])
    ]


def test_a_jpg_with_a_png_twin_never_reaches_the_gate(tmp_path):
    # The folder holds Example_Tab2.png besides the JPG that the output names:
    # the PNG would silently replace the JPG, so the study is not converted.
    study = with_outputs({**OUTPUT, "image": "Example_Tab2.jpg"}, TIMECOURSE)
    v1 = v1_study(tmp_path / "v1", study, SHEETS, IMAGES)
    Image.new("RGB", (4, 3), "red").save(v1 / "Example_Tab2.jpg")
    with pytest.raises(NotConverted) as error:
        converted(tmp_path, v1)
    assert error.value.code == "image_conflict"


@pytest.mark.parametrize("spread", [True, False], ids=["with sd", "mean only"])
def test_a_geometric_mean_moved_to_gmean_is_an_intended_change(
    tmp_path, sf_vocabulary, spread
):
    output = {**OUTPUT, "calculation_type": "geometric mean"}
    if not spread:
        del output["sd"]
    v1 = v1_study(tmp_path / "v1", with_outputs(output, TIMECOURSE), SHEETS, IMAGES)
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert result.outcome == "intended", result.differences
    assert [(c.kind, c.count) for c in result.changes] == [("gmean", 1)]


def test_a_geometric_mean_of_a_characteristic_is_an_intended_change(
    tmp_path, sf_vocabulary
):
    age = {"measurement_type": "age", "mean": 35, "unit": "yr", "image": "Tab1"}
    group = STUDY["groupset"]["groups"][0]
    characteristica = [
        *group["characteristica"],
        {**age, "calculation_type": "geometric mean"},
    ]
    study = with_outputs(
        OUTPUT,
        TIMECOURSE,
        groupset={"groups": [{**group, "characteristica": characteristica}]},
    )
    v1 = v1_study(tmp_path / "v1", study, SHEETS, IMAGES)
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert result.outcome == "intended", result.differences
    assert [(c.kind, c.count) for c in result.changes] == [("gmean", 1)]


def without_image(entry):
    return {key: value for key, value in entry.items() if key != "image"}


def test_images_that_the_conversion_adds_are_an_intended_change(
    tmp_path, sf_vocabulary
):
    # Characteristica take the image of their subject, outputs that of their sheet.
    group = STUDY["groupset"]["groups"][0]
    characteristica = [without_image(c) for c in group["characteristica"]]
    outputs = [OUTPUT, TIMECOURSE, X_OUTPUT, Y_OUTPUT]
    study = with_outputs(
        *map(without_image, outputs),
        groupset={"groups": [{**group, "characteristica": characteristica}]},
        dataset=DATASET,
    )
    sheets = {**SHEETS, **SCATTER_SHEET}
    v1 = v1_study(tmp_path / "v1", study, sheets, (*IMAGES, "Fig2"))
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert result.outcome == "intended", result.differences
    [change] = result.changes
    assert (change.kind, change.count) == ("image_added", 3 + 1 + 3 + 4)
    assert change.examples[0] == (
        "characteristica[Example_Tab1.png all species sample mean Homo sapiens]"
    )


def test_an_output_takes_the_figure_of_its_image(tmp_path, sf_vocabulary):
    # The rows of sheet Tab2 show Fig1: the converted row is a row of Fig1.
    study = with_outputs({**OUTPUT, "image": "Fig1"}, TIMECOURSE)
    v1 = v1_study(tmp_path / "v1", study, SHEETS, IMAGES)
    v2 = converted(tmp_path, v1)
    assert (v2 / "outputs_Fig1.tsv").exists()
    assert judge(v1, v2, sf_vocabulary).outcome == "identical"


def test_an_image_that_the_conversion_drops_is_a_mismatch(tmp_path, sf_vocabulary):
    # The image of the characteristic is no file of the folder.
    group = STUDY["groupset"]["groups"][0]
    sex = {"measurement_type": "sex", "choice": "M", "image": "Tab9"}
    characteristica = [*group["characteristica"][:2], sex]
    study = {
        **STUDY,
        "groupset": {"groups": [{**group, "characteristica": characteristica}]},
    }
    v1 = v1_study(tmp_path / "v1", study, SHEETS, IMAGES)
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert result.outcome == "mismatch"
    assert result.changes == []
    assert [(d.path, d.a, d.b) for d in result.differences] == [
        (
            "characteristica[Example_Tab9.png all sex sample mean M]",
            "count 2",
            "missing",
        ),
        ("characteristica[all sex sample mean M]", "missing", "count 2"),
    ]


def test_a_retired_calculation_is_an_intended_change(tmp_path, sf_vocabulary):
    # A geometric mean reported as a median: only the calculation is retired.
    median = {key: v for key, v in OUTPUT.items() if key not in ("mean", "sd")}
    output = {**median, "median": "col==mean", "calculation_type": "geometric mean"}
    v1 = v1_study(tmp_path / "v1", with_outputs(output, TIMECOURSE), SHEETS, IMAGES)
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert result.outcome == "intended", result.differences
    assert [(c.kind, c.count) for c in result.changes] == [("retired_calculation", 1)]


def test_a_renamed_timecourse_label_is_an_intended_change(tmp_path, sf_vocabulary):
    study = with_outputs(OUTPUT, {**TIMECOURSE, "label": "drug, plasma"})
    v1 = v1_study(tmp_path / "v1", study, SHEETS, IMAGES)
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert result.outcome == "intended", result.differences
    assert [(c.kind, c.examples) for c in result.changes] == [
        ("label_renamed", ["'drug, plasma' to drug_plasma"])
    ]


def test_curator_rows_of_a_sheet_without_image_are_identical(tmp_path, sf_vocabulary):
    group = {
        "source": "TabGroups",
        "name": "col==name",
        "count": "col==count",
        "characteristica": [
            {"measurement_type": "species", "choice": "Homo sapiens"},
            {"measurement_type": "healthy", "choice": "Y"},
            {"measurement_type": "sex", "choice": "M"},
        ],
    }
    study = {**STUDY, "groupset": {"groups": [group]}}
    sheets = {**SHEETS, "TabGroups": [["name", "count"], ["all", 2]]}
    v1 = v1_study(tmp_path / "v1", study, sheets, ("TabA", "Tab2", "Fig1"))
    v2 = converted(tmp_path, v1)
    assert "\tText\t" in (v2 / "characteristica.tsv").read_text()
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "identical", result.differences


def test_an_error_bar_below_zero_keeps_the_spread(tmp_path, sf_vocabulary):
    sheets = {
        **SHEETS,
        "Tab2": [["mean", "sd", "lower"], [2.5, Formula("=ABS(C3-A3)", 2.75), -0.25]],
    }
    v1 = v1_study(tmp_path / "v1", STUDY, sheets, IMAGES)
    v2 = converted(tmp_path, v1)
    assert "\t2.75\t" in (v2 / "outputs_Tab2.tsv").read_text()
    assert judge(v1, v2, sf_vocabulary).outcome == "identical"


def test_a_dropped_output_label_is_an_intended_change(tmp_path, sf_vocabulary):
    study = with_outputs({**OUTPUT, "label": "cmax_all"}, TIMECOURSE)
    v1 = v1_study(tmp_path / "v1", study, SHEETS, IMAGES)
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert result.outcome == "intended", result.differences
    assert [(c.kind, c.count) for c in result.changes] == [("output_label", 1)]


def test_differences_are_listed_up_to_the_maximum(tmp_path, sf_vocabulary):
    rows = [[float(mean), 0.5] for mean in range(1, 61)]
    v1 = v1_study(
        tmp_path / "v1", STUDY, {**SHEETS, "Tab2": [["mean", "sd"], *rows]}, IMAGES
    )
    v2 = converted(tmp_path, v1)
    table = v2 / "outputs_Tab2.tsv"
    table.write_text(table.read_text().replace("\t0.5\t", "\t0.6\t"))
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "mismatch"
    assert len(result.differences) == MAX_DIFFERENCES


def commented(record, *comments):
    return {**record, "comments": [["curator", text] for text in comments]}


def test_a_comment_with_a_line_break_is_identical(tmp_path, sf_vocabulary):
    output = {**commented(OUTPUT, "From\nTab2"), "descriptions": ["Fasted.\tMen."]}
    group = commented(STUDY["groupset"]["groups"][0], "All\nsubjects")
    x = commented(X_OUTPUT, "Age at\nscreening")
    study = with_outputs(
        output,
        TIMECOURSE,
        x,
        commented(Y_OUTPUT, "Cmax"),
        groupset={"groups": [group]},
        dataset=DATASET,
    )
    sheets = {**SHEETS, **SCATTER_SHEET}
    v1 = v1_study(tmp_path / "v1", study, sheets, (*IMAGES, "Fig2"))
    v2 = converted(tmp_path, v1)
    assert (
        "\tFasted. Men. / curator: From Tab2\n" in (v2 / "outputs_Tab2.tsv").read_text()
    )
    scatters = (v2 / "scatters_Fig2.tsv").read_text()
    assert "\tcurator: Age at screening / curator: Cmax\n" in scatters
    result = judge(v1, v2, sf_vocabulary)
    assert (result.outcome, result.differences) == ("identical", [])


@pytest.mark.parametrize(
    ("table", "path"),
    [
        ("outputs_Tab2.tsv", "measurements[Example_Tab2.png output all D1"),
        ("subjects.tsv", "subjects[all]"),
        ("scatters_Fig2.tsv", "measurements[Example_Fig2.png output age_vs_cmax_x"),
    ],
)
def test_a_dropped_comment_is_a_mismatch(tmp_path, sf_vocabulary, table, path):
    study = with_outputs(
        commented(OUTPUT, "Check"),
        TIMECOURSE,
        commented(X_OUTPUT, "Check"),
        Y_OUTPUT,
        groupset={"groups": [commented(STUDY["groupset"]["groups"][0], "Check")]},
        dataset=DATASET,
    )
    sheets = {**SHEETS, **SCATTER_SHEET}
    v1 = v1_study(tmp_path / "v1", study, sheets, (*IMAGES, "Fig2"))
    v2 = converted(tmp_path, v1)
    rewrite(v2 / table, "comment", "")
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "mismatch"
    differences = [(d.a, d.b) for d in result.differences if d.path.startswith(path)]
    assert differences and set(differences) == {("curator: Check", "no comment")}
    assert all(d.path.endswith(".comment") for d in result.differences)
