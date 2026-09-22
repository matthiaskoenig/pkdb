"""Run preserved client tests against isolated caches without network access."""

import shutil
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

import pkdb_data
import pymetadata
import pytest
import requests

_PATCHES = pytest.StashKey[pytest.MonkeyPatch]()
_CACHE = pytest.StashKey[TemporaryDirectory[str]]()


def pytest_configure(config: pytest.Config) -> None:
    """Prepare caches before vocabulary modules are imported during collection."""
    temporary = TemporaryDirectory(prefix="pkdb-client-tests-")
    config.stash[_CACHE] = temporary
    cache = Path(temporary.name)
    shutil.copytree(pkdb_data.CACHE_PATH, cache / "client")
    (cache / "metadata").mkdir()
    shutil.copyfile(
        Path(__file__).parent / "fixtures/identifiers_registry.json",
        cache / "metadata/identifiers_registry.json",
    )
    patches = pytest.MonkeyPatch()
    config.stash[_PATCHES] = patches
    patches.setattr(pkdb_data, "CACHE_PATH", cache / "client")
    patches.setattr(pymetadata, "CACHE_PATH", cache / "metadata")

    def no_network(*args, **kwargs):
        raise AssertionError("Client tests must use fixtures instead of live services")

    def offline_request(*args, **kwargs):
        raise requests.ConnectionError(
            "Offline client tests: external service unavailable"
        )

    patches.setattr(requests.sessions.Session, "request", offline_request)
    patches.setattr(urllib.request, "urlopen", no_network)


def pytest_unconfigure(config: pytest.Config) -> None:
    """Release the temporary caches and restore patched modules."""
    if _PATCHES in config.stash:
        config.stash[_PATCHES].undo()
    if _CACHE in config.stash:
        config.stash[_CACHE].cleanup()
