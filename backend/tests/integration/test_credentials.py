from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from pkdb_server.db.models.credentials import ApiKey, BrowserSession
from pkdb_server.db.models.users import EmailAddress, User
from pkdb_server.services.accounts import AccountService
from pkdb_server.services.authentication import (
    AuthenticationFailed,
    authenticate_token,
    password_hash,
)
from pkdb_server.services.authorization import AuthorizationDenied
from pkdb_server.services.credentials import (
    CredentialService,
    authenticate_session,
    require_session,
)


class Mailbox:
    def __init__(self):
        self.messages = []

    def send(self, recipient, subject, body):
        self.messages.append(body)


@pytest.fixture
def credentials(session_factory):
    mailbox = Mailbox()
    accounts = AccountService(session_factory, mailbox)
    service = CredentialService(session_factory, accounts)
    with session_factory.begin() as session:
        user = User(
            username="credential-user",
            role="curator",
            active=True,
            email="credential@example.org",
            password_hash=password_hash.hash("Example-password-42"),
        )
        session.add(user)
        session.flush()
        session.add(
            EmailAddress(
                user_id=user.id, email=user.email, is_primary=True, is_verified=True
            )
        )
    raw, principal = service.login("credential-user", "Example-password-42")
    return service, raw, principal, mailbox


def test_key_secrets_scopes_and_session_separation(credentials, session_factory):
    service, raw, principal, _ = credentials
    key = service.create_key(principal, "analysis")
    assert key["scopes"] == ["read"]
    assert "secret" not in service.keys(principal)[0]
    with session_factory.begin() as session:
        assert session.get(ApiKey, key["id"]).digest != key["secret"]
        actor = authenticate_token(key["secret"], session)
        assert actor.scopes == frozenset({"read"})
        assert actor.credential_kind == "api_key"
        with pytest.raises(AuthorizationDenied):
            require_session(actor, session)
        with pytest.raises(AuthenticationFailed):
            authenticate_token(raw, session)
        with pytest.raises(AuthenticationFailed):
            authenticate_session(key["secret"], session)
    service.revoke_session(principal, principal.credential_id)
    with session_factory.begin() as session:
        assert authenticate_token(key["secret"], session).user_id == principal.user_id
        with pytest.raises(AuthenticationFailed):
            authenticate_session(raw, session)


def test_key_demotion_expiry_and_revocation(credentials, session_factory):
    service, _, principal, _ = credentials
    key = service.create_key(principal, "uploader", ["read", "studies:write"])
    with session_factory.begin() as session:
        session.get(User, principal.user_id).role = "user"
    with session_factory.begin() as session:
        assert authenticate_token(key["secret"], session).role == "user"
    with pytest.raises(AuthorizationDenied):
        service.create_key(principal, "uploader 2", ["read", "studies:write"])
    service.revoke_key(principal, key["id"])
    service.revoke_key(principal, key["id"])
    with session_factory.begin() as session:
        with pytest.raises(AuthenticationFailed):
            authenticate_token(key["secret"], session)
    key2 = service.create_key(principal, "expired")
    with session_factory.begin() as session:
        session.get(ApiKey, key2["id"]).expires_at = datetime.now(UTC) - timedelta(
            seconds=1
        )
    with session_factory.begin() as session:
        with pytest.raises(AuthenticationFailed):
            authenticate_token(key2["secret"], session)


def test_recent_assurance_idle_timeout_and_reauthentication(
    credentials, session_factory
):
    service, raw, principal, _ = credentials
    with session_factory.begin() as session:
        session.get(
            BrowserSession, principal.credential_id
        ).authenticated_at -= timedelta(minutes=11)
    with pytest.raises(AuthorizationDenied):
        service.create_key(principal, "needs reauthentication")
    replacement = service.reauthenticate(principal, "Example-password-42")
    with session_factory.begin() as session:
        with pytest.raises(AuthenticationFailed):
            authenticate_session(raw, session)
        assert authenticate_session(replacement, session).user_id == principal.user_id
    service.create_key(principal, "works")
    with session_factory.begin() as session:
        session.get(BrowserSession, principal.credential_id).last_seen_at -= timedelta(
            hours=25
        )
    with session_factory.begin() as session:
        with pytest.raises(AuthenticationFailed):
            authenticate_session(replacement, session)


def test_rotation_is_bounded_and_reset_revokes_both_credential_types(
    credentials, session_factory
):
    service, raw, principal, mailbox = credentials
    key = service.create_key(principal, "rotate me")
    replacement = service.rotate_key(principal, key["id"], overlap_hours=0)
    with session_factory.begin() as session:
        with pytest.raises(AuthenticationFailed):
            authenticate_token(key["secret"], session)
        assert (
            authenticate_token(replacement["secret"], session).user_id
            == principal.user_id
        )
    service.accounts.request_reset("credential@example.org")
    service.accounts.complete_reset(
        mailbox.messages[-1].split()[-1], "Changed-password-42"
    )
    with session_factory.begin() as session:
        with pytest.raises(AuthenticationFailed):
            authenticate_token(replacement["secret"], session)
        with pytest.raises(AuthenticationFailed):
            authenticate_session(raw, session)


def test_verified_primary_email_and_live_key_limit(credentials, session_factory):
    service, _, principal, _ = credentials
    with session_factory.begin() as session:
        session.scalar(select(EmailAddress)).is_verified = False
    with pytest.raises(AuthorizationDenied):
        service.create_key(principal, "unverified")
    with session_factory.begin() as session:
        session.scalar(select(EmailAddress)).is_verified = True
    for number in range(10):
        service.create_key(principal, f"key {number}")
    with pytest.raises(ValueError, match="Revoke"):
        service.create_key(principal, "too many")


def test_refresh_uses_stored_scopes_and_rechecks_original_credential(
    credentials, session_factory
):
    from pkdb_server.services.authentication import revalidate_principal

    service, _, principal, _ = credentials
    key = service.create_key(principal, "read only")
    with session_factory.begin() as session:
        actor = authenticate_token(key["secret"], session)
        forged = actor.model_copy(
            update={"scopes": frozenset({"read", "studies:write"})}
        )
        assert revalidate_principal(forged, session, lock=True).scopes == frozenset(
            {"read"}
        )
    service.revoke_key(principal, key["id"])
    with session_factory.begin() as session:
        with pytest.raises(AuthenticationFailed):
            revalidate_principal(actor, session, lock=True)


def test_password_admin_can_export_and_read_own_staged_files(
    credentials, session_factory, tmp_path
):
    import io

    from pkdb.schemas.queries import QuerySpec
    from pkdb_server.files.store import FileStore
    from pkdb_server.services.exports import ExportService

    _, _, principal, _ = credentials
    files = FileStore(tmp_path / "staged", session_factory, 1024)
    staged = files.stage(
        principal, "private.csv", io.BytesIO(b"private scientific data")
    )
    with session_factory.begin() as session:
        session.get(User, principal.user_id).role = "admin"
    exports = ExportService(session_factory)
    assert exports.create_filter(QuerySpec(entity="studies"), principal) is not None
    with files.open_authorized(principal, staged.id) as stream:
        assert stream.read() == b"private scientific data"


def test_authenticated_account_actions_have_no_rate_limit(credentials):
    service, _, principal, _ = credentials
    for _ in range(11):
        assert service.reauthenticate(principal, "Example-password-42")
    for _ in range(4):
        assert (
            service.accounts.add_email(principal, "secondary@example.org")["email"]
            == "secondary@example.org"
        )
    with pytest.raises(AuthenticationFailed):
        service.reauthenticate(principal, "incorrect-password")
