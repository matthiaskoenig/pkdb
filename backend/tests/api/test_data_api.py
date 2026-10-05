"""The public interface preserves scientific selection and access controls."""

import io
import json
import zipfile

import pytest


def upload(client, bundle, headers, *, public=True):
    bundle.study["access"] = "public" if public else "private"
    response = client.put(
        f"/api/v2/studies/{bundle.study['sid']}",
        headers=headers,
        data={
            "study": json.dumps(bundle.study),
            "reference": json.dumps(bundle.reference),
        },
    )
    assert response.status_code == 201, response.text


def test_simple_discovery_and_paging(client, valid_bundle, admin_headers):
    upload(client, valid_bundle, admin_headers)
    studies = client.get("/api/v2/studies", params={"substance": "drug"})
    assert studies.status_code == 200, studies.text
    assert studies.json()["total"] == 1
    sid = valid_bundle.study["sid"]
    response = client.get(
        "/api/v2/measurements",
        params={
            "study_sid": sid,
            "substance": "drug",
            "measurement_type": "concentration",
            "page_size": 1,
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert set(data) == {"items", "total", "page", "page_size", "next", "previous"}
    assert data["total"] >= 2
    assert data["page"] == 1 and data["page_size"] == 1
    assert data["next"] == 2 and data["previous"] is None
    second = client.get(
        "/api/v2/measurements", params={"page_size": 1, "page": 2}
    ).json()
    assert second["previous"] == 1
    assert second["items"][0]["pk"] != data["items"][0]["pk"]


STATISTICS = {"mean", "median", "sd", "se", "cv", "gmean", "gsd", "gcv"}


def test_responses_carry_mean_and_geometric_statistics_without_value(
    client, valid_bundle, admin_headers
):
    output = valid_bundle.study["outputset"]["outputs"][0]
    output["gmean"] = 1.9
    intervention = valid_bundle.study["interventionset"]["interventions"][0]
    intervention.update(time="S0T12R3", subject="all")
    upload(client, valid_bundle, admin_headers)

    def items(entity):
        response = client.post(
            "/api/v2/query", json={"entity": entity, "page_size": 100}
        )
        assert response.status_code == 200, response.text
        return response.json()["items"]

    measurements = client.get("/api/v2/measurements").json()["items"]
    assert measurements
    for row in measurements:
        assert "value" not in row
        assert STATISTICS | {"error_bar", "error_type"} <= row.keys()
    reported = next(row for row in measurements if not row["normed"])
    assert (reported["mean"], reported["gmean"]) == (2.0, 1.9)
    doses = items("interventions")
    assert doses
    for row in doses:
        assert "value" not in row
        assert row["mean"] == 10.0
        assert (row["time"], row["interval"], row["doses"]) == (0.0, 12.0, 3)
        assert row["subject"]["name"] == "all"
    groups = items("groups")
    for characteristic in groups[0]["characteristica"]:
        assert "value" not in characteristic
        assert STATISTICS <= characteristic.keys()


def test_responses_carry_the_context_of_characteristics_and_interventions(
    client, valid_bundle, admin_headers
):
    intervention = valid_bundle.study["interventionset"]["interventions"][0]
    intervention.update(tissue="plasma", method="LC-MS")
    valid_bundle.study["groupset"]["groups"][0]["characteristica"].append(
        {
            "measurement_type": "concentration",
            "substance": "drug",
            "tissue": "plasma",
            "method": "LC-MS",
            "time": 1.5,
            "time_unit": "h",
            "mean": 2.0,
            "unit": "mg/l",
        }
    )
    upload(client, valid_bundle, admin_headers)

    def items(entity):
        response = client.post(
            "/api/v2/query", json={"entity": entity, "page_size": 100}
        )
        assert response.status_code == 200, response.text
        return response.json()["items"]

    doses = items("interventions")
    assert doses
    for row in doses:
        assert (row["tissue"]["name"], row["method"]["name"]) == ("plasma", "LC-MS")
    [group] = items("groups")
    contexts = {
        (
            row["measurement_type"]["name"],
            row["tissue"] and row["tissue"]["name"],
            row["method"] and row["method"]["name"],
            row["time"],
            row["time_unit"],
        )
        for row in group["characteristica"]
    }
    assert ("concentration", "plasma", "LC-MS", 1.5, "h") in contexts
    assert ("species", None, None, None, None) in contexts
    rows = client.get("/api/v1/pkdata/interventions/").json()["data"]["data"]
    assert rows
    for row in rows:
        assert (row["tissue"], row["tissue_label"]) == ("plasma", "plasma")
        assert (row["method"], row["method_label"]) == ("LC-MS", "LC-MS")
    rows = client.get("/api/v1/pkdata/groups/").json()["data"]["data"]
    assert {
        (
            row["measurement_type"],
            row["tissue"],
            row["method"],
            row["time"],
            row["time_unit"],
        )
        for row in rows
        if row["measurement_type"] == "concentration"
    } == {("concentration", "plasma", "LC-MS", 1.5, "h")}


def test_intervention_time_lists_are_numbers(client, valid_bundle, admin_headers):
    intervention = valid_bundle.study["interventionset"]["interventions"][0]
    intervention["time"] = "0|12|40"
    upload(client, valid_bundle, admin_headers)
    response = client.post("/api/v2/query", json={"entity": "interventions"})
    assert response.status_code == 200, response.text
    assert [row["time"] for row in response.json()["items"]] == [
        [0.0, 12.0, 40.0],
        [0.0, 12.0, 40.0],
    ]


@pytest.mark.parametrize(
    "field,total", [("mean", 2), ("gmean", 2), ("gsd", 2), ("gcv", 1), ("se", 0)]
)
def test_statistic_filters_use_mean_and_geometric_fields(
    client, valid_bundle, admin_headers, field, total
):
    valid_bundle.study["outputset"]["outputs"][0].update(gmean=1.9, gsd=1.2)
    upload(client, valid_bundle, admin_headers)
    response = client.post(
        "/api/v2/query",
        json={
            "entity": "measurements",
            "predicates": [{"field": field, "operator": "isnull", "value": False}],
        },
    )
    assert response.status_code == 200, response.text
    # The normalized representation derives gcv from the reported gsd.
    assert response.json()["total"] == total
    value_filter = client.post(
        "/api/v2/query",
        json={
            "entity": "measurements",
            "predicates": [{"field": "value", "operator": "gte", "value": 1}],
        },
    )
    assert value_filter.status_code == 400


def test_query_alias_and_same_measurement_scope(client, valid_bundle, admin_headers):
    upload(client, valid_bundle, admin_headers)
    query = {
        "entity": "measurements",
        "predicates": [{"field": "study_sid", "value": valid_bundle.study["sid"]}],
    }
    response = client.post("/api/v2/query", json=query)
    assert response.status_code == 200, response.text
    assert response.json() == client.get("/api/v2/measurements").json()
    # Both constraints must hold on one row, never on different rows.
    response = client.post(
        "/api/v2/query",
        json={
            "entity": "studies",
            "predicates": [
                {"field": "measurements.substance", "value": "drug"},
                {"field": "measurements.substance", "value": "other"},
            ],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 0


def test_counts_and_exports_preserve_private_visibility(
    client, valid_bundle, creator_headers
):
    upload(client, valid_bundle, creator_headers, public=False)
    assert client.get("/api/v2/studies").json()["total"] == 0
    assert (
        client.post("/api/v2/query", json={"entity": "measurements"}).json()["total"]
        == 0
    )
    assert client.get("/api/v2/studies", headers=creator_headers).json()["total"] == 1
    assert client.post("/api/v2/exports", json={}).status_code == 401
    response = client.post(
        "/api/v2/exports",
        headers=creator_headers,
        json={
            "queries": {
                "studies": {
                    "entity": "studies",
                    "predicates": [
                        {"field": "sid", "value": valid_bundle.study["sid"]}
                    ],
                }
            }
        },
    )
    assert response.status_code == 200, response.text
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert "outputs.csv" in archive.namelist()
        assert valid_bundle.study["sid"] in archive.read("studies.csv").decode()
        assert "TERMS_OF_USE.md" in archive.namelist()


@pytest.mark.parametrize(
    "params",
    [{"page": 0}, {"page_size": 1001}, {"unexpected": "value"}, {"substance": ""}],
)
def test_invalid_simple_parameters(client, params):
    assert client.get("/api/v2/studies", params=params).status_code == 422


@pytest.mark.parametrize(
    "query",
    [
        {"entity": "studies", "sort": "sid; DROP TABLE study"},
        {"entity": "measurements", "predicates": [{"field": "unknown", "value": "x"}]},
        {
            "entity": "measurements",
            "predicates": [{"field": "mean", "value": "not numeric"}],
        },
    ],
)
def test_unsafe_query_fields_are_rejected(client, query):
    assert client.post("/api/v2/query", json=query).status_code == 400


def test_injection_text_is_treated_as_a_value(client, valid_bundle, admin_headers):
    upload(client, valid_bundle, admin_headers)
    response = client.get("/api/v2/studies", params={"study_sid": "' OR 1=1 --"})
    assert response.status_code == 200 and response.json()["total"] == 0
    assert client.get("/api/v2/studies").json()["total"] == 1


def test_export_filter_validation(client, creator_headers):
    response = client.post(
        "/api/v2/exports",
        headers=creator_headers,
        json={
            "queries": {
                "studies": {
                    "entity": "studies",
                    "predicates": [{"field": "nope", "value": "x"}],
                }
            }
        },
    )
    assert response.status_code == 400
    response = client.post(
        "/api/v2/exports",
        headers=creator_headers,
        json={"queries": {"studies": {"entity": "outputs"}}},
    )
    assert response.status_code == 422


def test_documented_examples_against_seeded_database(
    client, valid_bundle, creator_headers, tmp_path
):
    import runpy
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    upload(client, valid_bundle, creator_headers)
    run_examples = runpy.run_path(str(root / "tools/api_examples/example.py"))[
        "run_examples"
    ]
    client.headers.update(creator_headers)
    summary = run_examples(
        client, tmp_path, substance="drug", study_sid=valid_bundle.study["sid"]
    )
    expected = json.loads(
        (root / "tools/api_examples/expected-fixture.json").read_text()
    )
    assert summary == expected
    assert json.loads((tmp_path / "summary.json").read_text()) == expected


def test_data_endpoints_require_read_scope_for_api_keys(client, session_factory):
    from pkdb_server.db.models.users import User
    from tests.api.test_upload_visibility import key_for

    with session_factory.begin() as session:
        user = User(username="write-only-reader", role="user", active=True)
        session.add(user)
        session.flush()
        headers = key_for(session, user, scopes=("studies:write",))
    assert client.get("/api/v2/studies", headers=headers).status_code == 403
    assert client.get("/api/v2/measurements", headers=headers).status_code == 403
    assert (
        client.post(
            "/api/v2/query", headers=headers, json={"entity": "studies"}
        ).status_code
        == 403
    )
    assert client.post("/api/v2/exports", headers=headers, json={}).status_code == 403


def test_statistics_overview_contract_and_private_access(
    client, valid_bundle, creator_headers
):
    upload(client, valid_bundle, creator_headers, public=False)
    public = client.get("/api/v2/statistics")
    assert public.status_code == 200, public.text
    assert public.json()["counts"]["study_count"] == 0
    assert public.json()["years"] == []
    response = client.get("/api/v2/statistics", headers=creator_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["date_basis"] == "study.date"
    assert data["generated_at"]
    assert data["counts"]["study_count"] == 1
    legacy = client.get("/api/v1/statistics/", headers=creator_headers).json()
    for key, value in legacy.items():
        if key != "version":
            assert data["counts"][key] == value
    assert (
        sum(row["study_count"] for row in data["years"])
        + data["undated"]["study_count"]
        == 1
    )
