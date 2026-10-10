import json
from datetime import date

import pytest

from pkdb.migration.model import NotConverted
from pkdb.migration.registry import Registry


def write(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_the_release_of_a_registered_study(tmp_path):
    registry = Registry.read(
        write(tmp_path / "ids.json", {"PKDB01237": ["albuterol/Guo2016", "2026-09-28"]})
    )
    for sid in ("PKDB01237", "Guo2016", ""):
        release = registry.release("albuterol/Guo2016", sid)
        assert release is not None
        assert (release.pkdb_id, release.date) == ("PKDB01237", date(2026, 9, 28))
    assert registry.release("albuterol/Other2000", "Other2000") is None


def test_no_registry_releases_nothing():
    assert Registry.read(None).release("caffeine/Example", "Example") is None


def test_a_pkdb_sid_without_a_registry_entry_refuses_the_study():
    registry = Registry({"PKDB00121": ("acetaminophen/Ganetzky2013", date(2020, 1, 1))})
    for sid, said in [
        ("PKDB00121", " and gives PKDB00121 to acetaminophen/Ganetzky2013"),
        ("PKDB00999", ""),
    ]:
        with pytest.raises(NotConverted) as error:
            registry.release("acetaminophen/Ganetsky2013", sid)
        assert (error.value.code, error.value.message) == (
            "registry_sid",
            f"study.json has the identifier {sid}, but the registry has no "
            f"identifier for acetaminophen/Ganetsky2013{said}. "
            "Fix the registry or the sid.",
        )
    # Without a registry, no study with a PKDB identifier is written unreleased.
    with pytest.raises(NotConverted):
        Registry().release("acetaminophen/Ganetsky2013", "PKDB00121")


def test_a_pkdb_sid_other_than_the_registry_identifier_refuses_the_study():
    registry = Registry(
        {
            "PKDB00112": ("codeine/Yue1989", date(2020, 1, 1)),
            "PKDB00113": ("codeine/Yue1989a", date(2020, 1, 1)),
        }
    )
    with pytest.raises(NotConverted) as error:
        registry.release("codeine/Yue1989", "PKDB00113")
    assert (error.value.code, error.value.message) == (
        "registry_sid",
        "study.json has the identifier PKDB00113, but the registry gives "
        "codeine/Yue1989 the identifier PKDB00112 and PKDB00113 to codeine/Yue1989a. "
        "Fix the registry or the sid.",
    )


def test_two_identifiers_of_one_study_refuse_it(tmp_path):
    registry = Registry.read(
        write(
            tmp_path / "ids.json",
            {
                "PKDB00001": ["caffeine/Example", "2020-01-01"],
                "PKDB00002": ["caffeine/Example", "2021-01-01"],
            },
        )
    )
    with pytest.raises(NotConverted) as error:
        registry.release("caffeine/Example", "PKDB00001")
    assert error.value.code == "double_identifier"
    assert "PKDB00001" in error.value.message and "PKDB00002" in error.value.message


def test_findings_name_double_identifiers_and_missing_paths(tmp_path):
    root = tmp_path
    (root / "studies" / "caffeine" / "Example").mkdir(parents=True)
    registry = Registry.read(
        write(
            tmp_path / "ids.json",
            {
                "PKDB00001": ["caffeine/Example", "2020-01-01"],
                "PKDB00002": ["caffeine/Example", "2021-01-01"],
                "PKDB00003": ["caffeine/Gone1999", "2021-01-01"],
            },
        )
    )
    findings = registry.findings(root)
    assert findings.double_identifiers == {
        "caffeine/Example": ["PKDB00001", "PKDB00002"]
    }
    assert findings.missing_paths == ["caffeine/Gone1999"]


@pytest.mark.parametrize(
    ("content", "problem"),
    [
        ("{", "is not JSON"),
        ("[]", "must map"),
        ('{"PKDB00001": ["a/B"]}', "entry PKDB00001"),
        ('{"PKDB00001": "a/B"}', "entry PKDB00001"),
        ('{"PKDB00001": ["a/B", "yesterday"]}', "entry PKDB00001"),
        ('{"PKDB00001": ["a/B", 3]}', "entry PKDB00001"),
    ],
)
def test_a_malformed_registry_names_the_file_and_entry(tmp_path, content, problem):
    path = tmp_path / "ids.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match=problem) as error:
        Registry.read(path)
    assert "ids.json" in str(error.value)


def test_the_locations_are_indexed_once():
    registry = Registry({"PKDB00001": ("a/B", date(2020, 1, 1))})
    assert registry.release("a/B", "B") is not None
    assert registry.release("a/C", "C") is None
    assert registry._by_location is registry._by_location
