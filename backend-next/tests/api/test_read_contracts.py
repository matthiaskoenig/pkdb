def test_public_output_pagination_and_statistics(client, valid_bundle, creator_headers):
    valid_bundle.study["access"] = "public"
    response = client.put(
        f"/api/v2/studies/{valid_bundle.study['sid']}",
        headers=creator_headers,
        data={
            "study": __import__("json").dumps(valid_bundle.study),
            "reference": __import__("json").dumps(valid_bundle.reference),
        },
    )
    assert response.status_code == 201
    response = client.get("/api/v1/outputs/", params={"page_size": 1})
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {
        "current_page",
        "last_page",
        "next_page_url",
        "prev_page_url",
        "data",
    }
    assert data["current_page"] == 1
    assert data["data"]["count"] >= 2
    assert len(data["data"]["data"]) == 1
    assert data["next_page_url"]
    assert data["prev_page_url"] is None
    record = data["data"]["data"][0]
    assert client.get(f"/api/v1/outputs/{record['pk']}/").json() == record
    assert client.get("/api/v1/statistics/").json()["study_count"] == 1
    assert client.get("/api/v1/outputs/", params={"page": -1}).status_code == 400
    assert (
        client.get("/api/v1/outputs/", params={"substance__delete": "x"}).status_code
        == 400
    )


def test_output_filters_do_not_expose_private_counts(
    client, valid_bundle, creator_headers
):
    import json

    valid_bundle.study["access"] = "private"
    response = client.put(
        f"/api/v2/studies/{valid_bundle.study['sid']}",
        headers=creator_headers,
        data={
            "study": json.dumps(valid_bundle.study),
            "reference": json.dumps(valid_bundle.reference),
        },
    )
    assert response.status_code == 201
    assert client.get("/api/v1/outputs/").json()["data"]["count"] == 0
    assert client.get("/api/v1/statistics/").json()["output_count"] == 0
    assert (
        client.get("/api/v1/outputs/", headers=creator_headers).json()["data"]["count"]
        > 0
    )


def test_group_and_individual_routes(client, valid_bundle, creator_headers):
    import json

    valid_bundle.study["access"] = "public"
    response = client.put(
        f"/api/v2/studies/{valid_bundle.study['sid']}",
        headers=creator_headers,
        data={
            "study": json.dumps(valid_bundle.study),
            "reference": json.dumps(valid_bundle.reference),
        },
    )
    assert response.status_code == 201
    response = client.get("/api/v1/groups/")
    assert response.status_code == 200
    row = response.json()["data"]["data"][0]
    assert row["name"] == "all"
    assert client.get(f"/api/v1/groups/{row['pk']}/").json() == row
    assert client.get("/api/v1/individuals/").json()["data"]["count"] == 0


def test_intervention_routes(client, valid_bundle, creator_headers):
    import json

    valid_bundle.study["access"] = "public"
    response = client.put(
        f"/api/v2/studies/{valid_bundle.study['sid']}",
        headers=creator_headers,
        data={
            "study": json.dumps(valid_bundle.study),
            "reference": json.dumps(valid_bundle.reference),
        },
    )
    assert response.status_code == 201
    response = client.get("/api/v1/interventions/", params={"normed": "true"})
    assert response.status_code == 200
    row = response.json()["data"]["data"][0]
    assert row["normed"]
    assert row["name"] == "dose"
    assert client.get(f"/api/v1/interventions/{row['pk']}/").json() == row
