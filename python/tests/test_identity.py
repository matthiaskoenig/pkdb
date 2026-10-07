import pytest

from pkdb.errors import ClientError
from pkdb.identity import (
    Author,
    IdentityError,
    UserMismatch,
    author_from,
    check_account,
    resolve_author,
)


def test_author_from_arguments_and_environment():
    assert author_from("mkoenig", None, environ={}) == Author("mkoenig")
    assert author_from(
        None, None, environ={"PKDB_USER": "a", "PKDB_AGENT": "claude-opus-5-5"}
    ) == Author("a", "claude-opus-5-5")
    assert author_from("b", "", environ={"PKDB_AGENT": "x"}) == Author("b", "x")


@pytest.mark.parametrize("user", [None, "", "two words", "x" * 256])
def test_author_needs_a_valid_user(user):
    with pytest.raises(IdentityError):
        author_from(user, None, environ={})


def account_check(result):
    """A fake server check that records its calls and returns or raises `result`."""
    calls = []

    def check(endpoint, api_key, user):
        calls.append((endpoint, api_key, user))
        if isinstance(result, Exception):
            raise result
        return result

    return check, calls


def test_the_author_is_the_account_of_a_checked_key():
    check, calls = account_check("curator")
    author = resolve_author(
        None,
        "claude",
        endpoint="https://pk-db.test",
        api_key="key",
        environ={"PKDB_USER": "curator"},
        check=check,
    )
    assert author == Author("curator", "claude")
    assert calls == [("https://pk-db.test", "key", "curator")]
    # Without a configured user, the account of the key writes.
    check, _ = account_check("account")
    assert resolve_author(
        None,
        None,
        endpoint="https://pk-db.test",
        api_key="key",
        environ={},
        check=check,
    ) == Author("account")


def test_the_configured_user_writes_without_a_check():
    check, calls = account_check("account")
    for endpoint, api_key, offline in (
        ("https://pk-db.test", None, False),
        (None, "key", False),
        ("https://pk-db.test", "key", True),
    ):
        author = resolve_author(
            "curator",
            None,
            endpoint=endpoint,
            api_key=api_key,
            offline=offline,
            environ={},
            check=check,
        )
        assert author == Author("curator")
    assert calls == []
    # An unreachable server cannot confirm the key, so the configured user writes.
    check, calls = account_check(None)
    assert resolve_author(
        "curator", None, endpoint="https://pk-db.test", api_key="key", check=check
    ) == Author("curator")
    assert len(calls) == 1
    with pytest.raises(IdentityError, match="required"):
        resolve_author(
            None,
            None,
            endpoint="https://pk-db.test",
            api_key="key",
            environ={},
            check=check,
        )


def test_a_key_of_another_account_is_refused():
    check, _ = account_check(UserMismatch("The API key belongs to PK-DB user 'other'"))
    with pytest.raises(UserMismatch, match="belongs to PK-DB user 'other'"):
        resolve_author(
            "curator", None, endpoint="https://pk-db.test", api_key="key", check=check
        )
    assert UserMismatch.code == "user_mismatch"
    assert issubclass(UserMismatch, IdentityError)


def test_check_account_asks_the_server_with_a_short_timeout(account_server):
    assert check_account("https://pk-db.test", "key", "curator") == "curator"
    [(endpoint, api_key, user, transport)] = account_server.calls
    assert (endpoint, api_key, user) == ("https://pk-db.test", "key", "curator")
    assert transport.timeout.read <= 10
    account_server.failure = ClientError("PK-DB request failed", code="unreachable")
    assert check_account("https://pk-db.test", "key", "curator") is None
    account_server.failure = ClientError("rejected", status_code=401)
    assert check_account("https://pk-db.test", "key", "curator") is None
    account_server.failure = ClientError("belongs to 'other'", code="user_mismatch")
    with pytest.raises(UserMismatch, match="belongs to 'other'"):
        check_account("https://pk-db.test", "key", "curator")
