import pytest

from pkdb.studyformat import format_folder, validate_folder
from pkdb.studyformat.issues import CANDIDATES, FIX, VOCABULARY, make_issue
from pkdb.studyformat.load import load_study
from pkdb.studyformat.terms import check_terms, vocabulary_terms

CMAX = {
    "subjects": "all",
    "interventions": "D1",
    "measurement": "cmax",
    "substance": "drug",
    "tissue": "plasma",
    "mean": "2",
    "unit": "mg/l",
}


@pytest.fixture
def run(make_study, valid_files, tsv, sf_vocabulary):
    def check(kind=None, *rows, file=None):
        files = dict(valid_files)
        if kind is not None:
            files[file or f"{kind}.tsv"] = tsv(kind, *rows)
        study = load_study(make_study(files))
        return {
            (issue.code, issue.source.header if issue.source else None)
            for issue in check_terms(study, sf_vocabulary)
        }

    return check


def test_valid_study_passes(run):
    assert run() == set()


def test_calculation_terms(sf_vocabulary):
    terms = vocabulary_terms(sf_vocabulary)["calculation_types"]
    assert "unspecified summary" in terms and "geometric mean" not in terms


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"measurement": "cmaxx"}, {("unknown_measurement", "measurement")}),
        ({"substance": "drugg"}, {("unknown_substance", "substance")}),
        ({"tissue": "blood"}, {("unknown_tissue", "tissue")}),
        ({"method": "LCMS"}, {("unknown_method", "method")}),
        ({"calculation": "median"}, {("unknown_calculation", "calculation")}),
        ({"calculation": "geometric mean"}, {("retired_calculation", "calculation")}),
        ({"calculation": "unspecified summary"}, set()),
        ({"mean": "-1"}, {("negative_value", "mean")}),
        ({"measurement": "change", "mean": "-1"}, set()),
        ({"unit": ""}, {("missing_unit", "unit")}),
        ({"measurement": "old_measure"}, {("deprecated_measurement", "measurement")}),
        ({"measurement": "concentration"}, {("missing_time", "time")}),
        ({"measurement": "concentration", "time": "NR", "time_unit": "NR"}, set()),
    ],
)
def test_output_terms(run, change, expected):
    assert run("outputs", {**CMAX, **change}, file="outputs_Tab2.tsv") == expected


def test_unknown_term_candidates(make_study, valid_files, tsv, sf_vocabulary):
    files = {
        **valid_files,
        "outputs_Tab2.tsv": tsv("outputs", {**CMAX, "measurement": "cmaxx"}),
    }
    issue = check_terms(load_study(make_study(files)), sf_vocabulary)[0]
    assert issue.suggestions[0].candidates == ["cmax", "tmax"]


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"measurement": "sex", "choice": "X"}, {("invalid_choice", "choice")}),
        ({"measurement": "sex"}, {("missing_choice", "choice")}),
        (
            {"measurement": "age", "choice": "old", "unit": "yr"},
            {("invalid_choice", "choice")},
        ),
        ({"measurement": "healthy", "choice": "N"}, set()),
    ],
)
def test_choices(run, row, expected):
    assert (
        run("characteristica", {"source": "Tab1", "subjects": "all", **row}) == expected
    )


def test_interventions(run):
    dose = {
        "name": "D1",
        "measurement": "dosing",
        "mean": "100",
        "unit": "mg",
        "route": "iv",
    }
    assert run("interventions", dose) == {
        ("unknown_route", "route"),
        ("missing_dosing_field", "substance"),
        ("missing_dosing_field", "form"),
        ("missing_dosing_field", "application"),
        ("missing_dosing_field", "time"),
        ("missing_dosing_field", "time_unit"),
    }


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"measurement": "age", "unit": "yr"}, {("missing_value", None)}),
        ({"measurement": "age", "median": "30", "unit": "yr"}, set()),
        ({"measurement": "age", "max": "30", "unit": "yr"}, set()),
        ({"measurement": "age", "mean": "2,5", "unit": "yr"}, set()),
        ({"measurement": "kinetics"}, set()),
        ({"measurement": "fasting"}, {("missing_choice", "choice")}),
        ({"measurement": "agee"}, {("unknown_measurement", "measurement")}),
    ],
)
def test_values_follow_the_measurement(run, row, expected):
    row = {"source": "Tab1", "subjects": "all", **row}
    assert run("characteristica", row) == expected


DOSE = {
    "name": "D1",
    "measurement": "dosing",
    "substance": "drug",
    "route": "oral",
    "form": "tablet",
    "application": "single dose",
    "time": "0",
    "time_unit": "h",
    "mean": "100",
    "unit": "mg",
}


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        (
            {"name": "Q1", "measurement": "qualitative dosing", "substance": "drug"},
            set(),
        ),
        ({"name": "F1", "measurement": "fasting", "choice": "Y"}, set()),
        ({**DOSE, "name": "D2", "mean": ""}, {("missing_value", "mean")}),
        (
            {**DOSE, "name": "D2", "mean": "", "median": "100"},
            {("missing_value", "mean")},
        ),
        ({**DOSE, "name": "D2", "mean": "2,5"}, set()),
    ],
)
def test_intervention_values(run, row, expected):
    assert run("interventions", DOSE, row) == expected


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"substance": ""}, {("missing_dosing_field", "substance")}),
        ({"route": ""}, {("missing_dosing_field", "route")}),
        ({"form": ""}, {("missing_dosing_field", "form")}),
        ({"application": ""}, {("missing_dosing_field", "application")}),
        ({"time": ""}, {("missing_dosing_field", "time")}),
        ({"time_unit": ""}, {("missing_dosing_field", "time_unit")}),
        ({"time": "NR", "time_unit": "NR"}, set()),
        # A dose without unit is reported once.
        ({"unit": ""}, {("missing_unit", "unit")}),
        (
            {"mean": "", "unit": ""},
            {("missing_value", "mean"), ("missing_dosing_field", "unit")},
        ),
        ({"application": "multiple dose"}, set()),
        ({"application": "constant infusion"}, set()),
        (
            {"application": "variable infusion"},
            {("invalid_application", "application")},
        ),
        ({"application": "single doze"}, {("unknown_application", "application")}),
        ({"form": "pill"}, {("unknown_form", "form")}),
    ],
)
def test_dosing_rules(run, row, expected):
    assert run("interventions", {**DOSE, **row}) == expected


@pytest.mark.parametrize(
    ("column", "value", "code", "candidate"),
    [
        ("form", "tablets", "unknown_form", "tablet"),
        ("application", "single doses", "unknown_application", "single dose"),
    ],
)
def test_unknown_form_and_application(
    make_study, valid_files, tsv, sf_vocabulary, column, value, code, candidate
):
    files = {
        **valid_files,
        "interventions.tsv": tsv("interventions", {**DOSE, column: value}),
    }
    [issue] = check_terms(load_study(make_study(files)), sf_vocabulary)
    assert (issue.code, issue.severity, issue.category) == (code, "error", "vocabulary")
    assert issue.source is not None and issue.source.header == column
    assert candidate in issue.suggestions[0].candidates


def test_medication_rules(run):
    medication = {"name": "M1", "measurement": "medication", "choice": "Y"}
    assert run("interventions", DOSE, medication) == {
        ("missing_dosing_field", "substance"),
        ("missing_dosing_field", "route"),
        ("missing_dosing_field", "unit"),
        ("missing_value", "mean"),
    }


def test_invalid_application_is_a_vocabulary_error(
    make_study, valid_files, tsv, sf_vocabulary
):
    row = {**DOSE, "application": "variable infusion"}
    files = {**valid_files, "interventions.tsv": tsv("interventions", row)}
    [issue] = check_terms(load_study(make_study(files)), sf_vocabulary)
    assert (issue.code, issue.severity, issue.category) == (
        "invalid_application",
        "error",
        "vocabulary",
    )


@pytest.mark.parametrize(
    ("kind", "row", "expected"),
    [
        ("outputs", {**CMAX, "unit": "h"}, {("unit_dimension", "unit")}),
        ("outputs", {**CMAX, "unit": "µg/ml"}, set()),
        ("outputs", {**CMAX, "unit": "mmol/l"}, set()),
        (
            "outputs",
            {**CMAX, "substance": "", "unit": "mmol/l"},
            {("unit_dimension", "unit")},
        ),
        ("outputs", {**CMAX, "unit": "foo"}, set()),
        (
            "outputs",
            {**CMAX, "measurement": "change", "unit": "kg"},
            {("unit_dimension", "unit")},
        ),
        ("interventions", {**DOSE, "unit": "mmol"}, set()),
        ("interventions", {**DOSE, "unit": "ml"}, {("unit_dimension", "unit")}),
        (
            "interventions",
            {**DOSE, "measurement": "qualitative dosing", "unit": "h"},
            set(),
        ),
        (
            "characteristica",
            {
                "source": "Tab1",
                "subjects": "all",
                "measurement": "age",
                "mean": "30",
                "unit": "kg",
            },
            {("unit_dimension", "unit")},
        ),
    ],
)
def test_units_fit_the_measurement(run, kind, row, expected):
    file = "outputs_Tab2.tsv" if kind == "outputs" else None
    assert run(kind, row, file=file) == expected


def test_unit_dimension_names_the_allowed_units(
    make_study, valid_files, tsv, sf_vocabulary
):
    files = {**valid_files, "outputs_Tab2.tsv": tsv("outputs", {**CMAX, "unit": "h"})}
    [issue] = check_terms(load_study(make_study(files)), sf_vocabulary)
    assert (issue.severity, issue.category) == ("error", "vocabulary")
    assert issue.source is not None and issue.source.cell == "X2"
    assert issue.suggestions[0].candidates == ["mg/l"]


def test_scatter_axis_units_fit_the_measurement(run):
    row = {
        "name": "s",
        "subjects": "S1",
        "x_measurement": "age",
        "x_mean": "30",
        "x_unit": "mg",
        "y_measurement": "cmax",
        "y_substance": "drug",
        "y_mean": "2",
        "y_unit": "h",
    }
    assert run("scatters", row, file="scatters_Fig2.tsv") == {
        ("unit_dimension", "x_unit"),
        ("unit_dimension", "y_unit"),
    }


def test_scatter_axes(run):
    row = {
        "name": "s",
        "subjects": "S1",
        "x_measurement": "agee",
        "x_mean": "30",
        "y_measurement": "cmax",
        "y_mean": "-2",
        "y_unit": "mg/l",
    }
    assert run("scatters", row, file="scatters_Fig2.tsv") == {
        ("unknown_measurement", "x_measurement"),
        ("negative_value", "y_mean"),
    }


def test_scatter_axis_time_and_unit(run):
    row = {
        "name": "s",
        "subjects": "S1",
        "x_measurement": "concentration",
        "x_substance": "drug",
        "x_mean": "1",
        "y_measurement": "cmax",
        "y_mean": "2",
        "y_unit": "mg/l",
    }
    assert run("scatters", row, file="scatters_Fig2.tsv") == {
        ("missing_time", "x_time"),
        ("missing_unit", "x_unit"),
    }


def test_measurement_without_unit(make_study, valid_files, tsv, sf_vocabulary):
    measurements = tuple(
        rule.model_copy(update={"units": ("NO_UNIT",)}) if rule.name == "age" else rule
        for rule in sf_vocabulary.measurements
    )
    vocabulary = sf_vocabulary.model_copy(update={"measurements": measurements})
    files = {
        **valid_files,
        "characteristica.tsv": tsv(
            "characteristica",
            {"source": "Tab1", "subjects": "all", "measurement": "age", "mean": "30"},
        ),
    }
    study = load_study(make_study(files))
    assert check_terms(study, vocabulary) == []
    assert [issue.code for issue in check_terms(study, sf_vocabulary)] == [
        "missing_unit"
    ]


def test_suggestions_name_their_kind():
    choices = make_issue("unknown_reference", "No row.", candidates=["all"])
    assert [(s.kind, s.candidates) for s in choices.suggestions] == [
        (CANDIDATES, ["all"])
    ]
    hint = make_issue(
        "unit_dimension", "No unit.", hint="Units of cmax.", candidates=["mg/l"]
    )
    assert hint.suggestions[0].kind == FIX
    term = make_issue(
        "unknown_tissue",
        "Unknown.",
        hint="Caveat.",
        candidates=["plasma"],
        suggestion=VOCABULARY,
    )
    assert term.suggestions[0].kind == VOCABULARY


def test_an_unknown_term_suggests_spellings_of_the_vocabulary(
    make_study, valid_files, sf_vocabulary
):
    outputs = valid_files["outputs_Tab2.tsv"].replace("plasma", "plasm")
    folder = make_study({**valid_files, "outputs_Tab2.tsv": outputs})
    assert format_folder(folder).ok
    [issue] = [
        i
        for i in validate_folder(folder, sf_vocabulary).issues
        if i.code == "unknown_tissue"
    ]
    assert issue.suggestions[0].kind == VOCABULARY
