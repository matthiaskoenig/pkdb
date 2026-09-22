"""Administrator MFA, without an email-only bypass."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import pyotp
from cryptography.fernet import Fernet
from sqlalchemy import select

from pkdb.db.models.mfa import AuditEvent, MfaCredential
from pkdb.db.models.security import SecurityConfiguration
from pkdb.services.authentication import AuthenticationFailed
from pkdb.services.authorization import AuthorizationDenied
from pkdb.services.credentials import digest, require_session


def require_admin_session(principal, session):
    user, credential = require_session(principal, session, recent=True, lock=True)
    config = session.get(SecurityConfiguration, 1)
    if (
        user.role != "admin"
        or config is None
        or config.designated_administrator_id != user.id
        or credential.mfa_at is None
        or credential.mfa_at <= datetime.now(UTC) - timedelta(minutes=10)
    ):
        raise AuthorizationDenied("Designated administrator with recent MFA required")
    return user


class MfaService:
    def __init__(self, session_factory, accounts, encryption_key):
        self.session_factory = session_factory
        self.accounts = accounts
        self.cipher = Fernet(encryption_key.encode()) if encryption_key else None

    def _actor(self, principal, session):
        user, credential = require_session(principal, session, recent=True)
        config = session.get(SecurityConfiguration, 1)
        if (
            user.role != "admin"
            or config is None
            or config.designated_administrator_id != user.id
        ):
            raise AuthorizationDenied("Designated administrator required")
        return user, credential

    def enroll(self, principal):
        if self.cipher is None:
            raise ValueError("MFA encryption key is not configured")
        with self.session_factory.begin() as session:
            user, credential = self._actor(principal, session)
            row = session.scalar(
                select(MfaCredential)
                .where(MfaCredential.user_id == user.id)
                .with_for_update()
            )
            if row is not None and row.confirmed:
                raise AuthorizationDenied("MFA is already enrolled")
            secret = pyotp.random_base32()
            if row is None:
                row = MfaCredential(user_id=user.id)
                session.add(row)
            row.encrypted_secret = self.cipher.encrypt(secret.encode()).decode()
            row.confirmed = False
            row.last_step = -1
            row.recovery_digests = []
            return {
                "secret": secret,
                "provisioning_uri": pyotp.TOTP(secret).provisioning_uri(
                    user.username, issuer_name="PK-DB"
                ),
            }

    def verify(self, principal, code, *, confirm=False):
        if self.cipher is None:
            raise ValueError("MFA encryption key is not configured")
        self.accounts._throttle("mfa", str(principal.user_id), 5, timedelta(minutes=10))
        with self.session_factory.begin() as session:
            user, credential = self._actor(principal, session)
            row = session.scalar(
                select(MfaCredential)
                .where(MfaCredential.user_id == user.id)
                .with_for_update()
            )
            if (
                row is None
                or (not confirm and not row.confirmed)
                or (confirm and row.confirmed)
            ):
                raise AuthenticationFailed("Invalid MFA state")
            now = datetime.now(UTC)
            step = int(now.timestamp()) // 30
            totp = pyotp.TOTP(
                self.cipher.decrypt(row.encrypted_secret.encode()).decode()
            )
            matched = next(
                (
                    s
                    for s in (step, step - 1, step + 1)
                    if s > row.last_step
                    and secrets.compare_digest(totp.at(s * 30), code)
                ),
                None,
            )
            recovery = hashlib.sha256(code.encode()).hexdigest()
            if matched is not None:
                row.last_step = matched
            elif not confirm and recovery in row.recovery_digests:
                row.recovery_digests = [
                    x for x in row.recovery_digests if x != recovery
                ]
            else:
                raise AuthenticationFailed("Invalid MFA code")
            result = {}
            if confirm:
                codes = [secrets.token_urlsafe(18) for _ in range(10)]
                row.recovery_digests = [
                    hashlib.sha256(x.encode()).hexdigest() for x in codes
                ]
                row.confirmed = True
                result["recovery_codes"] = codes
            credential.mfa_at = now
            credential.authenticated_at = now
            raw = secrets.token_urlsafe(32)
            credential.digest = digest(raw)
            session.add(
                AuditEvent(
                    actor_id=user.id,
                    action="mfa.confirm" if confirm else "mfa.verify",
                    target=str(user.id),
                )
            )
            return result, raw
