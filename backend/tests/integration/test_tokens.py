from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from pkdb_server.db.models.users import Token, User
from pkdb_server.services.authentication import (
    AuthenticationFailed,
    authenticate_token,
    issue_token,
)


@pytest.fixture
def active_user(db_session):
    user = User(username="active", active=True, role="curator")
    db_session.add(user)
    db_session.flush()
    return user


def test_only_digest_is_stored(db_session, active_user):
    raw = issue_token(active_user, db_session)
    row = db_session.scalar(select(Token))
    assert row.digest != raw
    assert len(row.digest) == 64
    assert authenticate_token(raw, db_session).user_id == active_user.id


@pytest.mark.parametrize("state", ["expired", "revoked", "disabled", "wrong_purpose"])
def test_unusable_token_is_rejected(db_session, active_user, state):
    raw = issue_token(active_user, db_session)
    token = db_session.scalar(select(Token))
    if state == "expired":
        token.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    elif state == "revoked":
        token.revoked_at = datetime.now(UTC)
    elif state == "disabled":
        active_user.active = False
    else:
        token.purpose = "reset_password"
    db_session.flush()
    with pytest.raises(AuthenticationFailed):
        authenticate_token(raw, db_session)


def test_unknown_token_is_rejected(db_session):
    with pytest.raises(AuthenticationFailed):
        authenticate_token("invalid", db_session)


@pytest.mark.parametrize("cutoff", [None, datetime(2020, 1, 1, tzinfo=UTC)])
def test_legacy_tokens_fail_closed_after_transition(db_session, active_user, cutoff):
    from pkdb_server.db.models.security import SecurityConfiguration
    from pkdb_server.services.authentication import revalidate_principal

    raw = issue_token(active_user, db_session)
    actor = authenticate_token(raw, db_session)
    config = db_session.get(SecurityConfiguration, 1)
    config.legacy_token_cutoff = cutoff
    db_session.flush()
    with pytest.raises(AuthenticationFailed):
        authenticate_token(raw, db_session)
    with pytest.raises(AuthenticationFailed):
        revalidate_principal(actor, db_session)
