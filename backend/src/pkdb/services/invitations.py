"""Explicit administrator invitations bound to an existing identity and contact."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from pkdb.db.models.audit import AuditEvent
from pkdb.db.models.users import EmailAddress, Token, User
from pkdb.services.accounts import AccountService, MailDeliveryFailed
from pkdb.services.admin_users import require_admin
from pkdb.services.authentication import AuthenticationFailed, password_hash


class InvitationService:
    def __init__(self, session_factory, mailer, clock=None):
        self.session_factory = session_factory
        self.mailer = mailer
        self.clock = clock or (lambda: datetime.now(UTC))

    def issue(self, principal, user_id: int, email_id: int):
        """Send only through an explicit administrator action after roster review."""
        now = self.clock()
        with self.session_factory.begin() as session:
            user = require_admin(principal, session, target_id=user_id)
            if user is None:
                raise LookupError("User not found")
            # Inactive accounts with credentials may be suspended. Invitations are
            # for unclaimed attribution/import identities, never reactivation.
            if (
                user.active
                or user.password_hash
                or user.role == "admin"
                or user.suspended_at is not None
            ):
                raise ValueError(
                    "Only unclaimed non-administrator accounts can be invited"
                )
            email = session.scalar(
                select(EmailAddress)
                .where(
                    EmailAddress.id == email_id,
                    EmailAddress.user_id == user.id,
                )
                .with_for_update()
            )
            if email is None or email.email != user.email or not email.is_primary:
                raise ValueError("Invitation requires the reviewed primary contact")
            session.execute(
                update(Token)
                .where(
                    Token.user_id == user.id,
                    Token.purpose == "invite",
                    Token.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )
            raw = secrets.token_urlsafe(32)
            session.add(
                Token(
                    user_id=user.id,
                    email_id=email.id,
                    purpose="invite",
                    digest=hashlib.sha256(raw.encode()).hexdigest(),
                    expires_at=now + timedelta(days=7),
                )
            )
            user.pending_verification = True
            session.flush()
            try:
                self.mailer.send(
                    email.email,
                    "Your PK-DB account invitation",
                    f"An administrator invited you to claim your existing PK-DB account {user.username}. "
                    f"Your one-use invitation token (valid for 7 days): {raw}",
                )
            except Exception as error:
                raise MailDeliveryFailed(
                    "Invitation email could not be delivered; retry"
                ) from error
            session.add(
                AuditEvent(
                    actor_id=principal.user_id,
                    action="invitation.sent",
                    target=f"user:{user.id}",
                    details={"email_id": email.id},
                )
            )
            return {
                "user_id": user.id,
                "delivery": "sent",
                "expires_at": now + timedelta(days=7),
            }

    def accept(self, raw: str, password: str):
        if not raw or len(raw) > 1024:
            raise AuthenticationFailed("Invalid invitation")
        AccountService._password(password)
        encoded = password_hash.hash(password)
        with self.session_factory.begin() as session:
            user = self.claim(session, raw, self.clock())
            user.password_hash = encoded
            return {"user_id": user.id, "username": user.username}

    @staticmethod
    def claim(session, raw, now):
        """Claim an invitation within the caller's atomic credential transaction."""
        if not raw or len(raw) > 1024:
            raise AuthenticationFailed("Invalid invitation")
        digest = hashlib.sha256(raw.encode()).hexdigest()
        lookup = session.scalar(select(Token).where(Token.digest == digest))
        if lookup is None:
            raise AuthenticationFailed("Invalid invitation")
        # User before token lock follows password-reset/suspension ordering.
        user = session.scalar(
            select(User).where(User.id == lookup.user_id).with_for_update()
        )
        token = session.scalar(
            select(Token)
            .where(Token.digest == digest)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if (
            user is None
            or token is None
            or token.purpose != "invite"
            or token.revoked_at is not None
            or token.expires_at <= now
            or user.active
            or user.password_hash
            or user.suspended_at is not None
            or not user.pending_verification
            or user.role == "admin"
        ):
            raise AuthenticationFailed("Invalid invitation")
        email = session.get(EmailAddress, token.email_id)
        if (
            email is None
            or email.user_id != user.id
            or not email.is_primary
            or email.email != user.email
        ):
            raise AuthenticationFailed("Invalid invitation")
        token.revoked_at = now
        user.active = True
        user.pending_verification = False
        email.is_verified = True
        # Outstanding invites/verification/reset actions cannot mutate the
        # newly claimed account. The caller controls credential/session issuance.
        session.execute(
            update(Token)
            .where(Token.user_id == user.id, Token.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        session.add(
            AuditEvent(
                actor_id=user.id,
                action="invitation.accepted",
                target=f"user:{user.id}",
                details={"email_id": email.id},
            )
        )
        return user
