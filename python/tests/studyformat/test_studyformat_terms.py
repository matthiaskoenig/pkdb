import pytest

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
    assert issue.suggestions[0].candidates == ["cmax"]


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
