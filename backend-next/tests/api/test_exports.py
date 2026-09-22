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
