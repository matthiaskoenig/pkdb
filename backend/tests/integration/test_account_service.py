from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from pkdb_server.db.models.users import User
from pkdb_server.services.accounts import AccountService, AccountThrottled
from pkdb_server.services.authentication import (
    AuthenticationFailed,
    authenticate_token,
    password_hash,
)


class Mailbox:
    def __init__(self):
        self.messages = []

    def send(self, recipient, subject, body):
        self.messages.append((recipient, subject, body))


@pytest.fixture
def accounts(session_factory):
    mailbox = Mailbox()
    service = AccountService(session_factory, mailbox)
    with session_factory.begin() as session:
        user = User(
            username="account",
            email="account@example.org",
            active=True,
            role="user",
            password_hash=password_hash.hash("Initial-password-42!"),
        )
        session.add(user)
    return service, mailbox


def test_reset_token_is_one_use_and_revokes_sessions(accounts, session_factory):
    service, mailbox = accounts
    from pkdb_server.db.models.users import EmailAddress

    with session_factory.begin() as session:
        user = session.scalar(select(User).where(User.username == "account"))
        session.add(EmailAddress(user_id=user.id, email=user.email, is_verified=True))
    old = service.login("account", "Initial-password-42!")
    service.request_reset("account@example.org")
    token = mailbox.messages[0][2].split()[-1]
    service.complete_reset(token, "New-test-password-42!")
    with pytest.raises(AuthenticationFailed):
        service.complete_reset(token, "Another-test-password-43!")
    with session_factory() as session:
        with pytest.raises(AuthenticationFailed):
            authenticate_token(old, session)
    assert service.login("account", "New-test-password-42!")


def test_unknown_reset_email_has_same_result(accounts):
    service, mailbox = accounts
    assert service.request_reset("unknown@example.org") is None
    assert mailbox.messages == []
    assert service.request_reset("account@example.org") is None


def test_registration_never_grants_an_elevated_role(accounts, session_factory):
    service, mailbox = accounts
    service.register("new-user", "new@example.org", "New-test-password-42!")
    with session_factory() as session:
        user = session.scalar(select(User).where(User.username == "new-user"))
        assert user.role == "user"
        assert not user.active
    with pytest.raises(AuthenticationFailed):
        service.login("new-user", "New-test-password-42!")
    token = mailbox.messages[0][2].split()[-1]
    service.verify_email(token)
    assert service.login("new-user", "New-test-password-42!")
    with pytest.raises(AuthenticationFailed):
        service.verify_email(token)


def test_login_throttle_expires_with_injected_clock(accounts):
    service, _ = accounts
    now = datetime(2026, 1, 1, tzinfo=UTC)
    service.clock = lambda: now
    for _ in range(10):
        with pytest.raises(AuthenticationFailed):
            service.login("account", "wrong")
    with pytest.raises(AccountThrottled):
        service.login("account", "Initial-password-42!")
    now += timedelta(minutes=11)
    assert service.login("account", "Initial-password-42!")


def test_reset_requires_verified_email(accounts, session_factory):
    service, mailbox = accounts
    service.request_reset("account@example.org")
    assert mailbox.messages == []


@pytest.mark.parametrize("action", ["expired", "wrong-purpose", "disabled"])
def test_invalid_reset_cannot_change_password(accounts, session_factory, action):
    from pkdb_server.db.models.users import EmailAddress

    service, mailbox = accounts
    with session_factory.begin() as session:
        user = session.scalar(select(User).where(User.username == "account"))
        session.add(EmailAddress(user_id=user.id, email=user.email, is_verified=True))
    now = datetime(2026, 1, 1, tzinfo=UTC)
    service.clock = lambda: now
    service.request_reset("account@example.org")
    token = mailbox.messages[0][2].split()[-1]
    if action == "expired":
        now += timedelta(hours=2)
    elif action == "disabled":
        with session_factory.begin() as session:
            session.scalar(
                select(User).where(User.username == "account")
            ).active = False
    with pytest.raises(AuthenticationFailed):
        if action == "wrong-purpose":
            service.verify_email(token)
        else:
            service.complete_reset(token, "Unwanted-password-42!")
    with session_factory() as session:
        user = session.scalar(select(User).where(User.username == "account"))
        assert password_hash.verify("Initial-password-42!", user.password_hash)


@pytest.fixture
def primary_change_context(accounts, session_factory):
    from pkdb_server.db.models.users import EmailAddress
    from pkdb_server.services.credentials import CredentialService

    service, mailbox = accounts
    with session_factory.begin() as session:
        user = session.scalar(select(User).where(User.username == "account"))
        primary = EmailAddress(
            user_id=user.id, email=user.email, is_primary=True, is_verified=True
        )
        secondary = EmailAddress(
            user_id=user.id,
            email="secondary@example.org",
            is_primary=False,
            is_verified=True,
        )
        session.add_all([primary, secondary])
        session.flush()
        primary_id, secondary_id = primary.id, secondary.id
    _, principal = CredentialService(session_factory, service).login(
        "account", "Initial-password-42!"
    )
    return service, mailbox, principal, primary_id, secondary_id


def test_primary_change_notifies_both_verified_addresses_once(
    primary_change_context, session_factory
):
    from pkdb_server.db.models.users import EmailAddress

    service, mailbox, principal, primary_id, secondary_id = primary_change_context
    service.change_email(principal, secondary_id, {"is_primary": True})
    assert [message[0] for message in mailbox.messages] == [
        "account@example.org",
        "secondary@example.org",
    ]
    for _, subject, body in mailbox.messages:
        assert "primary email" in subject
        assert "requested" in body
        assert "Initial-password-42!" not in body
    with session_factory.begin() as session:
        assert not session.get(EmailAddress, primary_id).is_primary
        assert session.get(EmailAddress, secondary_id).is_primary
        assert session.get(User, principal.user_id).email == "secondary@example.org"
    service.change_email(principal, secondary_id, {"is_primary": True})
    assert len(mailbox.messages) == 2


@pytest.mark.parametrize("fail_on", [1, 2])
def test_primary_change_mail_failure_retains_working_primary(
    primary_change_context, session_factory, fail_on
):
    from pkdb_server.db.models.users import EmailAddress
    from pkdb_server.services.accounts import MailDeliveryFailed

    service, mailbox, principal, primary_id, secondary_id = primary_change_context
    delivered = []

    def fail_delivery(recipient, subject, body):
        if len(delivered) + 1 == fail_on:
            raise OSError("SMTP unavailable")
        delivered.append((recipient, subject, body))

    service.mailer.send = fail_delivery
    with pytest.raises(MailDeliveryFailed):
        service.change_email(principal, secondary_id, {"is_primary": True})
    with session_factory.begin() as session:
        assert session.get(EmailAddress, primary_id).is_primary
        assert not session.get(EmailAddress, secondary_id).is_primary
        assert session.get(User, principal.user_id).email == "account@example.org"
    assert all("requested" in body for _, _, body in delivered)


def test_primary_change_does_not_notify_unverified_previous_address(
    primary_change_context, session_factory
):
    from pkdb_server.db.models.users import EmailAddress

    service, mailbox, principal, primary_id, secondary_id = primary_change_context
    with session_factory.begin() as session:
        session.get(EmailAddress, primary_id).is_verified = False
    service.change_email(principal, secondary_id, {"is_primary": True})
    assert [message[0] for message in mailbox.messages] == ["secondary@example.org"]
