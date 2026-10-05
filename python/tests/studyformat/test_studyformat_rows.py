import json
import subprocess
import sys

import pytest

from pkdb.studyformat.load import load_study
from pkdb.studyformat.rows import check_rows, subject_counts

CMAX = {
    "subjects": "all",
    "interventions": "D1",
    "measurement": "cmax",
    "substance": "drug",
    "tissue": "plasma",
    "unit": "mg/l",
}


@pytest.fixture
def run(make_study, valid_files, tsv):
    def check(kind=None, *rows, file=None, **files):
        if kind is not None:
            files[file or f"{kind}.tsv"] = tsv(kind, *rows)
        study = load_study(make_study({**valid_files, **files}))
        found = set()
        for issue in check_rows(study):
            assert issue.source is not None
            found.add((issue.code, issue.source.header))
        return found

    return check


def test_valid_study_passes(run):
    assert run() == set()


def test_required(run):
    # Whether a row needs a value depends on its measurement (layer 5).
    found = run("outputs", {"subjects": "all", "comment": "x"}, file="outputs_Tab2.tsv")
    assert found == {("missing_required", "measurement")}


def test_subject_count(run):
    found = run("subjects", {"name": "all", "count": "0"})
    assert ("invalid_count", "count") in found


def test_choice_rows_have_no_statistics(run):
    row = {
        "source": "Tab1",
        "subjects": "all",
        "measurement": "sex",
        "choice": "M",
        "mean": "3",
    }
    assert run("characteristica", row) == {("choice_statistics", "mean")}


def test_individual_statistics(run):
    individual = {
        "source": "TabA",
        "subjects": "S1",
        "measurement": "age",
        "mean": "30",
        "sd": "2",
        "unit": "yr",
    }
    explicit = {
        "source": "TabA",
        "subjects": "all",
        "measurement": "age",
        "count": "1",
        "mean": "30",
        "min": "1",
        "unit": "yr",
    }
    assert run("characteristica", individual, explicit) == {
        ("individual_statistics", "sd"),
        ("individual_statistics", "min"),
    }


def test_unspecified_summary(run):
    row = {**CMAX, "calculation": "unspecified summary", "mean": "2", "se": "0.1"}
    assert run("outputs", row, file="outputs_Tab2.tsv") == {
        ("unspecified_summary_statistics", "se")
    }


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        ({"mean": "2", "error_bar": "3"}, {("incomplete_error_bar", "error_type")}),
        ({"mean": "2", "error_type": "sd"}, {("incomplete_error_bar", "error_bar")}),
        (
            {"mean": "2", "error_bar": "3", "error_type": "gsd"},
            {("incomplete_error_bar", "gmean")},
        ),
        (
            {"mean": "2", "sd": "1", "error_bar": "3", "error_type": "sd"},
            {("error_bar_conflict", "sd")},
        ),
        ({"mean": "2", "error_bar": "3", "error_type": "se"}, set()),
    ],
)
def test_error_bars(run, extra, expected):
    assert run("outputs", {**CMAX, **extra}, file="outputs_Tab2.tsv") == expected


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        ({"min": "5", "max": "1"}, {("reversed_range", "min")}),
        ({"mean": "10", "min": "1", "max": "5"}, {("outside_range", "mean")}),
        ({"mean": "2", "sd": "-1"}, {("invalid_statistic", "sd")}),
        ({"gmean": "2", "gsd": "0.5"}, {("invalid_statistic", "gsd")}),
        ({"gmean": "0"}, {("invalid_statistic", "gmean")}),
        ({"mean": "2", "cv": "-3"}, {("invalid_statistic", "cv")}),
    ],
)
def test_ranges_and_spreads(run, extra, expected):
    assert run("outputs", {**CMAX, **extra}, file="outputs_Tab2.tsv") == expected


def test_outside_range_is_a_warning(make_study, valid_files, tsv):
    files = {
        **valid_files,
        "outputs_Tab2.tsv": tsv(
            "outputs", {**CMAX, "mean": "10", "min": "1", "max": "5"}
        ),
    }
    issues = check_rows(load_study(make_study(files)))
    assert [issue.severity for issue in issues] == ["warning"]


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        ({"mean": "2", "time": "1"}, {("missing_time_unit", "time_unit")}),
        (
            {"mean": "2", "time": "1", "time_unit": "kg"},
            {("time_dimension", "time_unit")},
        ),
        (
            {"mean": "2", "time": "1", "time_unit": "blorp"},
            {("invalid_time_unit", "time_unit")},
        ),
        ({"mean": "2", "time": "NR", "time_unit": "NR"}, set()),
        ({"mean": "2", "unit": "mg%"}, {("invalid_unit", "unit")}),
        ({"mean": "2", "unit": "foo"}, {("invalid_unit", "unit")}),
        ({"mean": "2", "unit": "µg/l"}, set()),
        ({"mean": "2", "unit": "mg/(l"}, {("invalid_unit", "unit")}),
        ({"mean": "2", "unit": "1/0"}, {("invalid_unit", "unit")}),
        ({"mean": "2", "unit": "*)"}, {("invalid_unit", "unit")}),
        ({"mean": "2", "unit": "5"}, {("invalid_unit", "unit")}),
        ({"mean": "2", "unit": "10^9"}, {("invalid_unit", "unit")}),
        ({"mean": "2", "unit": "ml/min/(1.73*m^2)"}, set()),
        ({"mean": "2", "unit": "l/(1.73*m^2)"}, set()),
        ({"mean": "2", "unit": "g/(1.73*m^2)"}, set()),
        ({"mean": "2", "unit": "10^9/l"}, set()),
        ({"mean": "2", "unit": "1/h"}, set()),
        ({"mean": "2", "unit": "dimensionless"}, set()),
        (
            {"mean": "2", "time": "1", "time_unit": "(h"},
            {("invalid_time_unit", "time_unit")},
        ),
        (
            {"mean": "2", "time": "1", "time_unit": "5"},
            {("invalid_time_unit", "time_unit")},
        ),
        ({"mean": "2", "time": "1", "time_unit": "2 h"}, set()),
        ({"mean": "2", "time": "1", "time_unit": "min"}, set()),
        (
            {"mean": "2", "time": "1", "time_unit": "h%"},
            {("invalid_time_unit", "time_unit")},
        ),
        ({"mean": "2", "unit": "mg*hr^2/l"}, set()),
        ({"mean": "2", "unit": "kg^0.75"}, set()),
        ({"mean": "2", "unit": "m**2"}, set()),
        ({"mean": "2", "unit": "10^12/l"}, set()),
    ],
)
def test_times_and_units(run, extra, expected):
    assert run("outputs", {**CMAX, **extra}, file="outputs_Tab2.tsv") == expected


def test_time_unit_characters_are_checked(make_study, valid_files, tsv):
    row = {**CMAX, "mean": "2", "time": "1", "time_unit": "h%"}
    files = {**valid_files, "outputs_Tab2.tsv": tsv("outputs", row)}
    [issue] = check_rows(load_study(make_study(files)))
    assert issue.code == "invalid_time_unit"
    assert "unsupported characters" in issue.message


# pint evaluates powers exactly: before the guard, each of these took minutes.
POWER_UNITS = [
    "9^9^9 g",
    "10**10**10 g",
    "10^(10^10) g",
    "(10^10)^10 g",
    "((9^9)^9)^9 g",
    "10^999 g",
    "g^-999",
    "9 ^ 9 ^ 9 g",
]
POWER_TIME_UNITS = ["10^10^10 hr", "10**10**10 hr", "hr^999", "(hr^99)^99"]
CHECK = """
import json, sys, time
from pkdb.studyformat.rows import time_unit_status, unit_known
result = {}
for unit in json.loads(sys.argv[1]):
    start = time.monotonic()
    result[unit] = [unit_known(unit), time_unit_status(unit), time.monotonic() - start]
print(json.dumps(result))
"""


def test_power_bombs_are_rejected_quickly():
    # A child process with a timeout fails the test instead of hanging the suite.
    units = [*POWER_UNITS, *POWER_TIME_UNITS]
    output = subprocess.run(
        [sys.executable, "-c", CHECK, json.dumps(units)],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    ).stdout
    for unit, (known, status, seconds) in json.loads(output).items():
        assert (unit, known, status) == (unit, False, "invalid")
        assert seconds < 1, unit


def test_timecourse_needs_numeric_time(run):
    row = {
        "label": "a",
        "subjects": "all",
        "measurement": "concentration",
        "time": "NR",
        "time_unit": "h",
        "mean": "1",
    }
    assert run("timecourses", row, file="timecourses_Fig1.tsv") == {
        ("invalid_time", "time")
    }


DOSE = {
    "source": "Text",
    "name": "D1",
    "measurement": "dosing",
    "substance": "drug",
    "route": "oral",
    "time_unit": "h",
    "mean": "100",
    "unit": "mg",
}


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        ({"time": "0;12", "interval": "12"}, {("schedule_conflict", "interval")}),
        ({"time": "0;12", "doses": "2"}, {("schedule_conflict", "doses")}),
        ({"time": "0", "interval": "24"}, {("invalid_schedule", "doses")}),
        (
            {"time": "0", "interval": "0", "doses": "2"},
            {("invalid_schedule", "interval")},
        ),
        ({"time": "0", "doses": "3"}, {("invalid_schedule", "interval")}),
        ({"time": "0", "doses": "0"}, {("invalid_schedule", "doses")}),
        ({"time": "2", "time_end": "1"}, {("invalid_schedule", "time_end")}),
        ({"time": "0", "interval": "24", "doses": "7"}, set()),
        ({"time": "0;12;40"}, set()),
    ],
)
def test_schedules(run, extra, expected):
    assert run("interventions", {**DOSE, **extra}) == expected


def test_scatter_axes(run):
    row = {
        "name": "s",
        "subjects": "S1",
        "x_measurement": "age",
        "x_mean": "30",
        "x_unit": "yr",
        "x_time": "2",
        "y_measurement": "cmax",
        "y_mean": "2",
        "y_unit": "mg%",
    }
    assert run("scatters", row, file="scatters_Fig2.tsv") == {
        ("missing_time_unit", "x_time_unit"),
        ("invalid_unit", "y_unit"),
    }


def test_subject_counts(make_study, valid_files):
    study = load_study(make_study(valid_files))
    assert subject_counts(study) == {"all": 2, "S1": 1, "S2": 1}


def test_issues_are_located_at_row_and_column(make_study, valid_files, tsv):
    row = {**CMAX, "mean": "2", "sd": "-1"}
    files = {**valid_files, "outputs_Tab2.tsv": tsv("outputs", row)}
    study = load_study(make_study(files))
    (issue,) = check_rows(study)
    table = study.table("outputs_Tab2.tsv")
    assert table is not None
    assert issue.source is not None
    assert (issue.source.file, issue.source.sheet, issue.source.row) == (
        "outputs_Tab2.tsv",
        "outputs_Tab2",
        2,
    )
    assert issue.source.header == "sd"
    letter = chr(ord("A") + table.header.index("sd"))
    assert (issue.source.column, issue.source.cell) == (letter, f"{letter}2")
    assert (issue.category, issue.stage, issue.severity) == (
        "scientific",
        "validate",
        "error",
    )
