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
            date=study.metadata.date,
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

    page = QueryService(session_factory).search(
        QuerySpec.model_validate({"entity": "subsets", "page_size": 1000}), Principal()
    )

    def without_ids(value):
        if isinstance(value, dict):
            return {
                key: without_ids(item) for key, item in value.items() if key != "pk"
            }
        if isinstance(value, list):
            return [without_ids(item) for item in value]
        return value

    def compare(actual, expected):
        if isinstance(expected, dict):
            assert actual.keys() == expected.keys()
            for key in expected:
                compare(actual[key], expected[key])
        elif isinstance(expected, list):
            assert len(actual) == len(expected)
            for left, right in zip(actual, expected, strict=True):
                compare(left, right)
        elif isinstance(expected, float):
            assert math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-12)
        else:
            assert actual == expected

    compare(
        sorted(without_ids(page.items), key=lambda row: row["name"]),
        sorted(without_ids(subjects["subsets"]), key=lambda row: row["name"]),
    )

    public_study = (
        QueryService(session_factory)
        .search(QuerySpec(entity="studies"), Principal())
        .items[0]
    )
    expected_study = subjects["study"]
    expected_study[
        "files"
    ] = []  # Anonymous reads cannot list this closed-license study's files.
    for section, entity in (
        ("groupset", "groups"),
        ("individualset", "individuals"),
        ("interventionset", "interventions"),
        ("outputset", "outputs"),
        ("dataset", "subsets"),
    ):
        predicates = (
            [{"field": "normed", "value": True}]
            if entity in {"outputs", "interventions"}
            else []
        )
        children = (
            QueryService(session_factory)
            .search(
                QuerySpec.model_validate(
                    {"entity": entity, "predicates": predicates, "page_size": 1000}
                ),
                Principal(),
            )
            .items
        )
        linked = public_study[section][entity]
        assert set(linked) == {child["pk"] for child in children}
        assert len(linked) == len(children)
        public_study[section][entity] = len(linked)
        expected_study[section][entity] = len(expected_study[section][entity])
    # Member/substance ordering was not a legacy contract; author and point order were.
    for field in ("curators", "collaborators", "substances"):
        public_study[field] = sorted(
            public_study[field], key=lambda row: json.dumps(row, sort_keys=True)
        )
        expected_study[field] = sorted(
            expected_study[field], key=lambda row: json.dumps(row, sort_keys=True)
        )
    compare(without_ids(public_study), without_ids(expected_study))

    from pkdb.db.analysis import ENTITIES
    from pkdb.services.analysis import AnalysisService

    analysis_golden = json.loads(
        (
            Path(__file__).parents[1] / "tests/fixtures/golden/frost2014-analysis.json"
        ).read_text()
    )
    actual_identities = {}
    for entity in ("groups", "individuals", "interventions", "outputs"):
        actual_identities[entity] = {
            str(row["pk"]): row
            for row in QueryService(session_factory)
            .search(
                QuerySpec.model_validate({"entity": entity, "page_size": 1000}),
                Principal(),
            )
            .items
        }

    def stable_analysis(rows, identities):
        def identity(entity, identifier):
            if identifier is None:
                return None
            row = identities[entity][str(identifier)]
            if entity == "outputs":
                return {
                    "normed": row["normed"],
                    "calculated": row["calculated"],
                    "label": row["label"],
                    "time": row["time"],
                    "measurement_type": row["measurement_type"]["sid"],
                    "substance": row["substance"]["sid"] if row["substance"] else None,
                    "group": row["group"]["name"] if row["group"] else None,
                    "individual": row["individual"]["name"]
                    if row["individual"]
                    else None,
                }
            if entity == "interventions":
                return {"name": row["name"], "normed": row["normed"]}
            return row["name"]

        result = []
        mapping = {
            "output_pk": "outputs",
            "intervention_pk": "interventions",
            "raw_pk": "interventions",
            "group_pk": "groups",
            "group_parent_pk": "groups",
            "individual_group_pk": "groups",
            "individual_pk": "individuals",
        }
        for original in rows:
            row = {
                key: value
                for key, value in original.items()
                if key
                not in {"data_pk", "subset_pk", "data_point_pk", "characteristica_pk"}
            }
            for key, entity in mapping.items():
                if key in row:
                    value = row[key]
                    row[key] = (
                        [identity(entity, item) for item in value]
                        if isinstance(value, list)
                        else identity(entity, value)
                    )
            for key in ("curators", "substances"):
                if key in row:
                    row[key] = sorted(row[key])
            result.append(row)
        return sorted(result, key=lambda row: json.dumps(row, sort_keys=True))

    for entity, expected in analysis_golden["rows"].items():
        actual = AnalysisService(session_factory).search(
            entity,
            QuerySpec.model_validate({"entity": ENTITIES[entity], "page_size": 1000}),
            Principal(),
        )
        assert actual.count == len(actual.items) == len(expected), entity
        compare(
            stable_analysis(actual.items, actual_identities),
            stable_analysis(expected, analysis_golden["identities"]),
        )

    # Characterize a two-point scatter assembled from the same four legacy
    # Frost measurements, inside a rollback-only transaction on both backends.
    from sqlalchemy import select

    from pkdb.db.models.measurements import (
        Measurement,
        Scatter,
        Subset,
        SubsetDimension,
        SubsetPoint,
    )
    from pkdb.db.scatter_export import rows as scatter_rows
    from pkdb.schemas.filters import FilterSpec

    expected = json.loads(
        (
            Path(__file__).parents[1] / "tests/fixtures/golden/frost2014-scatter.json"
        ).read_text()
    )
    with session_factory() as session:
        measurements = list(
            session.scalars(
                select(Measurement)
                .where(
                    Measurement.origin == "normalized",
                    Measurement.label == "apixaban_mAPI",
                    Measurement.time <= 2.01,
                )
                .order_by(Measurement.time)
            )
        )
        assert len(measurements) == 4
        study_id = measurements[0].study_id
        dataset = Scatter(
            study_id=study_id,
            key="export-characterization",
            name="export-characterization",
            data_type="scatter",
        )
        session.add(dataset)
        session.flush()
        subset = Subset(
            study_id=study_id,
            key="paired-export",
            scatter_id=dataset.id,
            name="paired",
            position=0,
            dimension_labels=["x", "y"],
        )
        session.add(subset)
        session.flush()
        for offset in (0, 2):
            point = SubsetPoint(
                study_id=study_id,
                key=f"export-point-{offset}",
                subset_id=subset.id,
                position=offset // 2,
            )
            session.add(point)
            session.flush()
            for axis in (0, 1):
                session.add(
                    SubsetDimension(
                        study_id=study_id,
                        subset_id=subset.id,
                        point_id=point.id,
                        position=offset + axis,
                        dimension=str(axis),
                        measurement_id=measurements[offset + axis].id,
                    )
                )
        session.flush()
        actual = json.loads(
            json.dumps(list(scatter_rows(session, FilterSpec(), Principal()))[0])
        )
        assert list(actual) == list(expected)
        assert actual["x_data_point"] == actual["y_data_point"]
        assert len(set(actual["x_data_point"])) == 2
        for row in (actual, expected):
            for key in list(row):
                if key.endswith("_pk") or key.endswith("_data_point"):
                    del row[key]
        compare(actual, expected)
