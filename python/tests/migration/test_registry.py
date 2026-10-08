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
    release = registry.release("albuterol/Guo2016")
    assert release is not None
    assert (release.pkdb_id, release.date) == ("PKDB01237", date(2026, 9, 28))
    assert registry.release("albuterol/Other2000") is None


def test_no_registry_releases_nothing():
    assert Registry.read(None).release("caffeine/Example") is None


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
        registry.release("caffeine/Example")
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
