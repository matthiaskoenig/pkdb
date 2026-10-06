import pytest

from pkdb.identity import Author, IdentityError, author_from


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
