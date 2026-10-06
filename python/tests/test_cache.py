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


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions")
@pytest.mark.parametrize(
    ("umask", "mode"), [(0o022, 0o644), (0o027, 0o640)], ids=["022", "027"]
)
def test_atomic_text_creates_files_by_the_umask(tmp_path, umask, mode):
    from pkdb.cache import atomic_text

    previous = os.umask(umask)
    try:
        atomic_text(tmp_path / "table.tsv", "new")
    finally:
        os.umask(previous)
    assert (tmp_path / "table.tsv").stat().st_mode & 0o777 == mode
    assert [path.name for path in tmp_path.iterdir()] == ["table.tsv"]


def test_atomic_text_removes_its_temporary_file_on_failure(tmp_path, monkeypatch):
    from pkdb.cache import atomic_text

    def fail(fd):
        raise OSError("disk full")

    monkeypatch.setattr("pkdb.cache.os.fsync", fail)
    with pytest.raises(OSError, match="disk full"):
        atomic_text(tmp_path / "table.tsv", "new")
    assert list(tmp_path.iterdir()) == []


def test_atomic_bytes_writes_bytes_and_leaves_no_temporary_file(tmp_path):
    from pkdb.cache import atomic_bytes

    target = tmp_path / "a" / "book.xlsx"
    atomic_bytes(target, b"PK\x03\x04\r\n\x00")
    assert target.read_bytes() == b"PK\x03\x04\r\n\x00"
    assert [path.name for path in target.parent.iterdir()] == ["book.xlsx"]


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions")
def test_atomic_bytes_keeps_the_permissions_of_the_replaced_file(tmp_path):
    from pkdb.cache import atomic_bytes

    target = tmp_path / "book.xlsx"
    target.write_bytes(b"old")
    target.chmod(0o640)
    atomic_bytes(target, b"new")
    assert target.read_bytes() == b"new"
    assert target.stat().st_mode & 0o777 == 0o640


def test_atomic_bytes_keeps_the_old_content_when_the_replace_fails(
    tmp_path, monkeypatch
):
    from pkdb.cache import atomic_bytes

    target = tmp_path / "book.xlsx"
    target.write_bytes(b"old")

    def fail(self, destination):
        raise OSError("locked")

    monkeypatch.setattr("pkdb.cache.Path.replace", fail)
    with pytest.raises(OSError, match="locked"):
        atomic_bytes(target, b"new")
    assert target.read_bytes() == b"old"
    assert [path.name for path in tmp_path.iterdir()] == ["book.xlsx"]


def test_atomic_text_encodes_utf8_with_lf_newlines(tmp_path):
    from pkdb.cache import atomic_text

    target = tmp_path / "table.tsv"
    atomic_text(target, "caf\u00e9\r\nx\n")
    assert target.read_bytes() == "caf\u00e9\r\nx\n".encode()
