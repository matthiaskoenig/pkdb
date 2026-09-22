from sqlalchemy import select

from pkdb.db.models.users import EmailAddress, User


def test_admin_invitation_and_public_accept_claim_existing_user(
    client, admin_headers, session_factory
):
    class Mailbox:
        def __init__(self):
            self.messages = []

        def send(self, recipient, subject, body):
            self.messages.append(body)

    mailbox = Mailbox()
    client.app.state.invitations.mailer = mailbox
    with session_factory.begin() as session:
        user = User(
            username="invited",
            role="reviewer",
            email="invite@example.org",
            active=False,
        )
        session.add(user)
        session.flush()
        email = EmailAddress(
            user_id=user.id, email=user.email, is_primary=True, is_verified=False
        )
        session.add(email)
        session.flush()
        user_id, email_id = user.id, email.id
    path = f"/api/v1/admin/users/{user_id}/invitations"
    assert client.post(path, json={"email_id": email_id}).status_code == 401
    response = client.post(path, headers=admin_headers, json={"email_id": email_id})
    assert response.status_code == 200
    assert response.json()["delivery"] == "sent"
    token = mailbox.messages[-1].split(": ")[-1]
    assert token not in response.text
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    browser_headers = {"Origin": client.app.state.browser_origin, "X-CSRF-Token": csrf}
    response = client.post(
        "/api/v1/auth/invitations/accept",
        headers=browser_headers,
        json={"token": token, "password": "Long-strong-password!"},
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == user_id
    assert (
        client.post(
            "/api/v1/auth/invitations/accept",
            headers=browser_headers,
            json={"token": token, "password": "Different-strong-password!"},
        ).status_code
        == 400
    )
    with session_factory() as session:
        assert session.get(User, user_id).active
        assert (
            session.scalar(select(User).where(User.username == "invited")).id == user_id
        )
        assert session.get(EmailAddress, email_id).is_verified


def test_admin_list_exposes_reviewed_invitation_contact_not_activation_bypass(
    client, admin_headers, creator_headers, session_factory
):
    from datetime import UTC, datetime

    with session_factory.begin() as session:
        invited = User(username="roster-new", email="new@example.org", active=False)
        suspended = User(
            username="roster-suspended",
            email="suspended@example.org",
            active=False,
            suspended_at=datetime.now(UTC),
        )
        missing = User(username="roster-no-contact", active=False)
        session.add_all([invited, suspended, missing])
        session.flush()
        email = EmailAddress(user_id=invited.id, email=invited.email, is_primary=True)
        session.add(email)
        session.flush()
        email_id = email.id
    response = client.get("/api/v1/admin/users?q=roster-", headers=admin_headers)
    assert response.status_code == 200
    rows = {row["username"]: row for row in response.json()}
    assert rows["roster-new"]["invitation_email_id"] == email_id
    assert rows["roster-new"]["can_invite"] is True
    assert rows["roster-new"]["can_activate"] is False
    assert rows["roster-suspended"]["status"] == "suspended"
    assert rows["roster-suspended"]["can_invite"] is False
    assert rows["roster-no-contact"]["can_invite"] is False
    assert client.get("/api/v1/admin/users", headers=creator_headers).status_code == 403
