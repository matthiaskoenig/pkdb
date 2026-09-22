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


def test_reference_read_preserves_authors_and_visibility(
    client, valid_bundle, creator_headers
):
    import json

    valid_bundle.study["access"] = "public"
    valid_bundle.reference["authors"] = [{"first_name": "First", "last_name": "Last"}]
    response = client.put(
        f"/api/v2/studies/{valid_bundle.study['sid']}",
        headers=creator_headers,
        data={
            "study": json.dumps(valid_bundle.study),
            "reference": json.dumps(valid_bundle.reference),
        },
    )
    assert response.status_code == 201
    response = client.get("/api/v1/references/")
    assert response.status_code == 200
    row = response.json()["data"]["data"][0]
    assert row["authors"][0]["first_name"] == "First"
    assert isinstance(row["authors"][0]["pk"], int)
    assert client.get(f"/api/v1/references/{row['sid']}/").json() == row
    valid_bundle.study["access"] = "private"
    response = client.put(
        f"/api/v2/studies/{valid_bundle.study['sid']}",
        headers=creator_headers,
        data={
            "study": json.dumps(valid_bundle.study),
            "reference": json.dumps(valid_bundle.reference),
        },
    )
    assert response.status_code == 200
    assert client.get("/api/v1/references/").json()["data"]["count"] == 0
    assert client.get(f"/api/v1/references/{row['sid']}/").status_code == 404


def test_scatter_subset_routes_preserve_dimension_order(
    client, valid_bundle, creator_headers
):
    import json
    from copy import deepcopy

    valid_bundle.study["access"] = "public"
    base = valid_bundle.study["outputset"]["outputs"][0]
    valid_bundle.study["outputset"]["outputs"] = [
        dict(deepcopy(base), label=label, time=time, output_type="array")
        for time in (0, 1)
        for label in ("x", "y")
    ]
    valid_bundle.study["dataset"] = {
        "data": [
            {
                "name": "figure",
                "data_type": "scatter",
                "subsets": [
                    {"name": "pairs", "dimensions": ["x", "y"], "shared": ["time"]}
                ],
            }
        ]
    }
    response = client.put(
        f"/api/v2/studies/{valid_bundle.study['sid']}",
        headers=creator_headers,
        data={
            "study": json.dumps(valid_bundle.study),
            "reference": json.dumps(valid_bundle.reference),
        },
    )
    assert response.status_code == 201
    response = client.get("/api/v1/subsets/")
    assert response.status_code == 200
    row = response.json()["data"]["data"][0]
    assert row["data_type"] == "scatter"
    assert len(row["array"]) == 2
    assert [[point["label"] for point in pair] for pair in row["array"]] == [
        ["x", "y"],
        ["x", "y"],
    ]
    assert client.get(f"/api/v1/subsets/{row['pk']}/").json() == row


def test_study_detail_contains_complete_sets_and_metadata(
    client, valid_bundle, creator_headers
):
    import json

    valid_bundle.study["access"] = "public"
    valid_bundle.study["descriptions"] = ["Study description"]
    response = client.put(
        f"/api/v2/studies/{valid_bundle.study['sid']}",
        headers=creator_headers,
        data={
            "study": json.dumps(valid_bundle.study),
            "reference": json.dumps(valid_bundle.reference),
        },
    )
    assert response.status_code == 201
    response = client.get(f"/api/v1/studies/{valid_bundle.study['sid']}/")
    assert response.status_code == 200
    row = response.json()
    assert row["reference"]["sid"] == valid_bundle.reference["sid"]
    assert row["creator"]["username"] == "curator"
    assert row["descriptions"][0]["text"] == "Study description"
    assert len(row["groupset"]["groups"]) == row["group_count"] == 1
    assert len(row["outputset"]["outputs"]) == row["output_count"] == 1
    assert row["files"] == []
    assert client.get("/api/v1/studies/").json()["data"]["data"] == [row]
    assert client.get("/api/v1/studies/missing/").status_code == 404


def test_legacy_name_and_sid_filters_are_distinct(
    client, valid_bundle, creator_headers, session_factory
):
    import json

    from pkdb.db.models.vocabulary import VocabularyNode

    with session_factory.begin() as session:
        session.get(VocabularyNode, "drug").name = "Drug display name"
    valid_bundle.study["access"] = "public"
    for section, key in (
        ("interventionset", "interventions"),
        ("outputset", "outputs"),
    ):
        for row in valid_bundle.study[section][key]:
            if row.get("substance") == "drug":
                row["substance"] = "Drug display name"
    response = client.put(
        f"/api/v2/studies/{valid_bundle.study['sid']}",
        headers=creator_headers,
        data={
            "study": json.dumps(valid_bundle.study),
            "reference": json.dumps(valid_bundle.reference),
        },
    )
    assert response.status_code == 201
    for entity in ("outputs", "interventions"):
        name_rows = client.get(
            f"/api/v1/{entity}/", params={"substance": "Drug display name"}
        ).json()["data"]
        sid_rows = client.get(
            f"/api/v1/{entity}/", params={"substance_sid": "drug"}
        ).json()["data"]
        assert name_rows["count"] > 0
        assert name_rows == sid_rows
        assert (
            client.get(f"/api/v1/{entity}/", params={"substance": "drug"}).json()[
                "data"
            ]["count"]
            == 0
        )
        assert (
            client.get(f"/api/v1/{entity}/", params={"search": "Drug display"}).json()[
                "data"
            ]["count"]
            == name_rows["count"]
        )
    for params in (
        {"creator": "curator"},
        {"reference_name": valid_bundle.reference["name"]},
        {"substance": "Drug display name"},
    ):
        response = client.get("/api/v1/studies/", params=params)
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1
    assert (
        client.get("/api/v1/studies/", params={"creator": "unknown"}).json()["data"][
            "count"
        ]
        == 0
    )


def test_subject_measurement_filter_alias(client, valid_bundle, creator_headers):
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
    response = client.get("/api/v1/groups/", params={"measurement_type_sid": "species"})
    assert response.status_code == 200
    assert response.json()["data"]["count"] == 1
    response = client.get(
        "/api/v1/groups/", params={"measurement_type_sid__exclude": "species"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["count"] == 0
