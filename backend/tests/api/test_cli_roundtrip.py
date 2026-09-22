import json

import pytest

from pkdb.cli import main
from pkdb.db.models.users import EmailAddress, User
from pkdb.services.authentication import password_hash


@pytest.mark.parametrize("credential_kind", ["legacy", "personal"])
def test_cli_validation_and_publication_roundtrip(
    client,
    creator_headers,
    valid_bundle,
    tmp_path,
    monkeypatch,
    capsys,
    credential_kind,
    ingestion_context,
    session_factory,
):
    if credential_kind == "personal":
        _, principal = ingestion_context
        with session_factory.begin() as session:
            user = session.get(User, principal.user_id)
            username = user.username
            user.password_hash = password_hash.hash("Upload-password-42")
            session.add(
                EmailAddress(
                    user_id=user.id,
                    email="upload@example.org",
                    is_primary=True,
                    is_verified=True,
                )
            )
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        browser_headers = {
            "Origin": client.app.state.browser_origin,
            "X-CSRF-Token": csrf,
        }
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": "Upload-password-42"},
                headers=browser_headers,
            ).status_code
            == 200
        )
        key = client.post(
            "/api/v1/me/api-keys",
            json={"name": "CLI upload", "scopes": ["read", "studies:write"]},
            headers=browser_headers,
        )
        assert key.status_code == 201
        creator_headers = {"Authorization": "Bearer " + key.json()["secret"]}
        client.cookies.clear()
    root = tmp_path / valid_bundle.study["name"]
    root.mkdir()
    (root / "study.json").write_text(json.dumps(valid_bundle.study))
    (root / "reference.json").write_text(json.dumps(valid_bundle.reference))
    for name, path in valid_bundle.files.items():
        (root / name).write_bytes(path.read_bytes())
    monkeypatch.setenv(
        "PKDB_API_TOKEN", creator_headers["Authorization"].split(" ", 1)[1]
    )
    for command in ("validate", "upload"):
        assert (
            main([command, str(root), "--api-url", "http://testserver"], client=client)
            == 0
        )
        assert json.loads(capsys.readouterr().out)["ok"] is True
    response = client.get(
        f"/api/v2/studies/{valid_bundle.study['sid']}", headers=creator_headers
    )
    assert response.status_code == 200
    assert response.json()["sid"] == valid_bundle.study["sid"]
