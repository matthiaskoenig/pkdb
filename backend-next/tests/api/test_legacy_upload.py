from copy import deepcopy


def test_legacy_draft_is_invisible_until_finalization(
    client, creator_headers, valid_bundle
):
    study = deepcopy(valid_bundle.study)
    study["access"] = "public"
    sections = {
        key: study.pop(key, None)
        for key in (
            "groupset",
            "interventionset",
            "individualset",
            "outputset",
            "dataset",
        )
    }
    assert (
        client.post(
            "/api/v1/_references/", headers=creator_headers, json=valid_bundle.reference
        ).status_code
        == 201
    )
    study["files"] = []
    response = client.post("/api/v1/_studies/", headers=creator_headers, json=study)
    assert response.status_code == 201
    sid = study["sid"]
    assert client.get(f"/api/v1/studies/{sid}/").status_code == 404
    assert (
        client.post(
            "/api/v1/_studies/", headers=creator_headers, json=study
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/update_index/", headers=creator_headers, json={"sid": sid}
        ).status_code
        == 409
    )
    for key, value in sections.items():
        response = client.patch(
            f"/api/v1/_studies/{sid}/", headers=creator_headers, json={key: value or {}}
        )
        assert response.status_code == 200
    response = client.post(
        "/api/v1/update_index/", headers=creator_headers, json={"sid": sid}
    )
    assert response.status_code == 200
    assert client.get(f"/api/v1/studies/{sid}/").status_code == 200
    assert (
        client.post(
            "/api/v1/update_index/",
            headers=creator_headers,
            json={"sid": sid, "action": "delete"},
        ).status_code
        == 422
    )
    assert client.get(f"/api/v1/studies/{sid}/").status_code == 200


def test_legacy_integer_file_handles_publish_and_explicit_delete_removes_study(
    client, creator_headers, valid_bundle
):
    study = deepcopy(valid_bundle.study)
    study["access"] = "public"
    sections = {
        key: study.pop(key, None)
        for key in (
            "groupset",
            "interventionset",
            "individualset",
            "outputset",
            "dataset",
        )
    }
    uploaded = client.post(
        "/api/v1/_datafiles/",
        headers=creator_headers,
        files={"file": ("Example_note.txt", b"original attachment")},
    )
    assert uploaded.status_code == 201
    assert type(uploaded.json()["id"]) is int
    study["files"] = [uploaded.json()["id"]]
    assert (
        client.post(
            "/api/v1/_references/", headers=creator_headers, json=valid_bundle.reference
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/_studies/", headers=creator_headers, json=study
        ).status_code
        == 201
    )
    sid = study["sid"]
    assert (
        client.patch(
            f"/api/v1/_studies/{sid}/", headers=creator_headers, json=sections
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/update_index/", headers=creator_headers, json={"sid": sid}
        ).status_code
        == 200
    )
    canonical = client.get(f"/api/v2/studies/{sid}", headers=creator_headers).json()
    assert canonical["attachments"][0]["name"] == "Example_note.txt"
    assert (
        client.get(uploaded.json()["file"], headers=creator_headers).content
        == b"original attachment"
    )
    from sqlalchemy import func, select

    from pkdb.db.models.files import StoredFile

    with client.app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(StoredFile)) == 1
    assert client.delete(f"/api/v1/_studies/{sid}/").status_code == 401
    assert (
        client.delete(f"/api/v1/_studies/{sid}/", headers=creator_headers).status_code
        == 204
    )
    assert client.get(f"/api/v1/studies/{sid}/").status_code == 404


def test_reference_conflict_is_structured_and_existing_study_is_unchanged(
    client, creator_headers, valid_bundle
):
    import json

    def put(study):
        return client.put(
            f"/api/v2/studies/{study['sid']}",
            headers=creator_headers,
            data={
                "study": json.dumps(study),
                "reference": json.dumps(valid_bundle.reference),
            },
        )

    assert put(valid_bundle.study).status_code == 201
    original = client.get(
        f"/api/v2/studies/{valid_bundle.study['sid']}", headers=creator_headers
    ).json()
    other = deepcopy(valid_bundle.study)
    other["sid"] = "OTHER"
    other["name"] = "Other"
    response = put(other)
    assert response.status_code == 409
    assert (
        client.get("/api/v2/studies/OTHER", headers=creator_headers).status_code == 404
    )
    assert (
        client.get(
            f"/api/v2/studies/{valid_bundle.study['sid']}", headers=creator_headers
        ).json()
        == original
    )


def test_legacy_reference_response_supports_unchanged_uploader(
    client, creator_headers, valid_bundle
):
    reference = {
        **valid_bundle.reference,
        "pmid": 123,
        "doi": None,
        "authors": [{"first_name": "A", "last_name": "Author"}],
    }
    response = client.post(
        "/api/v1/_references/", headers=creator_headers, json=reference
    )
    assert response.status_code == 201
    data = response.json()
    assert data["pmid"] == "123"
    assert "doi" not in data
    # The existing uploader checks the first element of each response value.
    assert not any("already exists" in value[0] for value in data.values())
