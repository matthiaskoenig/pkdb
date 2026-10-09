import pytest

from pkdb.lifecycle.names import parse_location


def test_valid_locations():
    assert parse_location("caffeine/Harder1988") == ("caffeine", "Harder1988")
    assert parse_location("Gd-EOB-DTPA/Al-Hadidi1994") == (
        "Gd-EOB-DTPA",
        "Al-Hadidi1994",
    )
    assert parse_location("acetaminophen_mice/Smith_2020b") == (
        "acetaminophen_mice",
        "Smith_2020b",
    )


@pytest.mark.parametrize(
    "value, message",
    [
        ("Harder1988", "<substance>/<name>"),
        ("caffeine/Harder 1988", "letters, digits"),
        ("caffeine/.hidden", "letters, digits"),
        ("caffeine/a/b", "<substance>/<name>"),
        ("caffeine/" + "A" * 25, "24 characters"),
        ("caffeine/outputs", "reserved"),
    ],
)
def test_invalid_locations(value, message):
    with pytest.raises(ValueError, match=message):
        parse_location(value)
