import pytest
from sqlalchemy import select

from pkdb_server.db.models.users import EmailAddress, User


def payload():
    return {
        "username": "new-user",
        "email": "NEW@example.test",
        "password": "New-password-42!",
        "first_name": "First",
        "last_name": "Last",
        "groups": ["basic"],
    }


def test_admin_creates_pending_user_without_issuing_credentials(
    client, admin_headers, session_factory
):
    response = client.post("/api/v1/_users/", headers=admin_headers, json=payload())
    assert response.status_code == 201
    data = response.json()
    assert set(data) == {
        "id",
        "username",
        "first_name",
        "last_name",
        "email",
        "groups",
    }
    assert data["groups"] == ["basic"]
    assert data["email"] == "new@example.test"
    assert "auth_token" not in data
    with session_factory() as session:
        user = session.get(User, data["id"])
        assert user.role == "user" and not user.active
        assert user.password_hash is None
        email = session.scalar(
            select(EmailAddress).where(EmailAddress.user_id == user.id)
        )
        assert email.is_primary and not email.is_verified
    assert (
        client.post(
            "/api-token-auth/",
            json={"username": "new-user", "password": payload()["password"]},
        ).status_code
        == 410
    )
    detail = client.get(f"/api/v1/_users/{data['id']}.json", headers=admin_headers)
    assert detail.status_code == 200
    assert detail.json() == {
        key: data[key]
        for key in ("id", "username", "first_name", "last_name", "groups")
    }


def test_admin_user_routes_reject_nonadmins_and_recheck_role(
    client, admin_headers, creator_headers, session_factory
):
    for headers, expected in (({}, 401), (creator_headers, 403)):
        assert (
            client.post("/api/v1/_users/", headers=headers, json=payload()).status_code
            == expected
        )
        assert client.get("/api/v1/_users/1/", headers=headers).status_code == expected
        assert (
            client.patch(
                "/api/v1/_users/1/", headers=headers, json={"groups": ["admin"]}
            ).status_code
            == expected
        )
    with session_factory.begin() as session:
        operator = session.scalar(select(User).where(User.username == "mkoenig"))
        operator.role = "user"
    assert (
        client.post(
            "/api/v1/_users/", headers=admin_headers, json=payload()
        ).status_code
        == 403
    )
    with session_factory() as session:
        assert session.scalar(select(User).where(User.username == "new-user")) is None


def test_admin_update_preserves_identity_and_applies_single_role(client, admin_headers):
    created = client.post(
        "/api/v1/_users/", headers=admin_headers, json=payload()
    ).json()
    url = f"/api/v1/_users/{created['id']}/"
    result = client.patch(
        url,
        headers=admin_headers,
        json={"username": "ignored", "groups": ["reviewer"], "first_name": "Changed"},
    )
    assert result.status_code == 200
    assert result.json()["username"] == "new-user"
    assert result.json()["groups"] == ["reviewer"]
    assert result.json()["first_name"] == "Changed"
    assert (
        client.put(
            url, headers=admin_headers, json={"last_name": "Missing role"}
        ).status_code
        == 400
    )
    assert (
        client.patch(
            url, headers=admin_headers, json={"groups": ["basic", "admin"]}
        ).status_code
        == 400
    )
    assert (
        client.patch(
            url, headers=admin_headers, json={"groups": ["unknown"]}
        ).status_code
        == 400
    )
    assert (
        client.get("/api/v1/_users/999999/", headers=admin_headers).status_code == 404
    )


def test_duplicate_admin_creation_rolls_back(client, admin_headers, session_factory):
    assert (
        client.post(
            "/api/v1/_users/", headers=admin_headers, json=payload()
        ).status_code
        == 201
    )
    changed = {**payload(), "username": "other-name"}
    assert (
        client.post("/api/v1/_users/", headers=admin_headers, json=changed).status_code
        == 409
    )
    with session_factory() as session:
        assert session.scalar(select(User).where(User.username == "other-name")) is None


def test_admin_service_rejects_stale_authorization(session_factory):
    from pkdb.schemas.admin_users import AdminUserCreate
    from pkdb.schemas.security import Principal

    from pkdb_server.services.admin_users import AdminUserService
    from pkdb_server.services.authorization import AuthorizationDenied

    with session_factory.begin() as session:
        user = User(username="former-operator", role="admin", active=True)
        session.add(user)
        session.flush()
        stale = Principal(user_id=user.id, username=user.username, role="admin")
    with session_factory.begin() as session:
        session.get(User, stale.user_id).role = "user"
    with pytest.raises(AuthorizationDenied):
        AdminUserService(session_factory).create(stale, AdminUserCreate(**payload()))


def test_admin_cannot_promote_a_second_administrator(client, admin_headers):
    created = client.post(
        "/api/v1/_users/", headers=admin_headers, json=payload()
    ).json()
    url = f"/api/v1/_users/{created['id']}/"
    assert (
        client.patch(url, headers=admin_headers, json={"groups": ["admin"]}).status_code
        == 400
    )
    assert (
        client.patch(
            url, headers=admin_headers, json={"groups": ["reviewer"]}
        ).status_code
        == 200
    )
    assert client.get(url, headers=admin_headers).json()["groups"] == ["reviewer"]
