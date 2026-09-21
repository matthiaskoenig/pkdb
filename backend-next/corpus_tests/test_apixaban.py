"""Explicit corpus gate: absence of the requested corpus is an error, not a skip."""

import os
from pathlib import Path

import pytest

from pkdb.importers.folder import load_folder, parse_bundle

ROOT = Path(os.environ["PKDB_STUDY_CORPUS"]) / "apixaban"
PATHS = sorted(path.parent for path in ROOT.glob("*/study.json"))
assert PATHS, f"No apixaban studies in {ROOT}"


@pytest.mark.parametrize("folder", PATHS, ids=lambda path: path.name)
def test_apixaban_parses_without_source_edits(folder):
    study = parse_bundle(load_folder(folder))
    assert study.sid
    assert study.reference.sid
    assert study.groups
    assert study.interventions
    assert study.measurements
    assert all(record.source is not None for record in study.measurements)


@pytest.mark.parametrize("folder", PATHS, ids=lambda path: path.name)
def test_apixaban_scientific_validation(folder, full_vocabulary):
    from pkdb.domain.validation import prepare_study

    prepared = prepare_study(parse_bundle(load_folder(folder)), full_vocabulary)
    assert prepared.report.valid


def test_frost2014_matches_all_legacy_measurements(full_vocabulary):
    import json
    import math

    from pkdb.domain.validation import prepare_study

    fixture = json.loads(
        (
            Path(__file__).parents[1]
            / "tests/fixtures/golden/frost2014-measurements.json"
        ).read_text()
    )
    study = prepare_study(
        parse_bundle(load_folder(ROOT / "Frost2014")), full_vocabulary
    ).study
    records = []
    for record in study.measurements:
        data = {
            name: getattr(record, name)
            for name in [
                "label",
                "output_type",
                "time",
                "time_unit",
                "unit",
                "measurement_type",
                "substance",
                "group",
                "individual",
                "calculation_type",
                "choice",
                "tissue",
                "method",
            ]
        }
        data.update(
            {
                name: getattr(record.statistics, name)
                for name in ["value", "mean", "median", "min", "max", "sd", "se", "cv"]
            }
        )
        data.update(
            interventions=sorted(record.interventions),
            normed=record.origin == "normalized",
            calculated=record.calculated,
        )
        records.append(data)

    def identity(record):
        return tuple(
            str(record[name])
            for name in [
                "normed",
                "calculated",
                "measurement_type",
                "substance",
                "group",
                "individual",
                "interventions",
                "label",
                "time",
            ]
        )

    expected = {identity(record): record for record in fixture["records"]}
    actual = {identity(record): record for record in records}
    assert len(records) == len(actual) == len(expected) == 782
    assert actual.keys() == expected.keys()
    for key, wanted in expected.items():
        tolerance = fixture["tolerances"][wanted["measurement_type"]]
        for field, value in wanted.items():
            found = actual[key][field]
            if type(value) is float and type(found) is float:
                assert math.isclose(
                    value, found, rel_tol=tolerance["rtol"], abs_tol=tolerance["atol"]
                ), (key, field, value, found)
            else:
                assert found == value, (key, field, value, found)
