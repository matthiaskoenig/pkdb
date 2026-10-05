import pytest

from pkdb.studyformat.text import (
    TsvError,
    canonical_number,
    format_number,
    natural_key,
    parse_number,
    parse_tsv,
    render_tsv,
    unquote,
)

BOM = chr(0xFEFF)
NBSP = chr(0xA0)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2.90", "2.9"),
        ("43.0", "43"),
        ("43", "43"),
        ("-0", "0"),
        ("+2", "2"),
        (".5", "0.5"),
        ("1e-3", "0.001"),
        ("0.00001", "1e-05"),
        ("1.94326186260799", "1.94326186260799"),
        ("1e16", "1e+16"),
        ("2,9", None),
        ("1_000", None),
        ("nan", None),
        ("inf", None),
        ("1e999", None),
        ("abc", None),
        ("", None),
    ],
)
def test_canonical_number(text, expected):
    assert canonical_number(text) == expected


def test_parse_and_format_number_round_trip():
    for value in (0.1, 1 / 3, 123456.789, -2.5e-12):
        assert parse_number(format_number(value)) == value


def test_natural_key_orders_numbers_by_value():
    names = ["Tab10", "Tab2", "Fig1", "tab3", "Tab2a"]
    assert sorted(names, key=natural_key) == ["Fig1", "Tab2", "Tab2a", "tab3", "Tab10"]


def test_natural_key_handles_non_ascii():
    assert sorted(["Ä2", "A10", "A2"], key=natural_key) == ["A2", "A10", "Ä2"]


def test_unquote():
    assert unquote('"D1,D2"') == "D1,D2"
    assert unquote('"say ""hi"""') == 'say "hi"'
    assert unquote('"a" and "b"') == '"a" and "b"'
    assert unquote("plain") == "plain"
    assert unquote('"') == '"'


def test_parse_tsv_normalizes_line_endings_bom_and_whitespace():
    text = f"{BOM}name\tcount \r\n all\t{NBSP}4\r\n\r\n\t\t\r\nS1\t1\n"
    parsed = parse_tsv(text.encode())
    assert parsed.header == ("name", "count")
    assert [(line.number, line.cells) for line in parsed.lines] == [
        (2, ("all", "4")),
        (5, ("S1", "1")),
    ]


def test_parse_tsv_keeps_ragged_rows():
    parsed = parse_tsv(b"a\tb\tc\nx\n")
    assert parsed.lines[0].cells == ("x",)


def test_parse_tsv_empty_file():
    assert parse_tsv(b"").header == ()


def test_parse_tsv_rejects_non_utf8():
    with pytest.raises(TsvError, match="UTF-8"):
        parse_tsv("name\nDahlström".encode("latin-1"))


def test_render_tsv():
    assert render_tsv(("a", "b"), [("1", ""), ("x", "y")]) == "a\tb\n1\t\nx\ty\n"
