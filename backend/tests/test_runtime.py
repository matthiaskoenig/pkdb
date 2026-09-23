"""The declared interpreter support must include usable scientific dependencies."""

import importlib
import importlib.util
import sys

import pytest


def test_supported_runtime_and_scientific_imports():
    assert sys.version_info[:2] == (3, 14)
    for name in (
        "pkdb",
        "pydantic",
        "numpy",
        "scipy",
        "pandas",
        "pint",
        "pkpdutils.nca",
    ):
        importlib.import_module(name)
    assert importlib.util.find_spec("pkdb_analysis") is None


def test_settings_reject_invalid_resource_limits(tmp_path):
    from pydantic import ValidationError

    from pkdb_server.config import Settings

    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+psycopg://localhost/test",
            file_root=tmp_path,
            upload_concurrency=0,
        )


def test_settings_require_explicit_storage_locations(monkeypatch):
    from pydantic import ValidationError

    from pkdb_server.config import Settings

    monkeypatch.delenv("PKDB_DATABASE_URL", raising=False)
    monkeypatch.delenv("PKDB_FILE_ROOT", raising=False)
    with pytest.raises(ValidationError):
        Settings()
