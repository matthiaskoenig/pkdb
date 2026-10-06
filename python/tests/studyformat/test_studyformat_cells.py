import pytest

from pkdb.studyformat.cells import canonical_cell, parse_cell
from pkdb.studyformat.tables import TABLES

OUT = TABLES["outputs"]
IV = TABLES["interventions"]
SUB = TABLES["subjects"]


@pytest.mark.parametrize(
    ("column", "text", "expected"),
    [
        (OUT.column("mean"), " 2.50 ", "2.5"),
        (OUT.column("mean"), "NA", ""),
        (OUT.column("mean"), "nan", ""),
        (OUT.column("mean"), "2,5", "2,5"),
        (OUT.column("count"), "17.0", "17"),
        (OUT.column("time"), "NR", "NR"),
        (OUT.column("time"), "0.50", "0.5"),
        (IV.column("time"), "0; 12.0 ;40", "0;12;40"),
        (OUT.column("interventions"), "D2, D10 ,D1", "D1,D2,D10"),
        (OUT.column("comment"), "NA", "NA"),
        (OUT.column("choice"), "NA", "NA"),
        (OUT.column("unit"), "mg/l", "mg/l"),
    ],
)
def test_canonical_cell(column, text, expected):
    assert canonical_cell(column, text) == expected


@pytest.mark.parametrize(
    ("column", "text", "value"),
    [
        (OUT.column("mean"), "", None),
        (OUT.column("interventions"), "", ()),
        (OUT.column("mean"), "2.5", 2.5),
        (OUT.column("count"), "17", 17),
        (OUT.column("time"), "NR", "NR"),
        (OUT.column("time_unit"), "NR", "NR"),
        (OUT.column("time"), "1.5", 1.5),
        (IV.column("time"), "0;12", (0.0, 12.0)),
        (IV.column("time"), "3", (3.0,)),
        (OUT.column("interventions"), "D1,D2", ("D1", "D2")),
        (OUT.column("subjects"), "Gruppe Ä", "Gruppe Ä"),
        (OUT.column("error_type"), "gsd", "gsd"),
        (SUB.column("source"), "Fig3A", "Fig3A"),
        (SUB.column("source"), "Text", "Text"),
    ],
)
def test_parse_cell_values(column, text, value):
    assert parse_cell(column, text) == (value, None)


@pytest.mark.parametrize(
    ("column", "text", "code"),
    [
        (OUT.column("mean"), "abc", "invalid_number"),
        (OUT.column("count"), "2.5", "invalid_integer"),
        (OUT.column("count"), "-1", "invalid_integer"),
        (OUT.column("time"), "early", "invalid_time"),
        (IV.column("time"), "0;x", "invalid_time"),
        (OUT.column("subjects"), "a;b", "invalid_name"),
        (OUT.column("interventions"), "D1,,D2", "invalid_name"),
        (OUT.column("error_type"), "SD", "invalid_enum"),
        (SUB.column("source"), "Table 2", "invalid_source"),
        (OUT.column("mean"), "NR", "invalid_number"),
    ],
)
def test_parse_cell_problems(column, text, code):
    value, problem = parse_cell(column, text)
    assert value is None
    assert problem is not None and problem.code == code


def test_decimal_comma_hint():
    _, problem = parse_cell(OUT.column("mean"), "2,9")
    assert problem is not None
    assert problem.code == "invalid_number"
    assert problem.hint is not None
    assert "decimal point" in problem.hint


@pytest.mark.parametrize(
    ("column", "text", "code", "hint"),
    [
        (
            OUT.column("count"),
            "2,5",
            "invalid_integer",
            "Use a decimal point: 2.5 instead of 2,5.",
        ),
        (
            OUT.column("time"),
            "1,5",
            "invalid_time",
            "Use a decimal point: 1.5 instead of 1,5.",
        ),
        (
            IV.column("time"),
            "0;1,5;3",
            "invalid_time",
            "Use a decimal point: 0;1.5;3 instead of 0;1,5;3.",
        ),
        (OUT.column("time"), "early", "invalid_time", None),
        (IV.column("time"), "0;x", "invalid_time", None),
    ],
)
def test_decimal_comma_hint_for_all_numbers(column, text, code, hint):
    _, problem = parse_cell(column, text)
    assert problem is not None
    assert (problem.code, problem.hint) == (code, hint)
