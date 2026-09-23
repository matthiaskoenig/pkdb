from copy import deepcopy

import pytest


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/v1/_references/"),
        ("PATCH", "/api/v1/_references/REF1/"),
        ("POST", "/api/v1/_studies/"),
        ("PATCH", "/api/v1/_studies/TEST1/"),
        ("POST", "/api/v1/update_index/"),
    ],
)
@pytest.mark.parametrize("body", ["{", "[]"])
def test_legacy_upload_authentication_precedes_body_validation(
    client, method, path, body
):
    response = client.request(
        method, path, content=body, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing credentials"}


def test_legacy_draft_is_invisible_until_finalization(
    client, admin_headers, valid_bundle
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
            "/api/v1/_references/", headers=admin_headers, json=valid_bundle.reference
        ).status_code
        == 201
    )
    study["files"] = []
    response = client.post("/api/v1/_studies/", headers=admin_headers, json=study)
    assert response.status_code == 201
    sid = study["sid"]
    assert client.get(f"/api/v1/studies/{sid}/").status_code == 404
    assert (
        client.post("/api/v1/_studies/", headers=admin_headers, json=study).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/update_index/", headers=admin_headers, json={"sid": sid}
        ).status_code
        == 409
    )
    for key, value in sections.items():
        response = client.patch(
            f"/api/v1/_studies/{sid}/", headers=admin_headers, json={key: value or {}}
        )
        assert response.status_code == 200
    response = client.post(
        "/api/v1/update_index/", headers=admin_headers, json={"sid": sid}
    )
    assert response.status_code == 200
    assert client.get(f"/api/v1/studies/{sid}/").status_code == 200
    assert (
        client.post(
            "/api/v1/update_index/",
            headers=admin_headers,
            json={"sid": sid, "action": "delete"},
        ).status_code
        == 422
    )
    assert client.get(f"/api/v1/studies/{sid}/").status_code == 200


def test_legacy_integer_file_handles_publish_and_explicit_delete_removes_study(
    client, admin_headers, valid_bundle
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
        headers=admin_headers,
        files={"file": ("Example_note.txt", b"original attachment")},
    )
    assert uploaded.status_code == 201
    assert type(uploaded.json()["id"]) is int
    study["files"] = [uploaded.json()["id"]]
    assert (
        client.post(
            "/api/v1/_references/", headers=admin_headers, json=valid_bundle.reference
        ).status_code
        == 201
    )
    assert (
        client.post("/api/v1/_studies/", headers=admin_headers, json=study).status_code
        == 201
    )
    sid = study["sid"]
    assert (
        client.patch(
            f"/api/v1/_studies/{sid}/", headers=admin_headers, json=sections
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/update_index/", headers=admin_headers, json={"sid": sid}
        ).status_code
        == 200
    )
    canonical = client.get(f"/api/v2/studies/{sid}", headers=admin_headers).json()
    assert canonical["attachments"][0]["name"] == "Example_note.txt"
    assert (
        client.get(uploaded.json()["file"], headers=admin_headers).content
        == b"original attachment"
    )
    from sqlalchemy import func, select

    from pkdb_server.db.models.files import StoredFile

    with client.app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(StoredFile)) == 1
    assert client.delete(f"/api/v1/_studies/{sid}/").status_code == 401
    assert (
        client.delete(f"/api/v1/_studies/{sid}/", headers=admin_headers).status_code
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


def test_owned_draft_reads_and_reference_edits_stay_unpublished(
    client, creator_headers, valid_bundle
):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    from pkdb_server.db.models.drafts import ReferenceDraft, StudyDraft
    from pkdb_server.db.models.users import User
    from pkdb_server.services.authentication import issue_token

    core = deepcopy(valid_bundle.study)
    for key in ("groupset", "individualset", "interventionset", "outputset", "dataset"):
        core.pop(key, None)
    sid, reference_sid = core["sid"], str(valid_bundle.reference["sid"])
    assert (
        client.post(
            "/api/v1/_references/", headers=creator_headers, json=valid_bundle.reference
        ).status_code
        == 201
    )
    response = client.patch(
        f"/api/v1/_references/{reference_sid}/",
        headers=creator_headers,
        json={"title": "Draft title"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Draft title"
    assert (
        client.get(
            f"/api/v1/_references/{reference_sid}/", headers=creator_headers
        ).json()
        == response.json()
    )
    assert (
        client.post("/api/v1/_studies/", headers=creator_headers, json=core).status_code
        == 201
    )
    response = client.get(f"/api/v1/_studies/{sid}/", headers=creator_headers)
    assert response.status_code == 200
    assert response.json()["sid"] == sid
    assert (
        client.get(f"/api/v1/studies/{sid}/", headers=creator_headers).status_code
        == 404
    )
    with client.app.state.session_factory.begin() as session:
        other = User(username="other-reader", role="curator", active=True)
        session.add(other)
        session.flush()
        other_token = issue_token(other, session)
    for path in (f"/_studies/{sid}/", f"/_references/{reference_sid}/"):
        assert client.get("/api/v1" + path).status_code == 401
        assert (
            client.get(
                "/api/v1" + path, headers={"Authorization": f"Token {other_token}"}
            ).status_code
            == 404
        )
    assert (
        client.patch(
            f"/api/v1/_references/{reference_sid}/",
            headers=creator_headers,
            json={"sid": "OTHER"},
        ).status_code
        == 422
    )
    with client.app.state.session_factory.begin() as session:
        for model in (ReferenceDraft, StudyDraft):
            session.execute(
                update(model).values(
                    expires_at=datetime.now(UTC) - timedelta(seconds=1)
                )
            )
    for path in (f"/_studies/{sid}/", f"/_references/{reference_sid}/"):
        assert client.get("/api/v1" + path, headers=creator_headers).status_code == 404


def test_publication_metadata_supports_resume_without_exposing_private_studies(
    client, creator_headers, valid_bundle
):
    import json

    from pkdb.domain.validation import PROCESSING_VERSION

    sid = valid_bundle.study["sid"]
    response = client.put(
        f"/api/v2/studies/{sid}",
        headers=creator_headers,
        data={
            "study": json.dumps(valid_bundle.study),
            "reference": json.dumps(valid_bundle.reference),
        },
    )
    assert response.status_code == 201
    digest = response.json()["digest"]
    response = client.get(f"/api/v2/studies/{sid}/publication", headers=creator_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["sid"] == sid and body["digest"] == digest
    assert (
        body["processing_version"]
        == body["current_processing_version"]
        == PROCESSING_VERSION
    )
    assert body["vocabulary_version"] == body["current_vocabulary_version"]
    assert len(body["vocabulary_version"]) == 64
    assert client.get(f"/api/v2/studies/{sid}/publication").status_code == 403
    assert (
        client.get(
            "/api/v2/studies/missing/publication", headers=creator_headers
        ).status_code
        == 404
    )
