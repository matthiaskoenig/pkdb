"""Scientific scope guarantees consumed by the modern frontend."""

import csv
from io import BytesIO, StringIO
from zipfile import ZipFile

import pytest

from tests.fixtures.frontend_search import (
    add_frontend_vocabulary,
    frontend_search_bundle,
    publish_frontend_fixture,
)


@pytest.fixture
def vocabulary(vocabulary):
    """The controlled vocabulary plus the parameters derived from timecourses."""
    from pkdb.domain.vocabulary import MeasurementRule

    derived = tuple(
        MeasurementRule(name=name, units=(unit,))
        for name, unit in [
            ("auc_end", "mg*h/l"),
            ("auc_inf", "mg*h/l"),
            ("cmax", "mg/l"),
            ("kel", "1/h"),
            ("thalf", "h"),
            ("tmax", "h"),
        ]
    )
    # The vocabulary spells the choice of the species as the complete one does.
    measurements = tuple(
        rule.model_copy(update={"choices": ("homo sapiens",)})
        if rule.name == "species"
        else rule
        for rule in vocabulary.measurements
    )
    return vocabulary.model_copy(update={"measurements": measurements + derived})


@pytest.fixture
def scientific_fixture(ingestion_context, session_factory):
    ingestion, creator = ingestion_context
    with session_factory.begin() as session:
        add_frontend_vocabulary(session)

    def install(related=False):
        from sqlalchemy import update

        from pkdb_server.db.models.studies import Study

        with session_factory.begin() as session:
            session.execute(
                update(Study)
                .where(Study.sid == "FRONTEND_SCOPE")
                .values(access="private")
            )
        ingestion.replace(frontend_search_bundle(related=related), creator)
        with session_factory.begin() as session:
            publish_frontend_fixture(session)

    install()
    return install


def selection(client, **params):
    response = client.get("/api/v1/filter/", params={"format": "json", **params})
    assert response.status_code == 200, response.text
    return response.json()


def test_joint_match_differs_from_qualifying_study(client, scientific_fixture):
    criteria = {"interventions__route": "oral", "outputs__substance": "drug-b"}
    matching = selection(client, concise="true", **criteria)
    broader = selection(client, concise="false", **criteria)
    assert matching["studies"] == matching["outputs"] == 0
    assert broader["studies"] == 1
    assert broader["outputs"] == broader["interventions"] == 2


def test_related_interventions_are_context_not_direct_matches(
    client, scientific_fixture
):
    scientific_fixture(related=True)
    selected = selection(
        client, concise="true", interventions__route="oral", outputs__substance="drug-b"
    )
    assert selected["studies"] == selected["outputs"] == 1
    assert selected["interventions"] == 2
    rows = client.get(
        "/api/v1/interventions/", params={"uuid": selected["uuid"]}
    ).json()["data"]
    assert rows["count"] == 2
    assert {row["name"] for row in rows["data"]} == {"oral-A", "iv-B"}


def test_intervention_predicates_must_match_same_record(client, scientific_fixture):
    selected = selection(
        client, interventions__route="oral", interventions__substance="drug-b"
    )
    assert selected["studies"] == selected["outputs"] == 0


def test_disabled_subjects_and_types_do_not_broaden_selection(
    client, scientific_fixture
):
    for criteria in [
        {"groups__id__in": "0", "individuals__id__in": "0"},
        {"outputs__id__in": "0"},
    ]:
        selected = selection(client, **criteria)
        assert selected["studies"] == selected["outputs"] == 0


def test_entity_count_and_export_preserve_zero_and_precision(
    client, scientific_fixture, creator_headers
):
    selected = selection(client)
    response = client.get(
        "/api/v1/outputs/", params={"uuid": selected["uuid"], "page_size": 1}
    )
    assert response.status_code == 200
    page = response.json()
    assert page["data"]["count"] == selected["outputs"] == 2
    assert page["last_page"] == 2
    assert (
        client.get(
            "/api/v1/outputs/", params={"uuid": selected["uuid"], "page": 99}
        ).status_code
        == 404
    )
    downloaded = client.get(
        "/api/v1/filter/", headers=creator_headers, params={"download": "true"}
    )
    assert downloaded.status_code == 200
    with ZipFile(BytesIO(downloaded.content)) as archive:
        rows = list(csv.DictReader(StringIO(archive.read("outputs.csv").decode())))
        assert {row["study_sid"] for row in rows} == {"FRONTEND_SCOPE"}
        assert {float(row["mean"]) for row in rows} == {0.0, 2.125}
        assert {row["unit"] for row in rows} == {"mg/l"}


def test_subject_union_inheritance_and_all_toggle_combinations(
    client, scientific_fixture, session_factory
):
    from sqlalchemy import select

    from pkdb_server.db.models.measurements import Measurement
    from pkdb_server.db.models.subjects import Group, Individual

    with session_factory.begin() as session:
        group = session.scalar(select(Group))
        person = Individual(
            study_id=group.study_id, key="person", name="person", group_id=group.id
        )
        session.add(person)
        session.flush()
        session.add(
            Measurement(
                study_id=group.study_id,
                key="individual-normalized",
                individual_id=person.id,
                measurement_type="concentration",
                substance="drug",
                mean=1.5,
                unit="mg/l",
                origin="normalized",
            )
        )
    for groups, individuals, expected in [
        (True, True, 3),
        (True, False, 2),
        (False, True, 1),
        (False, False, 0),
    ]:
        criteria = {}
        if not groups:
            criteria["groups__id__in"] = "0"
        if not individuals:
            criteria["individuals__id__in"] = "0"
        assert selection(client, **criteria)["outputs"] == expected
    # Both predicates must resolve on the same effective characteristic row.
    for measurement, choice, expected in [("sex", "NR", 3), ("species", "NR", 0)]:
        criteria = {
            f"{entity}__characteristics.{field}": value
            for entity in ("groups", "individuals")
            for field, value in [("measurement_type", measurement), ("choice", choice)]
        }
        selected = selection(client, **criteria)
        assert selected["outputs"] == expected


def test_licence_and_visibility_rechecked_for_existing_selection(
    client, scientific_fixture, session_factory
):
    from sqlalchemy import update

    from pkdb_server.db.models.studies import Study

    selected = selection(client)
    assert selected["studies"] == 1
    assert selection(client, studies__licence__in="0")["studies"] == 0
    assert selection(client, studies__licence__in="open")["studies"] == 1
    assert selection(client, studies__licence__in="closed")["studies"] == 0
    with session_factory.begin() as session:
        session.execute(update(Study).values(access="private"))
    rows = client.get("/api/v1/outputs/", params={"uuid": selected["uuid"]})
    assert rows.status_code == 200
    assert rows.json()["data"]["count"] == 0
    assert selection(client)["studies"] == 0


def test_table_refinement_does_not_change_selection_counts_or_export(
    client, scientific_fixture, creator_headers
):
    selected = selection(client)
    refined = client.get(
        "/api/v1/studies/",
        params={
            "uuid": selected["uuid"],
            "search_multi_match": "definitely-no-such-study",
        },
    )
    assert refined.status_code == 200
    assert refined.json()["data"]["count"] == 0
    assert selected["studies"] == 1
    exported = client.get(
        "/api/v1/filter/", headers=creator_headers, params={"download": "true"}
    )
    with ZipFile(BytesIO(exported.content)) as archive:
        assert (
            len(list(csv.DictReader(StringIO(archive.read("studies.csv").decode()))))
            == 1
        )


def test_selected_subsets_preserve_nonmatching_point_context(
    client, scientific_fixture, session_factory
):
    from tests.fixtures.frontend_search import add_frontend_plot_context

    with session_factory.begin() as session:
        add_frontend_plot_context(session)
    selected = selection(client, outputs__substance="drug")
    assert selected["outputs"] == selected["timecourses"] == selected["scatters"] == 1
    for kind, width in [("timecourse", 1), ("scatter", 2)]:
        response = client.get(
            "/api/v1/subsets/", params={"uuid": selected["uuid"], "data_type": kind}
        )
        assert response.status_code == 200, response.text
        rows = response.json()["data"]
        assert rows["count"] == 1
        array = rows["data"][0]["array"]
        assert all(len(point) == width for point in array)
        assert {point["mean"] for pair in array for point in pair} == {0.0, 2.125}


def test_output_type_toggles_select_only_normalized_records(
    client, scientific_fixture, session_factory
):
    from sqlalchemy import select

    from pkdb_server.db.models.measurements import Measurement
    from pkdb_server.db.models.subjects import Group

    with session_factory.begin() as session:
        group = session.scalar(select(Group))
        for kind in ("timecourse", "array"):
            for origin in ("reported", "normalized", "calculated"):
                session.add(
                    Measurement(
                        study_id=group.study_id,
                        key=f"{kind}-{origin}",
                        group_id=group.id,
                        measurement_type="concentration",
                        substance="drug",
                        mean=1.25,
                        unit="mg/l",
                        output_type=kind,
                        origin=origin,
                    )
                )
    assert selection(client)["outputs"] == 4
    for kind, count in [
        ("output", 2),
        ("timecourse", 1),
        ("array", 1),
        ("timecourse__array", 2),
        ("0", 0),
    ]:
        assert selection(client, outputs__output_type__in=kind)["outputs"] == count


def test_expired_uuid_is_distinct_from_empty_selection(
    client, scientific_fixture, session_factory
):
    from datetime import UTC, datetime, timedelta
    from uuid import UUID

    from pkdb_server.db.models.saved_queries import SavedQuery

    selected = selection(client)
    with session_factory.begin() as session:
        session.get(SavedQuery, UUID(selected["uuid"])).expires_at = datetime.now(
            UTC
        ) - timedelta(seconds=1)
    expired = client.get("/api/v1/studies/", params={"uuid": selected["uuid"]})
    assert expired.status_code == 404
    assert expired.json()["detail"] == "Saved filter unavailable"
    empty = selection(client, studies__sid="missing")
    response = client.get("/api/v1/studies/", params={"uuid": empty["uuid"]})
    assert response.status_code == 200
    assert response.json()["data"]["count"] == 0


@pytest.mark.parametrize("concise,expected", [("true", set()), ("false", {0.0, 2.125})])
def test_compound_scope_zip_parity(
    client, scientific_fixture, concise, expected, creator_headers
):
    response = client.get(
        "/api/v1/filter/",
        headers=creator_headers,
        params={
            "download": "true",
            "concise": concise,
            "interventions__route": "oral",
            "outputs__substance": "drug-b",
        },
    )
    assert response.status_code == 200
    with ZipFile(BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {
            f"{entity}.csv"
            for entity in (
                "studies",
                "groups",
                "individuals",
                "interventions",
                "outputs",
                "timecourses",
                "scatters",
                "info_nodes",
            )
        } | {"README.md", "TERMS_OF_USE.md"}
        rows = list(csv.DictReader(StringIO(archive.read("outputs.csv").decode())))
        assert {float(row["mean"]) for row in rows} == expected
        assert all(row["study_sid"] == "FRONTEND_SCOPE" for row in rows)


@pytest.fixture
def format2_study(ingestion_context, session_factory, tmp_path):
    from tests.fixtures.frontend_search import (
        add_frontend_vocabulary,
        write_frontend_format2_study,
    )

    ingestion, creator = ingestion_context
    with session_factory.begin() as session:
        add_frontend_vocabulary(session)
    folder = write_frontend_format2_study(tmp_path / "sources")
    ingestion.replace(folder, creator)
    return folder


def test_format2_fixture_carries_the_fields_the_study_page_shows(
    client, creator_headers, format2_study
):
    from tests.fixtures.frontend_search import (
        FORMAT2_ISSUE,
        FORMAT2_PKDB_ID,
        FORMAT2_SID,
    )

    study = client.get(f"/api/v1/studies/{FORMAT2_SID}/", headers=creator_headers)
    assert study.status_code == 200, study.text
    assert {
        key: study.json()[key]
        for key in (
            "sid",
            "pkdb_id",
            "release_date",
            "issue",
            "review_status",
            "open_review_items",
        )
    } == {
        "sid": FORMAT2_SID,
        "pkdb_id": FORMAT2_PKDB_ID,
        "release_date": "2026-09-28",
        "issue": FORMAT2_ISSUE,
        "review_status": "in_review",
        "open_review_items": 1,
    }
    # A private study is neither served nor revealed by its PKDB identifier.
    assert client.get(f"/api/v1/studies/{FORMAT2_SID}/").status_code == 404
    assert client.get(f"/api/v1/studies/{FORMAT2_PKDB_ID}/").status_code == 404
    moved = client.get(
        f"/api/v1/studies/{FORMAT2_PKDB_ID}/",
        headers=creator_headers,
        follow_redirects=False,
    )
    assert moved.status_code == 308
    assert moved.headers["location"] == f"/api/v1/studies/{FORMAT2_SID}/"


def test_format2_fixture_has_schedules_geometric_statistics_and_labels(
    client, creator_headers, format2_study
):
    from tests.fixtures.frontend_search import FORMAT2_SID

    def rows(entity, **params):
        response = client.get(
            f"/api/v1/{entity}/",
            headers=creator_headers,
            params={"study_sid": FORMAT2_SID, **params},
        )
        assert response.status_code == 200, response.text
        return response.json()["data"]["data"]

    schedules = {
        row["name"]: {
            key: row[key] for key in ("time", "interval", "doses", "time_unit")
        }
        for row in rows("interventions", normed="true")
    }
    assert schedules == {
        "D1": {"time": 0.0, "interval": 24.0, "doses": 7, "time_unit": "h"},
        "D2": {
            "time": [0.0, 12.0, 40.0],
            "interval": None,
            "doses": None,
            "time_unit": "h",
        },
    }
    outputs = rows("outputs", normed="true")
    geometric = {
        (row["gmean"], row["time"]): row for row in outputs if row["gmean"] is not None
    }
    # The reported geometric statistics are kept and the other one is derived.
    assert geometric[4.0, 2.0]["gsd"] == 1.5
    assert geometric[4.0, 2.0]["gcv"] == pytest.approx(0.4227, abs=1e-4)
    assert geometric[3.0, 4.0]["gcv"] == pytest.approx(0.5)
    assert geometric[3.0, 4.0]["gsd"] == pytest.approx(1.6038, abs=1e-4)
    assert not any("value" in row for row in outputs)
    series = {
        point["label"]
        for subset in rows("subsets", data_type="timecourse")
        for pair in subset["array"]
        for point in pair
    }
    assert series == {
        "Plasma after 10 mg daily (geometric)",
        "Plasma after 10 mg daily (arithmetic)",
    }


def test_value_ordering_uses_the_mean_else_the_median_else_the_geometric_mean(
    client, creator_headers, format2_study
):
    from tests.fixtures.frontend_search import FORMAT2_SID

    def values(entity, ordering):
        response = client.get(
            f"/api/v1/{entity}/",
            headers=creator_headers,
            params={
                "study_sid": FORMAT2_SID,
                "normed": "true",
                "ordering": ordering,
                "page_size": 100,
            },
        )
        assert response.status_code == 200, response.text
        return [
            next(
                (
                    row[key]
                    for key in ("mean", "median", "gmean")
                    if row[key] is not None
                ),
                None,
            )
            for row in response.json()["data"]["data"]
        ]

    outputs = values("outputs", "central_value")
    reported = [value for value in outputs if value is not None]
    # Rows with a mean and rows with a geometric mean take part in one order.
    assert len(set(reported)) > 3
    assert reported == sorted(reported)
    assert outputs[: len(reported)] == reported
    descending = values("outputs", "-central_value")
    assert [value for value in descending if value is not None] == sorted(
        reported, reverse=True
    )
    assert values("interventions", "central_value") == sorted(
        values("interventions", "central_value")
    )
    assert values("interventions", "-central_value") == sorted(
        values("interventions", "central_value"), reverse=True
    )
