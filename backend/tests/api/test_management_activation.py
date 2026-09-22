import pytest

from pkdb.db.models.providers import ExternalIdentity
from pkdb.db.models.users import EmailAddress, User


@pytest.mark.parametrize("provider_only", [False, True])
@pytest.mark.parametrize("verified", [False, True])
def test_suspension_cannot_bypass_primary_email_verification(
    client, admin_headers, session_factory, provider_only, verified
):
    with session_factory.begin() as session:
        user = User(
            username="pending",
            email="pending@example.org",
            role="user",
            active=verified,
            pending_verification=not verified,
            password_hash=None if provider_only else "existing-password-hash",
        )
        session.add(user)
        session.flush()
        identifier = user.id
        session.add(
            EmailAddress(
                user_id=user.id, email=user.email, is_primary=True, is_verified=verified
            )
        )
        if provider_only:
            session.add(
                ExternalIdentity(
                    user_id=user.id,
                    provider="github",
                    issuer="https://github.com",
                    subject="123",
                    label="pending",
                )
            )
    path = f"/api/v1/admin/users/{identifier}"
    assert (
        client.patch(path, headers=admin_headers, json={"active": False}).status_code
        == 200
    )
    row = client.get("/api/v1/admin/users?q=pending", headers=admin_headers).json()[0]
    assert row["can_activate"] == verified
    response = client.patch(path, headers=admin_headers, json={"active": True})
    assert response.status_code == (200 if verified else 409), response.text
    with session_factory() as session:
        assert session.get(User, identifier).active == verified
    row = client.get("/api/v1/admin/users?q=pending", headers=admin_headers).json()[0]
    assert not row["can_activate"]
