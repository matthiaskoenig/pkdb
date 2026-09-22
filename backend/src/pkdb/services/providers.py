"""OAuth login with stable subjects and explicit, session-bound account linking."""

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta

from authlib.integrations.requests_client import OAuth2Session
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError

from pkdb.db.models.credentials import BrowserSession
from pkdb.db.models.mfa import AuditEvent
from pkdb.db.models.providers import ExternalIdentity, OAuthTransaction
from pkdb.db.models.users import EmailAddress, User
from pkdb.schemas.accounts import EmailRequest
from pkdb.schemas.profiles import ProfileUpdate
from pkdb.services.authentication import AuthenticationFailed
from pkdb.services.authorization import AuthorizationDenied
from pkdb.services.credentials import digest, require_session

PROVIDERS = {
    "github": {
        "issuer": "https://github.com",
        "authorize": "https://github.com/login/oauth/authorize",
        "token": "https://github.com/login/oauth/access_token",
        "scope": "read:user",
    },
    "orcid": {
        "issuer": "https://orcid.org",
        "authorize": "https://orcid.org/oauth/authorize",
        "token": "https://orcid.org/oauth/token",
        "scope": "/authenticate",
    },
}


class ProviderService:
    def __init__(
        self,
        session_factory,
        accounts,
        *,
        origin,
        providers,
        client_factory=OAuth2Session,
    ):
        self.session_factory = session_factory
        self.accounts = accounts
        self.origin = origin.rstrip("/")
        self.providers = providers
        self.client_factory = client_factory

    def enabled(self):
        return [
            name
            for name in PROVIDERS
            if self.providers.get(name, {}).get("client_id")
            and self.providers.get(name, {}).get("client_secret")
        ]

    def _client(self, provider):
        if provider not in self.enabled():
            raise LookupError("Provider unavailable")
        config = self.providers[provider]
        return self.client_factory(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            redirect_uri=f"{self.origin}/api/v1/auth/{provider}/callback",
            scope=PROVIDERS[provider]["scope"],
            token_endpoint_auth_method="client_secret_post",
            code_challenge_method="S256" if provider == "github" else None,
            default_timeout=15,
        )

    def start(self, provider, *, principal=None, intent="login"):
        if intent not in {"login", "link", "reauthenticate"}:
            raise ValueError("Invalid provider intent")
        state, browser, verifier = (secrets.token_urlsafe(32) for _ in range(3))
        with self._client(provider) as client:
            kwargs = {"code_verifier": verifier} if provider == "github" else {}
            url, _ = client.create_authorization_url(
                PROVIDERS[provider]["authorize"], state=state, **kwargs
            )
        with self.session_factory.begin() as session:
            session.execute(
                delete(OAuthTransaction).where(
                    OAuthTransaction.expires_at <= datetime.now(UTC)
                )
            )
            user_id = session_id = None
            if intent != "login":
                if principal is None:
                    raise AuthenticationFailed("Session required")
                user, credential = require_session(
                    principal, session, recent=intent == "link", lock=True
                )
                if user.role == "admin" and intent == "link":
                    from pkdb.services.mfa import require_admin_session

                    require_admin_session(principal, session)
                user_id, session_id = user.id, credential.id
            session.add(
                OAuthTransaction(
                    digest=digest(state),
                    browser_digest=digest(browser),
                    provider=provider,
                    intent=intent,
                    user_id=user_id,
                    session_id=session_id,
                    code_verifier=verifier,
                    expires_at=datetime.now(UTC) + timedelta(minutes=10),
                )
            )
        return url, browser

    def _exchange(self, provider, code, verifier):
        with self._client(provider) as client:
            kwargs = {"code_verifier": verifier} if provider == "github" else {}
            token = client.fetch_token(
                PROVIDERS[provider]["token"],
                code=code,
                headers={"Accept": "application/json"},
                allow_redirects=False,
                **kwargs,
            )
            if provider == "github":
                response = client.get(
                    "https://api.github.com/user",
                    headers={"Accept": "application/vnd.github+json"},
                    allow_redirects=False,
                )
                response.raise_for_status()
                user = response.json()
                if (
                    not isinstance(user.get("id"), int)
                    or user["id"] <= 0
                    or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", user.get("login", ""))
                ):
                    raise AuthenticationFailed("Invalid provider identity")
                return {"subject": str(user["id"]), "label": user["login"]}
            # ORCID /authenticate returns the authenticated iD directly from its
            # confidential authorization-code exchange. Never trust browser input.
            subject = token.get("orcid", "")
            if not re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", subject):
                raise AuthenticationFailed("Invalid provider identity")
            subject = ProfileUpdate.orcid_identifier(subject)
            return {"subject": subject, "label": subject}

    def callback(self, provider, state, browser, code, *, principal=None):
        if not all((state, browser, code)) or any(
            len(value) > 2048 for value in (state, browser, code)
        ):
            raise AuthenticationFailed("Invalid OAuth transaction")
        now = datetime.now(UTC)
        with self.session_factory.begin() as session:
            tx = session.scalar(
                select(OAuthTransaction)
                .where(
                    OAuthTransaction.digest == digest(state),
                    OAuthTransaction.browser_digest == digest(browser),
                    OAuthTransaction.provider == provider,
                    OAuthTransaction.expires_at > now,
                    OAuthTransaction.consumed_at.is_(None),
                )
                .with_for_update()
            )
            if tx is None:
                raise AuthenticationFailed("Invalid OAuth transaction")
            tx.consumed_at = now
            identifier, verifier = tx.id, tx.code_verifier
            tx.code_verifier = ""
        identity = self._exchange(provider, code, verifier)
        try:
            with self.session_factory.begin() as session:
                tx = session.get(OAuthTransaction, identifier)
                now = datetime.now(UTC)
                if tx is None or tx.expires_at <= now:
                    raise AuthenticationFailed("OAuth transaction expired")
                linked = session.scalar(
                    select(ExternalIdentity).where(
                        ExternalIdentity.provider == provider,
                        ExternalIdentity.issuer == PROVIDERS[provider]["issuer"],
                        ExternalIdentity.subject == identity["subject"],
                    )
                )
                if tx.intent != "login":
                    if (
                        principal is None
                        or principal.user_id != tx.user_id
                        or principal.credential_id != tx.session_id
                    ):
                        raise AuthenticationFailed("Original browser session required")
                    user, credential = require_session(
                        principal, session, recent=tx.intent == "link", lock=True
                    )
                    if tx.intent == "link":
                        if user.role == "admin":
                            from pkdb.services.mfa import require_admin_session

                            require_admin_session(principal, session)
                        if linked is not None:
                            raise ValueError("Identity is already linked")
                        self._link(session, user, provider, identity)
                        return {"status": "linked"}
                    if linked is None or linked.user_id != user.id:
                        raise AuthenticationFailed("Linked identity required")
                    raw = secrets.token_urlsafe(32)
                    credential.digest = digest(raw)
                    credential.authenticated_at = now
                    return {"status": "authenticated", "session": raw}
                if linked is not None:
                    user = session.scalar(
                        select(User).where(User.id == linked.user_id).with_for_update()
                    )
                    if not user.active or user.pending_verification:
                        raise AuthenticationFailed("Account is not active")
                    return {
                        "status": "authenticated",
                        "session": self._session(session, user, now),
                    }
                raw = secrets.token_urlsafe(32)
                tx.identity = identity
                tx.onboarding_digest = digest(raw)
                return {"status": "onboarding", "onboarding": raw}
        except IntegrityError as error:
            raise ValueError("Identity is already linked") from error

    @staticmethod
    def _session(session, user, now):
        raw = secrets.token_urlsafe(32)
        session.add(
            BrowserSession(
                user_id=user.id,
                digest=digest(raw),
                last_seen_at=now,
                authenticated_at=now,
                expires_at=now + timedelta(days=7),
                device="Provider login",
            )
        )
        return raw

    @staticmethod
    def _link(session, user, provider, identity):
        session.add(
            ExternalIdentity(
                user_id=user.id,
                provider=provider,
                issuer=PROVIDERS[provider]["issuer"],
                subject=identity["subject"],
                label=identity["label"],
            )
        )
        setattr(user, provider, identity["label"])
        setattr(user, f"{provider}_provenance", "authenticated")
        session.add(
            AuditEvent(
                actor_id=user.id, action="identity.link", target=provider, details={}
            )
        )

    def onboarding(self, raw, browser, *, username=None, email=None):
        if not raw or not browser:
            raise AuthenticationFailed("Onboarding required")
        with self.session_factory.begin() as session:
            tx = session.scalar(
                select(OAuthTransaction)
                .where(
                    OAuthTransaction.onboarding_digest == digest(raw),
                    OAuthTransaction.browser_digest == digest(browser),
                    OAuthTransaction.expires_at > datetime.now(UTC),
                )
                .with_for_update()
            )
            if tx is None or not tx.identity:
                raise AuthenticationFailed("Onboarding expired")
            if username is None:
                return {"provider": tx.provider, "label": tx.identity["label"]}
            username = username.strip()
            if (
                not re.fullmatch(r"[A-Za-z0-9_.-]{1,150}", username)
                or username.casefold() == "mkoenig"
            ):
                raise ValueError("Username unavailable")
            if email is None:
                raise ValueError("Contact email required")
            address = EmailRequest(email=email.strip()).email.casefold()
            lock = int.from_bytes(
                hashlib.sha256(
                    f"register-user:{username.casefold()}".encode()
                ).digest()[:8],
                "big",
                signed=True,
            )
            session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock})
            if (
                session.scalar(
                    select(User.id).where(
                        func.lower(User.username) == username.casefold()
                    )
                )
                is not None
            ):
                raise ValueError(
                    "Username unavailable; sign in to link an existing account"
                )
            if (
                session.scalar(
                    select(EmailAddress.id).where(EmailAddress.email == address)
                )
                is not None
                or session.scalar(
                    select(User.id).where(func.lower(User.email) == address)
                )
                is not None
            ):
                raise ValueError(
                    "Account cannot be created; sign in to link an existing account"
                )
            user = User(
                username=username,
                email=address,
                role="user",
                active=False,
                pending_verification=True,
            )
            session.add(user)
            session.flush()
            entry = EmailAddress(
                user_id=user.id, email=address, is_primary=True, is_verified=False
            )
            session.add(entry)
            session.flush()
            self._link(session, user, tx.provider, tx.identity)
            self.accounts._send_token(user, "verify_email", session, entry)
            tx.onboarding_digest = None
            tx.identity = None
            return {"status": "verification_required"}

    def accept_invitation(self, raw, browser, token):
        """Bind a proven provider identity to the exact emailed invitation account."""
        from pkdb.services.invitations import InvitationService

        if not raw or not browser:
            raise AuthenticationFailed("Onboarding required")
        now = datetime.now(UTC)
        with self.session_factory.begin() as session:
            tx = session.scalar(
                select(OAuthTransaction)
                .where(
                    OAuthTransaction.onboarding_digest == digest(raw),
                    OAuthTransaction.browser_digest == digest(browser),
                    OAuthTransaction.expires_at > now,
                    OAuthTransaction.intent == "login",
                )
                .with_for_update()
            )
            if tx is None or not tx.identity:
                raise AuthenticationFailed("Onboarding expired")
            linked = session.scalar(
                select(ExternalIdentity.id).where(
                    ExternalIdentity.provider == tx.provider,
                    ExternalIdentity.issuer == PROVIDERS[tx.provider]["issuer"],
                    ExternalIdentity.subject == tx.identity["subject"],
                )
            )
            if linked is not None:
                raise ValueError("Identity is already linked")
            user = InvitationService.claim(session, token, now)
            self._link(session, user, tx.provider, tx.identity)
            tx.onboarding_digest = None
            tx.identity = None
            return {
                "status": "authenticated",
                "user_id": user.id,
                "username": user.username,
                "session": self._session(session, user, now),
            }

    def identities(self, principal):
        with self.session_factory.begin() as session:
            require_session(principal, session)
            return [
                {
                    "id": row.id,
                    "provider": row.provider,
                    "subject": row.subject,
                    "label": row.label,
                    "linked_at": row.created_at,
                }
                for row in session.scalars(
                    select(ExternalIdentity).where(
                        ExternalIdentity.user_id == principal.user_id
                    )
                )
            ]

    def unlink(self, principal, identifier):
        with self.session_factory.begin() as session:
            user, _ = require_session(principal, session, recent=True, lock=True)
            if user.role == "admin":
                from pkdb.services.mfa import require_admin_session

                require_admin_session(principal, session)
            identities = list(
                session.scalars(
                    select(ExternalIdentity).where(ExternalIdentity.user_id == user.id)
                )
            )
            row = next(
                (identity for identity in identities if identity.id == identifier), None
            )
            if row is None:
                raise LookupError("Identity not found")
            if len(identities) <= 1 and not user.password_hash:
                raise AuthorizationDenied("Keep at least one usable sign-in method")
            setattr(user, f"{row.provider}_provenance", "self_asserted")
            session.add(
                AuditEvent(
                    actor_id=user.id,
                    action="identity.unlink",
                    target=row.provider,
                    details={},
                )
            )
            session.delete(row)
