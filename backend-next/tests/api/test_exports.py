import json
from copy import deepcopy


def test_analysis_pagination_counts_expanded_pairs(
    client, creator_headers, valid_bundle
):
    valid_bundle.study["access"] = "public"
    intervention = deepcopy(valid_bundle.study["interventionset"]["interventions"][0])
    intervention["name"] = "second"
    valid_bundle.study["interventionset"]["interventions"].append(intervention)
    valid_bundle.study["outputset"]["outputs"][0]["interventions"] = ["dose", "second"]
    response = client.put(
        f"/api/v2/studies/{valid_bundle.study['sid']}",
        headers=creator_headers,
        data={
            "study": json.dumps(valid_bundle.study),
            "reference": json.dumps(valid_bundle.reference),
        },
    )
    assert response.status_code == 201
    response = client.get("/api/v1/pkdata/outputs/", params={"page_size": 1})
    assert response.status_code == 200
    page = response.json()
    assert page["data"]["count"] == 4
    assert len(page["data"]["data"]) == 1
    assert page["last_page"] == 4
    row = page["data"]["data"][0]
    assert row["study_sid"] == valid_bundle.study["sid"]
    assert row["measurement_type"] == "concentration"
    assert row["intervention_pk"] > 0
    assert row["group_pk"] > 0
    assert row["individual_pk"] is None
    for entity in ("studies", "groups", "interventions"):
        response = client.get(f"/api/v1/pkdata/{entity}/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] > 0
    for entity in ("individuals", "timecourses", "data"):
        response = client.get(f"/api/v1/pkdata/{entity}/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 0


def test_saved_filter_scopes_public_and_analysis_reads(
    client, creator_headers, valid_bundle
):
    response = client.put(
        f"/api/v2/studies/{valid_bundle.study['sid']}",
        headers=creator_headers,
        data={
            "study": json.dumps(valid_bundle.study),
            "reference": json.dumps(valid_bundle.reference),
        },
    )
    assert response.status_code == 201
    response = client.get("/api/v1/filter/", headers=creator_headers)
    assert response.status_code == 200
    saved = response.json()
    assert (
        saved["studies"]
        == saved["groups"]
        == saved["interventions"]
        == saved["outputs"]
        == 1
    )
    for path in ("outputs", "pkdata/outputs"):
        response = client.get(
            f"/api/v1/{path}/", headers=creator_headers, params={"uuid": saved["uuid"]}
        )
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1
        response = client.get(f"/api/v1/{path}/", params={"uuid": saved["uuid"]})
        assert response.status_code == 403
    empty = client.get(
        "/api/v1/filter/",
        headers=creator_headers,
        params={"outputs__substance": "missing"},
    )
    assert empty.status_code == 200
    assert empty.json()["studies"] == empty.json()["outputs"] == 0
    response = client.get(
        "/api/v1/studies/",
        headers=creator_headers,
        params={"uuid": empty.json()["uuid"]},
    )
    assert response.status_code == 200
    assert response.json()["data"]["count"] == 0


def test_legacy_zip_download_members_and_normalized_rows(
    client, creator_headers, valid_bundle
):
    import csv
    from io import BytesIO, StringIO
    from zipfile import ZipFile

    response = client.put(
        f"/api/v2/studies/{valid_bundle.study['sid']}",
        headers=creator_headers,
        data={
            "study": json.dumps(valid_bundle.study),
            "reference": json.dumps(valid_bundle.reference),
        },
    )
    assert response.status_code == 201
    response = client.get(
        "/api/v1/filter/", headers=creator_headers, params={"download": "true"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-zip-compressed"
    assert response.headers["content-disposition"] == "attachment; filename=pkdata.zip"
    with ZipFile(BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {
            f"{name}.csv"
            for name in (
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
        outputs = list(csv.DictReader(StringIO(archive.read("outputs.csv").decode())))
        assert len(outputs) == 1
        assert outputs[0]["normed"] == "True"
        assert outputs[0]["study_sid"] == valid_bundle.study["sid"]
        assert archive.read("scatters.csv") == b'""\n'
        nodes = list(csv.DictReader(StringIO(archive.read("info_nodes.csv").decode())))
        assert nodes and set(nodes[0]) == {"", "sid", "label", "ntype"}
        assert archive.read("README.md")


def test_export_releases_capacity_when_headers_cannot_be_sent():
    import asyncio

    import pytest

    from pkdb.api.exports import download_response

    class Service:
        closed = False

        def stream_export(self, *args):
            try:
                yield b"archive"
            finally:
                self.closed = True

    service = Service()
    response = download_response(service, None, None)

    async def send(message):
        raise OSError("client disconnected before headers")

    async def receive():
        return {"type": "http.disconnect"}

    with pytest.raises(Exception):
        asyncio.run(
            response({"type": "http", "asgi": {"spec_version": "2.4"}}, receive, send)
        )
    assert service.closed


def test_export_limit_and_capacity_errors_precede_headers(client, creator_headers):
    service = client.app.state.exports
    service.max_bytes = 1
    response = client.get(
        "/api/v1/filter/", headers=creator_headers, params={"download": "true"}
    )
    assert response.status_code == 413
    assert response.headers["content-type"].startswith("application/json")
    service.max_bytes = 1_000_000
    assert service.slots.acquire(blocking=False)
    assert service.slots.acquire(blocking=False)
    try:
        response = client.get(
            "/api/v1/filter/", headers=creator_headers, params={"download": "true"}
        )
        assert response.status_code == 503
        assert response.headers["retry-after"] == "1"
    finally:
        service.slots.release()
        service.slots.release()
    response = client.get(
        "/api/v1/filter/", headers=creator_headers, params={"download": "true"}
    )
    assert response.status_code == 200


def test_subject_analysis_distinguishes_measurement_sid_from_name(
    client, creator_headers, valid_bundle
):
    from sqlalchemy import update

    from pkdb.db.models.vocabulary import VocabularyNode

    response = client.put(
        f"/api/v2/studies/{valid_bundle.study['sid']}",
        headers=creator_headers,
        data={
            "study": json.dumps(valid_bundle.study),
            "reference": json.dumps(valid_bundle.reference),
        },
    )
    assert response.status_code == 201
    with client.app.state.session_factory.begin() as session:
        session.execute(
            update(VocabularyNode)
            .where(VocabularyNode.sid == "species")
            .values(name="Species display")
        )
    for field, value in [
        ("measurement_type_sid", "species"),
        ("measurement_type", "Species display"),
    ]:
        response = client.get(
            "/api/v1/pkdata/groups/", headers=creator_headers, params={field: value}
        )
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1


def test_frontend_json_format_parameter_is_transport_metadata(client):
    for path in ("filter", "studies", "outputs", "info_nodes", "pkdata/groups"):
        response = client.get(f"/api/v1/{path}/", params={"format": "json"})
        assert response.status_code == 200, (path, response.text)


def test_frontend_multi_match_search_alias_filters_study_membership(
    client, creator_headers, valid_bundle
):
    response = client.put(
        f"/api/v2/studies/{valid_bundle.study['sid']}",
        headers=creator_headers,
        data={
            "study": json.dumps(valid_bundle.study),
            "reference": json.dumps(valid_bundle.reference),
        },
    )
    assert response.status_code == 201
    for term, count in [("Example", 1), ("unmatchedstudyname", 0)]:
        response = client.get(
            "/api/v1/studies/",
            headers=creator_headers,
            params={"format": "json", "search_multi_match": term},
        )
        assert response.status_code == 200
        assert response.json()["data"]["count"] == count
