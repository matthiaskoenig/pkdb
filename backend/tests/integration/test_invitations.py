from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from pkdb.db.models.credentials import BrowserSession
from pkdb.db.models.mfa import AuditEvent
from pkdb.db.models.security import SecurityConfiguration
from pkdb.db.models.users import EmailAddress, Token, User
from pkdb.schemas.security import Principal
from pkdb.services.accounts import MailDeliveryFailed
from pkdb.services.authentication import AuthenticationFailed, password_hash
from pkdb.services.invitations import InvitationService


class Mailer:
    def __init__(self):
        self.messages = []

    def send(self, recipient, subject, body):
        self.messages.append((recipient, subject, body))

    @property
    def token(self):
        return self.messages[-1][2].split(": ")[-1]


@pytest.fixture
def invitation_context(session_factory):
    now = datetime.now(UTC)
    with session_factory.begin() as session:
        admin = User(username="mkoenig", role="admin", active=True)
        invited = User(
            username="MariiaMysh",
            role="reviewer",
            active=False,
            email="reviewer@example.org",
        )
        session.add_all([admin, invited])
        session.flush()
        session.get(SecurityConfiguration, 1).designated_administrator_id = admin.id
        browser = BrowserSession(
            user_id=admin.id,
            digest="a" * 64,
            last_seen_at=now,
            authenticated_at=now,
            mfa_at=now,
            expires_at=now + timedelta(days=1),
        )
        email = EmailAddress(
            user_id=invited.id, email=invited.email, is_primary=True, is_verified=False
        )
        session.add_all([browser, email])
        session.flush()
        principal = Principal(
            user_id=admin.id,
            username="mkoenig",
            role="admin",
            credential_kind="session",
            credential_id=browser.id,
        )
        invited_id, email_id = invited.id, email.id
    mailer = Mailer()
    return (
        InvitationService(session_factory, mailer),
        principal,
        invited_id,
        email_id,
        mailer,
    )


def test_invitation_claims_existing_identity_once(session_factory, invitation_context):
    service, principal, invited_id, email_id, mailer = invitation_context
    result = service.issue(principal, invited_id, email_id)
    assert result["delivery"] == "sent" and "token" not in result
    raw = mailer.token
    with session_factory() as session:
        assert session.scalar(select(Token)).digest != raw
        assert not session.get(User, invited_id).active
    accepted = service.accept(raw, "A-strong-new-password!")
    assert accepted["user_id"] == invited_id
    with session_factory() as session:
        user = session.get(User, invited_id)
        assert user.active and user.role == "reviewer"
        assert password_hash.verify("A-strong-new-password!", user.password_hash)
        assert session.get(EmailAddress, email_id).is_verified
        assert set(session.scalars(select(AuditEvent.action))) == {
            "invitation.sent",
            "invitation.accepted",
        }
    with pytest.raises(AuthenticationFailed):
        service.accept(raw, "Another-strong-password!")


def test_invitation_resend_revokes_previous_and_expiry_blocks_claim(
    session_factory, invitation_context
):
    service, principal, invited_id, email_id, mailer = invitation_context
    service.issue(principal, invited_id, email_id)
    previous = mailer.token
    service.issue(principal, invited_id, email_id)
    with pytest.raises(AuthenticationFailed):
        service.accept(previous, "A-strong-new-password!")
    service.clock = lambda: datetime.now(UTC) + timedelta(days=8)
    with pytest.raises(AuthenticationFailed):
        service.accept(mailer.token, "A-strong-new-password!")
    with session_factory() as session:
        assert not session.get(User, invited_id).active


def test_suspension_and_changed_contact_block_claim(
    session_factory, invitation_context
):
    service, principal, invited_id, email_id, mailer = invitation_context
    service.issue(principal, invited_id, email_id)
    with session_factory.begin() as session:
        session.get(User, invited_id).pending_verification = False
    with pytest.raises(AuthenticationFailed):
        service.accept(mailer.token, "A-strong-new-password!")
    service.issue(principal, invited_id, email_id)
    with session_factory.begin() as session:
        session.get(User, invited_id).email = "changed@example.org"
    with pytest.raises(AuthenticationFailed):
        service.accept(mailer.token, "A-strong-new-password!")


def test_credentials_on_disabled_account_block_invitation(
    session_factory, invitation_context
):
    service, principal, invited_id, email_id, _ = invitation_context
    with session_factory.begin() as session:
        session.get(User, invited_id).password_hash = "existing-credential"
    with pytest.raises(ValueError, match="unclaimed"):
        service.issue(principal, invited_id, email_id)


def test_failed_delivery_rolls_back_pending_token(session_factory, invitation_context):
    service, principal, invited_id, email_id, _ = invitation_context

    class FailingMailer:
        def send(self, *args):
            raise OSError("delivery failed")

    service.mailer = FailingMailer()
    with pytest.raises(MailDeliveryFailed):
        service.issue(principal, invited_id, email_id)
    with session_factory() as session:
        assert session.scalar(select(Token)) is None
        assert not session.get(User, invited_id).pending_verification


def test_suspended_unclaimed_user_cannot_be_reinvited(
    session_factory, invitation_context
):
    service, principal, invited_id, email_id, _ = invitation_context
    with session_factory.begin() as session:
        session.get(User, invited_id).suspended_at = datetime.now(UTC)
    with pytest.raises(ValueError, match="unclaimed"):
        service.issue(principal, invited_id, email_id)
