from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

import httpx2
import pytest
from authlib.integrations.httpx_client import OAuth2Client
from sqlalchemy import select

from pkdb.db.models.providers import ExternalIdentity, OAuthTransaction
from pkdb.db.models.users import User
from pkdb.services.accounts import AccountService
from pkdb.services.authentication import AuthenticationFailed, password_hash
from pkdb.services.authorization import AuthorizationDenied
from pkdb.services.credentials import CredentialService, authenticate_session
from pkdb.services.providers import ProviderService


class Mailbox:
    def __init__(self):
        self.messages = []

    def send(self, recipient, subject, body):
        self.messages.append(body)


@pytest.fixture
def provider_context(session_factory):
    mailbox = Mailbox()
    accounts = AccountService(session_factory, mailbox)
    calls = []

    def response(data):
        return httpx2.Response(200, json=data)

    def http(request):
        calls.append(request)
        if request.url.host == "api.github.com":
            return response(
                {
                    "id": 12345,
                    "login": "example-person",
                    "email": "existing@example.org",
                },
            )
        if request.url.host == "orcid.org":
            return response(
                {
                    "access_token": "provider-secret",
                    "token_type": "bearer",
                    "orcid": "0000-0002-1825-0097",
                },
            )
        return response({"access_token": "provider-secret", "token_type": "bearer"})

    def client_factory(**kwargs):
        return OAuth2Client(transport=httpx2.MockTransport(http), **kwargs)

    service = ProviderService(
        session_factory,
        accounts,
        origin="http://localhost:8080",
        providers={
            provider: {"client_id": "client", "client_secret": "secret"}
            for provider in ("github", "orcid")
        },
        client_factory=client_factory,
    )
    return service, accounts, mailbox, calls


def start(service, provider="github", **kwargs):
    url, browser = service.start(provider, **kwargs)
    return parse_qs(urlsplit(url).query)["state"][0], browser, url


def test_state_is_browser_bound_one_use_and_github_pkce(
    provider_context, session_factory
):
    service, _, _, calls = provider_context
    state, browser, url = start(service)
    params = parse_qs(urlsplit(url).query)
    assert params["code_challenge_method"] == ["S256"]
    with pytest.raises(AuthenticationFailed):
        service.callback("github", state, "another browser", "code")
    result = service.callback("github", state, browser, "code")
    assert result["status"] == "onboarding"
    assert "code_verifier" in parse_qs(calls[0].content.decode())
    with pytest.raises(AuthenticationFailed):
        service.callback("github", state, browser, "code")
    with session_factory.begin() as session:
        tx = session.scalar(select(OAuthTransaction))
        assert tx.code_verifier == ""
        assert "provider-secret" not in str(tx.identity)


def test_provider_registration_requires_contact_verification_and_ordinary_role(
    provider_context, session_factory
):
    service, accounts, mailbox, _ = provider_context
    state, browser, _ = start(service, "orcid")
    result = service.callback("orcid", state, browser, "code")
    with pytest.raises(ValueError):
        service.onboarding(
            result["onboarding"], browser, username="MKoenig", email="new@example.org"
        )
    result2 = service.onboarding(
        result["onboarding"], browser, username="newperson", email="new@example.org"
    )
    assert result2["status"] == "verification_required"
    with session_factory.begin() as session:
        user = session.scalar(select(User).where(User.username == "newperson"))
        assert user.role == "user" and user.pending_verification and not user.active
        assert user.password_hash is None
        assert user.orcid_provenance == "authenticated"
    state, browser, _ = start(service, "orcid")
    with pytest.raises(AuthenticationFailed):
        service.callback("orcid", state, browser, "code")
    accounts.verify_email(mailbox.messages[0].split()[-1])
    state, browser, _ = start(service, "orcid")
    result = service.callback("orcid", state, browser, "code")
    with session_factory.begin() as session:
        actor = authenticate_session(result["session"], session)
        assert actor.role == "user"
    with pytest.raises(AuthorizationDenied):
        service.unlink(actor, service.identities(actor)[0]["id"])


def test_matching_provider_email_never_merges_and_link_is_session_bound(
    provider_context, session_factory
):
    service, accounts, _, _ = provider_context
    with session_factory.begin() as session:
        session.add(
            User(
                username="existing",
                email="existing@example.org",
                role="curator",
                active=True,
                password_hash=password_hash.hash("Existing-password-42"),
            )
        )
    state, browser, _ = start(service)
    result = service.callback("github", state, browser, "code")
    assert result["status"] == "onboarding"
    with pytest.raises(ValueError):
        service.onboarding(
            result["onboarding"],
            browser,
            username="another",
            email="existing@example.org",
        )
    credentials = CredentialService(session_factory, accounts)
    _, principal = credentials.login("existing", "Existing-password-42")
    state, browser, _ = start(service, principal=principal, intent="link")
    with pytest.raises(AuthenticationFailed):
        service.callback("github", state, browser, "code")
    state, browser, _ = start(service, principal=principal, intent="link")
    assert (
        service.callback("github", state, browser, "code", principal=principal)[
            "status"
        ]
        == "linked"
    )
    identities = service.identities(principal)
    assert identities[0]["subject"] == "12345"
    state, browser, _ = start(service, principal=principal, intent="reauthenticate")
    assert (
        service.callback("github", state, browser, "code", principal=principal)[
            "status"
        ]
        == "authenticated"
    )
    service.unlink(principal, identities[0]["id"])
    with session_factory.begin() as session:
        assert session.scalar(select(ExternalIdentity)) is None


def invited_account(session_factory, **overrides):
    from datetime import UTC, datetime, timedelta

    from pkdb.db.models.users import EmailAddress, Token
    from pkdb.services.credentials import digest

    with session_factory.begin() as session:
        values = dict(
            username="imported",
            email="invited@example.org",
            role="reviewer",
            active=False,
            pending_verification=True,
        )
        values.update(overrides)
        user = User(**values)
        session.add(user)
        session.flush()
        email = EmailAddress(user_id=user.id, email=user.email, is_primary=True)
        session.add(email)
        session.flush()
        session.add(
            Token(
                user_id=user.id,
                email_id=email.id,
                purpose="invite",
                digest=digest("invitation-secret"),
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
        )
        return user.id


@pytest.fixture
def provider_http_client(ingestion_context, session_factory):
    from fastapi.testclient import TestClient

    from pkdb.app import create_app
    from pkdb.config import Settings

    ingestion, _ = ingestion_context
    settings = Settings(
        database_url=session_factory.kw["bind"].url.render_as_string(
            hide_password=False
        ),
        file_root=ingestion.file_store.root,
        rate_limits_enabled=False,
    )
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.mark.parametrize("provider", ["github", "orcid"])
def test_provider_invitation_http_claim_is_explicit_and_browser_bound(
    provider_http_client, provider_context, session_factory, provider
):
    from pkdb.db.models.users import EmailAddress

    client = provider_http_client
    service, _, mailbox, _ = provider_context
    client.app.state.providers = service
    user_id = invited_account(session_factory)
    response = client.get(f"/api/v1/auth/{provider}/start", follow_redirects=False)
    state = parse_qs(urlsplit(response.headers["location"]).query)["state"][0]
    response = client.get(
        f"/api/v1/auth/{provider}/callback?state={state}&code=code",
        follow_redirects=False,
    )
    assert response.headers["location"] == "/account?oauth=onboarding"
    with session_factory() as session:
        assert not session.get(User, user_id).active
    path = "/api/v1/auth/onboarding/invitation"
    assert client.post(path, json={"token": "invitation-secret"}).status_code == 403
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    headers = {"Origin": client.app.state.browser_origin, "X-CSRF-Token": csrf}
    onboarding = client.cookies.get("pkdb_dev_onboarding")
    browser = client.cookies.get("pkdb_dev_oauth")
    with pytest.raises(AuthenticationFailed):
        service.accept_invitation(onboarding, "wrong-browser", "invitation-secret")
    response = client.post(path, headers=headers, json={"token": "invitation-secret"})
    assert response.status_code == 200, response.text
    assert response.json() == {
        "status": "authenticated",
        "user_id": user_id,
        "username": "imported",
    }
    assert "session" not in response.json()
    with session_factory() as session:
        user = session.get(User, user_id)
        assert user.active and not user.pending_verification
        assert user.password_hash is None and user.role == "reviewer"
        assert session.scalar(
            select(EmailAddress).where(EmailAddress.user_id == user_id)
        ).is_verified
        assert session.scalar(select(ExternalIdentity)).user_id == user_id
        actor = authenticate_session(
            client.cookies.get(client.app.state.session_cookie_name), session
        )
        assert actor.user_id == user_id and actor.role == "reviewer"
    assert mailbox.messages == []
    with pytest.raises(AuthenticationFailed):
        service.accept_invitation(onboarding, browser, "invitation-secret")


@pytest.mark.parametrize(
    "overrides",
    [
        {"active": True},
        {"role": "admin"},
        {"password_hash": "existing-hash"},
        {"suspended_at": datetime.now(UTC)},
        {"pending_verification": False},
    ],
)
def test_provider_invitation_rejects_claimed_or_privileged_accounts(
    provider_context, session_factory, overrides
):
    service, _, _, _ = provider_context
    user_id = invited_account(session_factory, **overrides)
    state, browser, _ = start(service)
    result = service.callback("github", state, browser, "code")
    with pytest.raises(AuthenticationFailed):
        service.accept_invitation(result["onboarding"], browser, "invitation-secret")
    with session_factory() as session:
        assert session.get(User, user_id).active == overrides.get("active", False)
        assert session.scalar(select(ExternalIdentity)) is None


def test_provider_invitation_collision_rolls_back_claim(
    provider_context, session_factory
):
    from pkdb.db.models.users import Token
    from pkdb.services.providers import PROVIDERS

    service, _, _, _ = provider_context
    user_id = invited_account(session_factory)
    state, browser, _ = start(service)
    result = service.callback("github", state, browser, "code")
    with session_factory.begin() as session:
        other = User(
            username="other", email="other@example.org", role="user", active=True
        )
        session.add(other)
        session.flush()
        session.add(
            ExternalIdentity(
                user_id=other.id,
                provider="github",
                issuer=PROVIDERS["github"]["issuer"],
                subject="12345",
                label="example-person",
            )
        )
    with pytest.raises(ValueError, match="already linked"):
        service.accept_invitation(result["onboarding"], browser, "invitation-secret")
    with session_factory() as session:
        assert not session.get(User, user_id).active
        assert session.scalar(select(Token)).revoked_at is None
