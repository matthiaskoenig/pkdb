"""Transactional account actions with one-use tokens and PostgreSQL throttles."""

import hashlib
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from pkdb.db.models.users import AccountThrottle, EmailAddress, Token, User
from pkdb.schemas.security import Principal
from pkdb.services.authentication import (
    AuthenticationFailed,
    issue_token,
    password_hash,
)


class Mailer(Protocol):
    def send(self, recipient: str, subject: str, body: str) -> None: ...


class AccountThrottled(ValueError):
    pass


class MailDeliveryFailed(RuntimeError):
    pass


class AccountService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        mailer: Mailer,
        clock: Callable[[], datetime] | None = None,
    ):
        self.session_factory = session_factory
        self.mailer = mailer
        self.clock = clock or (lambda: datetime.now(UTC))
        self._dummy_hash = password_hash.hash(secrets.token_urlsafe(32))

    def _throttle(
        self, action: str, identity: str, limit: int, window: timedelta
    ) -> None:
        key = hashlib.sha256(f"{action}:{identity.casefold()}".encode()).hexdigest()
        lock = int.from_bytes(bytes.fromhex(key)[:8], "big", signed=True)
        now = self.clock()
        with self.session_factory.begin() as session:
            session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock})
            session.execute(
                delete(AccountThrottle).where(AccountThrottle.expires_at <= now)
            )
            row = session.get(AccountThrottle, key)
            if row is None:
                session.add(
                    AccountThrottle(key=key, attempts=1, expires_at=now + window)
                )
            elif row.attempts >= limit:
                raise AccountThrottled("Too many account attempts")
            else:
                row.attempts += 1

    @staticmethod
    def _password(password: str) -> None:
        if len(password) < 8 or len(password) > 1024:
            raise ValueError("Password must contain between 8 and 1024 characters")

    def login(self, username: str, password: str) -> str:
        self._throttle("login", username, 10, timedelta(minutes=10))
        with self.session_factory.begin() as session:
            user = session.scalar(
                select(User).where(User.username == username).with_for_update()
            )
            encoded = (
                user.password_hash if user and user.password_hash else self._dummy_hash
            )
            try:
                valid = password_hash.verify(password, encoded)
            except ValueError, TypeError:
                valid = False
            if not valid or user is None or not user.active:
                raise AuthenticationFailed("Invalid credentials")
            return issue_token(user, session)

    def _send_token(
        self,
        user: User,
        purpose: str,
        session: Session,
        email: EmailAddress | None = None,
    ) -> None:
        raw = secrets.token_urlsafe(32)
        recipient = email.email if email else user.email
        if not recipient:
            raise ValueError("Email address required")
        session.add(
            Token(
                user_id=user.id,
                email_id=email.id if email else None,
                digest=hashlib.sha256(raw.encode()).hexdigest(),
                purpose=purpose,
                expires_at=self.clock() + timedelta(hours=1),
            )
        )
        session.flush()
        try:
            self.mailer.send(
                recipient,
                "PK-DB account verification"
                if purpose == "verify_email"
                else "PK-DB password reset",
                f"Your one-use {purpose} token: {raw}",
            )
        except Exception as error:
            raise MailDeliveryFailed(
                "Account email could not be delivered; retry"
            ) from error

    def request_reset(self, email: str) -> None:
        address = email.strip().casefold()
        self._throttle("reset", address, 3, timedelta(hours=1))
        with self.session_factory.begin() as session:
            entry = session.scalar(
                select(EmailAddress).where(
                    EmailAddress.email == address, EmailAddress.is_verified.is_(True)
                )
            )
            if entry is not None:
                user = session.scalar(
                    select(User)
                    .where(User.id == entry.user_id, User.active.is_(True))
                    .with_for_update()
                )
                if user is not None:
                    self._send_token(user, "reset_password", session, entry)

    def _consume(self, raw: str, purpose: str, session: Session) -> tuple[User, Token]:
        if not raw or len(raw) > 1024:
            raise AuthenticationFailed("Invalid account token")
        digest = hashlib.sha256(raw.encode()).hexdigest()
        lookup = session.scalar(select(Token).where(Token.digest == digest))
        if lookup is None:
            raise AuthenticationFailed("Invalid account token")
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
            or token.purpose != purpose
            or token.revoked_at is not None
            or token.expires_at <= self.clock()
        ):
            raise AuthenticationFailed("Invalid account token")
        token.revoked_at = self.clock()
        return user, token

    def complete_reset(self, token: str, new_password: str) -> None:
        self._password(new_password)
        encoded = password_hash.hash(new_password)
        with self.session_factory.begin() as session:
            user, _ = self._consume(token, "reset_password", session)
            if not user.active:
                raise AuthenticationFailed("Inactive account")
            user.password_hash = encoded
            session.execute(
                update(Token)
                .where(Token.user_id == user.id, Token.revoked_at.is_(None))
                .values(revoked_at=self.clock())
            )

    def register(self, username: str, email: str, password: str) -> None:
        self._password(password)
        if not username or len(username) > 150 or "@" not in email or len(email) > 320:
            raise ValueError("Valid username and email required")
        address = email.strip().casefold()
        self._throttle("register", address, 3, timedelta(hours=1))
        encoded = password_hash.hash(password)
        try:
            with self.session_factory.begin() as session:
                if (
                    session.scalar(
                        select(EmailAddress.id).where(EmailAddress.email == address)
                    )
                    is not None
                    or session.scalar(select(User.id).where(User.email == address))
                    is not None
                ):
                    return
                user = User(
                    username=username,
                    email=address,
                    role="user",
                    active=False,
                    pending_verification=True,
                    password_hash=encoded,
                )
                session.add(user)
                session.flush()
                entry = EmailAddress(
                    user_id=user.id, email=address, is_primary=True, is_verified=False
                )
                session.add(entry)
                session.flush()
                self._send_token(user, "verify_email", session, entry)
        except IntegrityError as error:
            raise ValueError("Username or email is unavailable") from error

    def verify_email(self, token: str) -> str:
        with self.session_factory.begin() as session:
            user, action = self._consume(token, "verify_email", session)
            email = session.get(EmailAddress, action.email_id)
            if email is None or email.user_id != user.id:
                raise AuthenticationFailed("Invalid verification token")
            email.is_verified = True
            if user.pending_verification:
                user.active = True
                user.pending_verification = False
            address = email.email
        return address

    def resend_verification(self, email: str) -> None:
        address = email.strip().casefold()
        self._throttle("verify", address, 3, timedelta(hours=1))
        with self.session_factory.begin() as session:
            entry = session.scalar(
                select(EmailAddress).where(
                    EmailAddress.email == address, EmailAddress.is_verified.is_(False)
                )
            )
            if entry is not None:
                user = session.scalar(
                    select(User).where(User.id == entry.user_id).with_for_update()
                )
                if user is not None:
                    self._send_token(user, "verify_email", session, entry)

    @staticmethod
    def _email_data(entry: EmailAddress) -> dict:
        return {
            "id": entry.id,
            "created_at": entry.created_at.isoformat(),
            "email": entry.email,
            "is_primary": entry.is_primary,
            "is_verified": entry.is_verified,
        }

    @staticmethod
    def _account(session: Session, principal: Principal) -> User:
        user = session.scalar(
            select(User)
            .where(User.id == principal.user_id, User.active.is_(True))
            .with_for_update()
        )
        if user is None:
            raise AuthenticationFailed("Inactive account")
        return user

    def emails(self, principal: Principal, email_id: int | None = None):
        with self.session_factory.begin() as session:
            user = self._account(session, principal)
            query = select(EmailAddress).where(EmailAddress.user_id == user.id)
            if email_id is not None:
                entry = session.scalar(query.where(EmailAddress.id == email_id))
                if entry is None:
                    raise LookupError("Email not found")
                return self._email_data(entry)
            return [
                self._email_data(entry)
                for entry in session.scalars(query.order_by(EmailAddress.id))
            ]

    def add_email(self, principal: Principal, email: str, is_primary: bool = False):
        if is_primary:
            raise ValueError("Unverified email cannot be primary")
        address = email.strip().casefold()
        self._throttle("add_email", str(principal.user_id), 3, timedelta(hours=1))
        try:
            with self.session_factory.begin() as session:
                user = self._account(session, principal)
                existing = session.scalar(
                    select(EmailAddress).where(EmailAddress.email == address)
                )
                if existing is not None:
                    # Do not disclose another account's ownership or verification state.
                    return {
                        "id": None,
                        "created_at": None,
                        "email": address,
                        "is_primary": False,
                        "is_verified": False,
                    }
                entry = EmailAddress(
                    user_id=user.id, email=address, is_primary=False, is_verified=False
                )
                session.add(entry)
                session.flush()
                self._send_token(user, "verify_email", session, entry)
                return self._email_data(entry)
        except IntegrityError as error:
            raise ValueError("Email request unavailable") from error

    def change_email(
        self, principal: Principal, email_id: int, values: dict, remove: bool = False
    ):
        with self.session_factory.begin() as session:
            user = self._account(session, principal)
            entry = session.scalar(
                select(EmailAddress).where(
                    EmailAddress.user_id == user.id, EmailAddress.id == email_id
                )
            )
            if entry is None:
                raise LookupError("Email not found")
            if remove:
                if entry.is_primary:
                    user.email = None
                session.delete(entry)
                return None
            if "email" in values and values["email"].strip().casefold() != entry.email:
                raise ValueError("Existing emails may not be edited")
            if values.get("is_primary"):
                if not entry.is_verified:
                    raise ValueError("Unverified email cannot be primary")
                session.execute(
                    update(EmailAddress)
                    .where(EmailAddress.user_id == user.id)
                    .values(is_primary=False)
                )
                entry.is_primary = True
                user.email = entry.email
            return self._email_data(entry)
