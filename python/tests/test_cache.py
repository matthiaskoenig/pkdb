"""Caches preserve explicit endpoint pins and verify content identity."""

import json
import os

import pytest

from pkdb.cache import VocabularyCache, bundled_vocabulary
from pkdb.domain.vocabulary import vocabulary_hash


def test_endpoint_cache_pins_independent_snapshots(tmp_path, vocabulary):
    cache = VocabularyCache(tmp_path)
    first = cache.store("https://first.test/api/v2", vocabulary)
    other = vocabulary.model_copy(update={"version": "test-v2"})
    cache.store("https://second.test", other)
    assert cache.load("https://first.test/") == vocabulary
    assert cache.load("https://second.test") == other
    assert first.name == vocabulary_hash(vocabulary) + ".json"


def test_cache_rejects_tampered_snapshot(tmp_path, vocabulary):
    cache = VocabularyCache(tmp_path)
    path = cache.store("https://example.test", vocabulary)
    value = json.loads(path.read_text())
    value["vocabulary"]["version"] = "tampered"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="hash"):
        cache.load("https://example.test")


def test_bundled_snapshot_is_complete_and_content_verified():
    vocabulary = bundled_vocabulary()
    assert {"concentration", "dosing", "species", "sex", "healthy"} <= set(
        vocabulary.measurement_map()
    )
    assert vocabulary.substances
    assert vocabulary.routes


def test_invalid_cache_index_is_a_validation_error(tmp_path, vocabulary):
    cache = VocabularyCache(tmp_path)
    cache.store("https://example.test", vocabulary)
    pointer = next((tmp_path / "endpoints").glob("*.json"))
    pointer.write_text("[]")
    with pytest.raises(ValueError, match="cache"):
        cache.load("https://example.test")


def test_missing_pinned_snapshot_does_not_silently_fall_back(tmp_path, vocabulary):
    cache = VocabularyCache(tmp_path)
    path = cache.store("https://example.test", vocabulary)
    path.unlink()
    with pytest.raises(ValueError, match="snapshot"):
        cache.load("https://example.test")


def test_atomic_text_writes_lf(tmp_path):
    from pkdb.cache import atomic_text

    target = tmp_path / "a" / "table.tsv"
    atomic_text(target, "x\ty\n1\t2\n")
    assert target.read_bytes() == b"x\ty\n1\t2\n"


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions")
def test_atomic_text_keeps_the_permissions_of_the_replaced_file(tmp_path):
    from pkdb.cache import atomic_text

    target = tmp_path / "table.tsv"
    target.write_text("old")
    target.chmod(0o640)
    atomic_text(target, "new")
    assert target.read_text() == "new"
    assert target.stat().st_mode & 0o777 == 0o640
