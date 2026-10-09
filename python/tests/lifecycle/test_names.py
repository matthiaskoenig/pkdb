import pytest

from pkdb.lifecycle.names import case_twin, parse_location


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
        ("caffeine/Outputs", "reserved"),
        ("caffeine/VALIDATE", "reserved"),
    ],
)
def test_invalid_locations(value, message):
    with pytest.raises(ValueError, match=message):
        parse_location(value)


def test_case_twin(tmp_path):
    (tmp_path / "Smith2020").mkdir()
    assert case_twin(tmp_path, "smith2020") == "Smith2020"
    assert case_twin(tmp_path, "Smith2020") is None
    assert case_twin(tmp_path, "Jones2021") is None
    assert case_twin(tmp_path / "missing", "Smith2020") is None
