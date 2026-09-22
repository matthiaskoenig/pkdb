from datetime import UTC, datetime, timedelta

import pyotp
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from pkdb.db.models.security import SecurityConfiguration
from pkdb.db.models.users import User
from pkdb.schemas.security import Principal
from pkdb.services.accounts import AccountService
from pkdb.services.authentication import AuthenticationFailed, password_hash
from pkdb.services.authorization import AuthorizationDenied
from pkdb.services.credentials import CredentialService, authenticate_session
from pkdb.services.mfa import MfaService, require_admin_session
from pkdb.services.quotas import QuotaExceeded, QuotaService


class Mailbox:
    def send(self, recipient: str, subject: str, body: str) -> None:
        pass


def test_administrator_mfa_rotation_and_replay(session_factory):
    accounts = AccountService(session_factory, Mailbox())
    credentials = CredentialService(session_factory, accounts)
    mfa = MfaService(session_factory, accounts, Fernet.generate_key().decode())
    with session_factory.begin() as session:
        user = User(
            username="mkoenig",
            role="admin",
            active=True,
            password_hash=password_hash.hash("Admin-password-42!"),
        )
        session.add(user)
        session.flush()
        config = session.get(SecurityConfiguration, 1)
        if config is None:
            config = SecurityConfiguration(id=1)
            session.add(config)
        config.designated_administrator_id = user.id
    raw, principal = credentials.login("mkoenig", "Admin-password-42!")
    with session_factory() as session:
        with pytest.raises(AuthorizationDenied):
            require_admin_session(principal, session)
    enrollment = mfa.enroll(principal)
    code = pyotp.TOTP(enrollment["secret"]).now()
    result, new_raw = mfa.verify(principal, code, confirm=True)
    assert len(result["recovery_codes"]) == 10
    with session_factory.begin() as session:
        with pytest.raises(AuthenticationFailed):
            authenticate_session(raw, session)
        principal = authenticate_session(new_raw, session)
        assert require_admin_session(principal, session).username == "mkoenig"
    with pytest.raises(AuthenticationFailed):
        mfa.verify(principal, code)
    result2, new_raw = mfa.verify(principal, result["recovery_codes"][0])
    assert result2 == {}
    with session_factory.begin() as session:
        principal = authenticate_session(new_raw, session)
    with pytest.raises(AuthenticationFailed):
        mfa.verify(principal, result["recovery_codes"][0])


def test_account_quota_shared_across_keys_and_service_instances(session_factory):
    quotas = QuotaService(session_factory)
    other = QuotaService(session_factory)
    for index in range(120):
        p = Principal(
            user_id=42,
            role="user",
            credential_kind="api_key",
            credential_id=index // 40,
            scopes=frozenset({"read"}),
        )
        quotas.charge(p, "test-ip")
    with pytest.raises(QuotaExceeded) as error:
        other.charge(p.model_copy(update={"credential_id": 99}), "other-ip")
    assert 0 < error.value.retry_after <= 60
    assert quotas.usage(42)["account"]["requests"] == 120


def test_anonymous_bulk_export_denied(session_factory):
    with pytest.raises(QuotaExceeded):
        QuotaService(session_factory).charge(Principal(), "test-ip", "export")


def test_shared_work_leases_release_and_expire(session_factory):
    from pkdb.db.models.limits import WorkLease

    quotas = QuotaService(session_factory)
    principal = Principal(user_id=42, role="curator")
    lease = quotas.acquire(principal, "ip", "upload")
    with pytest.raises(QuotaExceeded):
        QuotaService(session_factory).acquire(principal, "different-ip", "upload")
    quotas.release(lease)
    lease = quotas.acquire(principal, "ip", "upload")
    with session_factory.begin() as session:
        for row in session.scalars(
            select(WorkLease).where(WorkLease.request_id == lease)
        ):
            row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    lease2 = quotas.acquire(principal, "ip", "upload")
    quotas.release(lease2)
