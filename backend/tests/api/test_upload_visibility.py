"""Upload keys can preserve visibility; private data needs an explicit assignment."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select

from pkdb_server.db.models.credentials import ApiKey
from pkdb_server.db.models.files import StudyAttachment
from pkdb_server.db.models.studies import Study, StudyGrant, StudyUser
from pkdb_server.db.models.users import User
from pkdb_server.services.credentials import digest


def key_for(session, user, scopes=("read", "studies:write")):
    secret = f"pkdb_live_visibility_{user.id}"
    session.add(
        ApiKey(
            user_id=user.id,
            name="upload test",
            prefix=secret[:17],
            digest=digest(secret),
            scopes=list(scopes),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    return {"Authorization": f"Bearer {secret}"}


def body(bundle):
    return {
        "study": json.dumps(bundle.study),
        "reference": json.dumps(bundle.reference),
    }


@pytest.mark.parametrize("access", ["public", "private"])
@pytest.mark.parametrize("role", ["curator", "reviewer", "admin"])
def test_write_key_uploads_either_visibility_and_can_change_it(
    client, valid_bundle, session_factory, role, access
):
    with session_factory.begin() as session:
        uploader = User(username="uploader", role=role, active=True)
        session.add(uploader)
        session.flush()
        headers = key_for(session, uploader)
    # Keep the scientific creator attribution, even when another curator uploads.
    valid_bundle.study["access"] = access
    url = f"/api/v2/studies/{valid_bundle.study['sid']}"
    assert (
        client.post(
            "/api/v2/studies/validate", headers=headers, data=body(valid_bundle)
        ).status_code
        == 200
    )
    response = client.put(url, headers=headers, data=body(valid_bundle))
    assert response.status_code == 201, response.text
    assert client.get(url, headers=headers).json()["metadata"]["access"] == access
    assert client.get(url).status_code == (200 if access == "public" else 403)
    assert client.get("/api/v1/studies/").json()["data"]["count"] == (
        1 if access == "public" else 0
    )
    valid_bundle.study["access"] = "private" if access == "public" else "public"
    response = client.put(url, headers=headers, data=body(valid_bundle))
    assert response.status_code == 200, response.text
    assert client.get(url).status_code == (403 if access == "public" else 200)


@pytest.mark.parametrize(
    "scopes,active", [(("read",), True), (("read", "studies:write"), False)]
)
def test_upload_still_requires_active_write_key(
    client, valid_bundle, session_factory, scopes, active
):
    with session_factory.begin() as session:
        uploader = User(username="uploader", role="curator", active=active)
        session.add(uploader)
        session.flush()
        headers = key_for(session, uploader, scopes)
    valid_bundle.study["access"] = "public"
    response = client.put(
        f"/api/v2/studies/{valid_bundle.study['sid']}",
        headers=headers,
        data=body(valid_bundle),
    )
    assert response.status_code == (403 if active else 401)


def test_private_visibility_matches_details_lists_exports_and_attachments(
    client,
    creator_headers,
    admin_headers,
    valid_bundle,
    session_factory,
    ingestion_context,
    tmp_path,
):
    valid_bundle.study["access"] = "private"
    attachment = tmp_path / "notes.txt"
    attachment.write_text("private attachment")
    url = f"/api/v2/studies/{valid_bundle.study['sid']}"
    with attachment.open("rb") as source:
        assert (
            client.put(
                url,
                headers=creator_headers,
                data=body(valid_bundle),
                files={"files": ("notes.txt", source)},
            ).status_code
            == 201
        )
    cases = [
        ("anonymous", {}, False),
        ("admin", admin_headers, True),
        ("creator without assignment", creator_headers, False),
    ]
    with session_factory.begin() as session:
        study = session.scalar(
            select(Study).where(Study.sid == valid_bundle.study["sid"])
        )
        session.execute(delete(StudyGrant).where(StudyGrant.study_id == study.id))
        file_id = session.scalar(
            select(StudyAttachment.file_id).where(StudyAttachment.study_id == study.id)
        )
        for name, role, grant, allowed in [
            ("assigned-curator", "curator", "curator", True),
            ("assigned-reviewer", "reviewer", "curator", True),
            ("unassigned-reviewer", "reviewer", None, False),
            ("unassigned-curator", "curator", None, False),
            ("collaborator", "user", "collaborator", False),
        ]:
            user = User(username=name, role=role, active=True)
            session.add(user)
            session.flush()
            if grant:
                # Collaborators are attribution only; effective grants are curators.
                model = StudyUser if grant == "collaborator" else StudyGrant
                session.add(model(study_id=study.id, user_id=user.id, role=grant))
            cases.append((name, key_for(session, user), allowed))
    for name, headers, allowed in cases:
        assert client.get(url, headers=headers).status_code == (
            200 if allowed else 403
        ), name
        for path in ("studies", "outputs", "pkdata/studies", "pkdata/outputs"):
            response = client.get(f"/api/v1/{path}/", headers=headers)
            assert response.status_code == 200, response.text
            assert (response.json()["data"]["count"] > 0) == allowed, (name, path)
        overview = client.get("/api/v1/filter/", headers=headers)
        assert overview.status_code == 200
        assert (overview.json()["studies"] > 0) == allowed, name
        response = client.get(f"/media/{file_id}/notes.txt", headers=headers)
        assert response.status_code == (
            200 if allowed else 401 if name == "anonymous" else 403
        ), name
