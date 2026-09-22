"""Test access to the environment variables."""

import pytest
from pkdb_data.management.envs import (
    EnvironmentNotInitializedError,
    get_environment,
)


def test_get_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test reading the connection information."""
    monkeypatch.setenv("API_BASE", "https://alpha.pk-db.com/")
    monkeypatch.setenv("USER", "curator")
    monkeypatch.setenv("PASSWORD", "secret")

    env = get_environment()
    assert env.api_base == "https://alpha.pk-db.com"
    assert env.api_url == "https://alpha.pk-db.com/api/v1"
    assert env.user == "curator"
    assert env.password == "secret"


def test_get_environment_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that a missing variable is reported instead of exiting on import."""
    monkeypatch.delenv("API_BASE", raising=False)
    with pytest.raises(EnvironmentNotInitializedError, match="API_BASE"):
        get_environment()
