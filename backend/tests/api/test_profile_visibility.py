from sqlalchemy import select

from pkdb.db.models.providers import ExternalIdentity
from pkdb.db.models.users import User
from pkdb.services.profiles import public_profile


def test_owner_can_hide_provider_references_without_disconnecting_login(
    client, admin_headers, session_factory
):
    references = {"github": "example-person", "orcid": "0000-0002-1825-0097"}
    with session_factory.begin() as session:
        user = session.scalar(select(User).where(User.username == "mkoenig"))
        user_id = user.id
        for provider, reference in references.items():
            setattr(user, provider, reference)
            setattr(user, f"{provider}_provenance", "authenticated")
            session.add(
                ExternalIdentity(
                    user_id=user_id,
                    provider=provider,
                    issuer="https://github.com"
                    if provider == "github"
                    else "https://orcid.org",
                    subject="12345" if provider == "github" else reference,
                    label=reference,
                )
            )
    before = client.get("/api/v1/me/identities", headers=admin_headers).json()
    response = client.patch(
        "/api/v1/me",
        headers=admin_headers,
        json={"github_visible": False, "orcid_visible": False},
    )
    assert response.status_code == 200, response.text
    owner = client.get("/api/v1/me", headers=admin_headers).json()
    for provider, reference in references.items():
        assert owner[provider] == reference
        assert owner[f"{provider}_provenance"] == "authenticated"
        assert owner[f"{provider}_visible"] is False
    with session_factory() as session:
        public = public_profile(session.get(User, user_id))
        for provider in references:
            assert public[provider] is None
            assert public[f"{provider}_provenance"] is None
            assert f"{provider}_visible" not in public
    assert client.get("/api/v1/me/identities", headers=admin_headers).json() == before
    assert (
        client.patch(
            "/api/v1/me", headers=admin_headers, json={"github": "someone-else"}
        ).status_code
        == 403
    )
    assert (
        client.patch(
            "/api/v1/me",
            headers=admin_headers,
            json={"github_visible": True, "orcid_visible": True},
        ).status_code
        == 200
    )
    with session_factory() as session:
        public = public_profile(session.get(User, user_id))
        assert all(
            public[provider] == reference for provider, reference in references.items()
        )
