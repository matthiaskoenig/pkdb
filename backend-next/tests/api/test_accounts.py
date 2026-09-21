import pytest
from sqlalchemy import select

from pkdb.db.models.users import User


@pytest.fixture
def mailbox(client):
    class Mailbox:
        def __init__(self):
            self.messages = []

        def send(self, recipient, subject, body):
            self.messages.append((recipient, subject, body))

    mailbox = Mailbox()
    client.app.state.accounts.mailer = mailbox
    return mailbox


def test_legacy_registration_verification_and_login(client, mailbox):
    response = client.post(
        "/accounts/register/",
        json={
            "username": "new",
            "email": "new@example.org",
            "password": "Initial-password-42!",
        },
    )
    assert response.status_code == 201
    assert response.json() == {"username": "new", "email": "new@example.org"}
    assert (
        client.post(
            "/api-token-auth/",
            json={"username": "new", "password": "Initial-password-42!"},
        ).status_code
        == 400
    )
    token = mailbox.messages[0][2].split()[-1]
    response = client.post("/accounts/verify-email/", json={"key": token})
    assert response.status_code == 200
    assert response.json() == {"email": "new@example.org"}
    response = client.post(
        "/api-token-auth/", json={"username": "new", "password": "Initial-password-42!"}
    )
    assert response.status_code == 200
    assert set(response.json()) == {"token"}


def test_registration_rejects_privilege_injection(client, mailbox, session_factory):
    response = client.post(
        "/accounts/register/",
        json={
            "username": "elevated",
            "email": "e@example.org",
            "password": "Initial-password-42!",
            "role": "admin",
        },
    )
    assert response.status_code == 422
    with session_factory() as session:
        assert session.scalar(select(User).where(User.username == "elevated")) is None


def test_mail_failure_does_not_create_unusable_account(
    client, mailbox, session_factory
):
    def fail(*args):
        raise OSError("test mail failure")

    mailbox.send = fail
    response = client.post(
        "/accounts/register/",
        json={
            "username": "mailfail",
            "email": "fail@example.org",
            "password": "Initial-password-42!",
        },
    )
    assert response.status_code == 503
    with session_factory() as session:
        assert session.scalar(select(User).where(User.username == "mailfail")) is None


def test_unknown_reset_email_uses_legacy_response(client, mailbox):
    response = client.post(
        "/accounts/request-password-reset/", json={"email": "unknown@example.org"}
    )
    assert response.status_code == 200
    assert response.json() == {"email": "unknown@example.org"}
    assert mailbox.messages == []


def test_email_addresses_are_owner_scoped_and_must_be_verified(
    client, mailbox, creator_headers
):
    response = client.post(
        "/accounts/emails/",
        headers=creator_headers,
        json={"email": "extra@example.org"},
    )
    assert response.status_code == 201
    entry = response.json()
    assert entry["email"] == "extra@example.org"
    assert not entry["is_verified"]
    detail = f"/accounts/emails/{entry['id']}/"
    assert client.get(detail).status_code == 401
    assert (
        client.patch(
            detail, headers=creator_headers, json={"is_primary": True}
        ).status_code
        == 400
    )
    token = mailbox.messages[-1][2].split()[-1]
    assert (
        client.post("/accounts/verify-email/", json={"key": token}).status_code == 200
    )
    result = client.patch(detail, headers=creator_headers, json={"is_primary": True})
    assert result.status_code == 200
    assert result.json()["is_primary"]
    assert (
        client.patch(
            detail, headers=creator_headers, json={"email": "changed@example.org"}
        ).status_code
        == 400
    )
    assert client.get("/accounts/emails/", headers=creator_headers).status_code == 200
    assert client.delete(detail, headers=creator_headers).status_code == 204
    assert client.get(detail, headers=creator_headers).status_code == 404
