"""The curator roster lists GitHub logins for the issue sync, also hidden ones."""

from datetime import UTC, datetime, timedelta

from pkdb_server.db.models.credentials import ApiKey
from pkdb_server.db.models.users import User
from pkdb_server.services.credentials import digest


def key_for(session, user):
    secret = f"pkdb_live_curators_{user.id}"
    session.add(
        ApiKey(
            user_id=user.id,
            name="roster test",
            prefix=secret[:17],
            digest=digest(secret),
            scopes=["read"],
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    return {"Authorization": f"Bearer {secret}"}


def test_the_roster_needs_credentials(client):
    assert client.get("/api/v2/curators").status_code == 401


def test_the_roster_lists_curators_with_hidden_github_logins(client, session_factory):
    with session_factory.begin() as session:
        session.add_all(
            [
                User(
                    username="hidden",
                    role="curator",
                    display_name="Hidden Person",
                    github="hidden-gh",
                    github_visible=False,
                ),
                User(
                    username="rev", role="reviewer", first_name="Re", last_name="Viewer"
                ),
                User(username="boss", role="admin", github="boss-gh"),
                User(username="plain", role="user", github="plain-gh"),
            ]
        )
        reader = User(username="reader", role="user", active=True)
        session.add(reader)
        session.flush()
        headers = key_for(session, reader)
    response = client.get("/api/v2/curators", headers=headers)
    assert response.status_code == 200
    rows = {row["username"]: row for row in response.json()["curators"]}
    assert rows["hidden"] == {
        "username": "hidden",
        "name": "Hidden Person",
        "github": "hidden-gh",
    }
    assert rows["rev"] == {"username": "rev", "name": "Re Viewer", "github": None}
    assert rows["boss"]["name"] == "boss"
    assert "plain" not in rows and "reader" not in rows
    names = [row["username"] for row in response.json()["curators"]]
    assert names == sorted(names)
