from sqlalchemy import select

from pkdb_server.db.models.users import User
from pkdb_server.services.profiles import public_profile


def test_owner_can_edit_and_hide_optional_profile_references(
    client, admin_headers, session_factory
):
    references = {"github": "example-person", "orcid": "0000-0002-1825-0097"}
    with session_factory.begin() as session:
        user = session.scalar(select(User).where(User.username == "mkoenig"))
        user_id = user.id
        for provider, reference in references.items():
            setattr(user, provider, reference)
            setattr(user, f"{provider}_provenance", "self_asserted")
    response = client.patch(
        "/api/v1/me",
        headers=admin_headers,
        json={"github_visible": False, "orcid_visible": False},
    )
    assert response.status_code == 200, response.text
    owner = client.get("/api/v1/me", headers=admin_headers).json()
    for provider, reference in references.items():
        assert owner[provider] == reference
        assert owner[f"{provider}_provenance"] == "self_asserted"
        assert owner[f"{provider}_visible"] is False
    with session_factory() as session:
        public = public_profile(session.get(User, user_id))
        for provider in references:
            assert public[provider] is None
            assert public[f"{provider}_provenance"] is None
            assert f"{provider}_visible" not in public
    assert (
        client.patch(
            "/api/v1/me", headers=admin_headers, json={"github": "example-person"}
        ).status_code
        == 200
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
