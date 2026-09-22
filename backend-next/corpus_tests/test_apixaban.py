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


def test_frost2014_postgresql_outputs_match_legacy(
    full_vocabulary, session_factory, tmp_path
):
    import json
    import math
    import shutil

    from sqlalchemy import select

    from pkdb.db.bootstrap import bootstrap
    from pkdb.db.models.studies import Study
    from pkdb.db.models.users import User
    from pkdb.db.replace import insert_graph
    from pkdb.domain.validation import prepare_study
    from pkdb.schemas.queries import QuerySpec
    from pkdb.schemas.security import Principal
    from pkdb.services.queries import QueryService

    study = prepare_study(
        parse_bundle(load_folder(ROOT / "Frost2014")), full_vocabulary
    ).study
    usernames = {
        study.metadata.creator,
        *[c.user for c in study.metadata.curators],
        *study.metadata.collaborators,
    }
    (tmp_path / "users.json").write_text(
        json.dumps([{"username": username} for username in usernames])
    )
    shutil.copy(
        Path(__file__).parents[1] / "bootstrap/vocabulary.json",
        tmp_path / "vocabulary.json",
    )
    with session_factory.begin() as session:
        assert not bootstrap(tmp_path, session).errors
        owner = session.scalar(
            select(User).where(User.username == study.metadata.creator)
        )
        root = Study(
            sid=study.sid,
            name=study.metadata.name,
            access="public",
            licence="closed",
            creator_id=owner.id,
        )
        session.add(root)
        session.flush()
        insert_graph(session, root, study)
    page = QueryService(session_factory).search(
        QuerySpec(entity="outputs", page_size=1000), Principal()
    )
    fixture = json.loads(
        (
            Path(__file__).parents[1]
            / "tests/fixtures/golden/frost2014-measurements.json"
        ).read_text()
    )
    records = []
    for row in page.items:
        result = {
            key: row[key]
            for key in (
                "normed",
                "calculated",
                "label",
                "output_type",
                "time",
                "time_unit",
                "unit",
                "value",
                "mean",
                "median",
                "min",
                "max",
                "sd",
                "se",
                "cv",
            )
        }
        if row["calculated"]:
            result["output_type"] = "output"
        for key in (
            "measurement_type",
            "substance",
            "calculation_type",
            "choice",
            "tissue",
            "method",
            "group",
            "individual",
        ):
            result[key] = row[key]["name"] if row[key] else None
        result["interventions"] = sorted(r["name"] for r in row["interventions"])
        records.append(result)

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

    expected = {identity(row): row for row in fixture["records"]}
    actual = {identity(row): row for row in records}
    assert len(records) == len(actual) == len(expected) == page.count == 782
    assert actual.keys() == expected.keys()
    for key, wanted in expected.items():
        tolerance = fixture["tolerances"][wanted["measurement_type"]]
        for field, value in wanted.items():
            found = actual[key][field]
            if type(value) is float and type(found) is float:
                assert math.isclose(
                    value, found, rel_tol=tolerance["rtol"], abs_tol=tolerance["atol"]
                ), (key, field)
            else:
                assert found == value, (key, field, value, found)

    stats = QueryService(session_factory).statistics(Principal())
    assert stats == {
        "study_count": 1,
        "reference_count": 1,
        "group_count": 1,
        "individual_count": 70,
        "intervention_count": 2,
        "output_count": 391,
        "output_calculated_count": 12,
        "timecourse_count": 4,
        "scatter_count": 0,
    }

    subjects = json.loads(
        (
            Path(__file__).parents[1] / "tests/fixtures/golden/frost2014-subjects.json"
        ).read_text()
    )

    def stable(value):
        if isinstance(value, list):
            return sorted(
                [stable(v) for v in value], key=lambda v: json.dumps(v, sort_keys=True)
            )
        if isinstance(value, dict):
            return {key: stable(v) for key, v in value.items() if key != "pk"}
        return value

    for entity in ("groups", "individuals"):
        page = QueryService(session_factory).search(
            QuerySpec.model_validate({"entity": entity, "page_size": 1000}), Principal()
        )
        actual_subjects = stable(page.items)
        for actual_subject, expected_subject in zip(
            actual_subjects, subjects[entity], strict=True
        ):
            for field in expected_subject:
                if field == "characteristica":
                    for actual_char, expected_char in zip(
                        actual_subject[field], expected_subject[field], strict=True
                    ):
                        for char_field in expected_char:
                            assert (
                                actual_char[char_field] == expected_char[char_field]
                            ), (
                                entity,
                                actual_subject["name"],
                                expected_char["measurement_type"]["name"],
                                char_field,
                                actual_char[char_field],
                                expected_char[char_field],
                            )
                else:
                    assert actual_subject[field] == expected_subject[field]

    page = QueryService(session_factory).search(
        QuerySpec.model_validate({"entity": "interventions", "page_size": 1000}),
        Principal(),
    )
    assert stable(page.items) == subjects["interventions"]

    page = QueryService(session_factory).search(
        QuerySpec(entity="references"), Principal()
    )
    assert stable(page.items) == stable(subjects["references"])
    assert [author["first_name"] for author in page.items[0]["authors"]] == [
        author["first_name"] for author in subjects["references"][0]["authors"]
    ]
