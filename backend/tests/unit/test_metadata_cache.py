"""Cache lifetimes survive checkouts and apply separately to daily registries."""

import json
import os

import pytest

from info_nodes.metadata_cache import MetadataCache, use_metadata_cache


@pytest.mark.parametrize(
    ("name", "hours"),
    [
        ("ols/term.json", 60 * 24),
        ("chebi/term.json", 60 * 24),
        ("unichem/key.json", 60 * 24),
        ("identifiers_registry.json", 24),
        ("unichem_sources.json", 24),
    ],
)
def test_expiration_uses_persisted_fetch_time(tmp_path, name, hours):
    now = 1_800_000_000.0
    cache = MetadataCache(tmp_path, clock=lambda: now)
    path = tmp_path / name
    cache.write({"value": "fresh"}, path)
    cache.save()
    os.utime(path, (now + hours * 3600, now + hours * 3600))
    reader = MetadataCache(tmp_path, clock=lambda: now + hours * 3600 - 1)
    assert reader.read(path) == {"value": "fresh"}
    reader = MetadataCache(tmp_path, clock=lambda: now + hours * 3600)
    with pytest.raises(OSError, match="expired"):
        reader.read(path)


def test_offline_can_read_expired_cache_without_changing_it(tmp_path):
    cache = MetadataCache(tmp_path, clock=lambda: 1.0)
    path = tmp_path / "identifiers_registry.json"
    cache.write({"prefix": {}}, path)
    cache.save()
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    offline = MetadataCache(tmp_path, offline=True, clock=lambda: 1_800_000_000.0)
    assert offline.read(path) == {"prefix": {}}
    offline.save()
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_untracked_cache_is_not_assumed_fresh(tmp_path):
    path = tmp_path / "identifiers_registry.json"
    path.write_text(json.dumps({"prefix": {}}))
    with pytest.raises(OSError):
        MetadataCache(tmp_path).read(path)
    assert MetadataCache(tmp_path, offline=True).read(path) == {"prefix": {}}


def test_expired_cache_is_not_a_network_failure_fallback(tmp_path):
    cache = MetadataCache(tmp_path, clock=lambda: 1.0)
    path = tmp_path / "unichem_sources.json"
    cache.write({"old": {}}, path)
    cache.save()
    reader = MetadataCache(tmp_path, clock=lambda: 1_800_000_000.0)
    assert reader.fallback(path, reason="unavailable") is None


def test_fma_uses_current_iri_and_reuses_cache_offline(tmp_path, monkeypatch):
    import urllib.parse

    from pymetadata.core.annotation import get_ols_query

    from info_nodes import metadata_cache

    requests = []

    def fetch(url):
        requests.append(urllib.parse.unquote(urllib.parse.unquote(url)))
        return {"label": "Blood", "description": ["A portion of blood."]}

    monkeypatch.setattr(metadata_cache, "get_json", fetch)
    with use_metadata_cache(tmp_path, offline=False):
        assert get_ols_query().query_ols("fma", "FMA:10951")["label"] == "Blood"
    assert requests == [
        "https://www.ebi.ac.uk/ols4/api/ontologies/fma/terms/"
        "http://purl.org/sig/ont/fma/fma10951"
    ]
    with use_metadata_cache(tmp_path, offline=True):
        assert get_ols_query().query_ols("fma", "FMA:10951")["label"] == "Blood"
    assert len(requests) == 1


def test_failed_expired_refresh_replays_identically_offline(tmp_path, monkeypatch):
    from pymetadata.core.annotation import get_ols_query
    from pymetadata.webservices.webservice import WebserviceError

    from info_nodes import metadata_cache

    monkeypatch.setattr(metadata_cache, "get_json", lambda url: {"label": "old"})
    with use_metadata_cache(tmp_path, offline=False):
        get_ols_query().query_ols("fma", "FMA:10951")
    manifest = tmp_path / "manifest.json"
    data = json.loads(manifest.read_text())
    for entry in data["entries"].values():
        entry["fetched_at"] = 1.0
    manifest.write_text(json.dumps(data))

    def unavailable(url):
        raise WebserviceError("Service unavailable")

    monkeypatch.setattr(metadata_cache, "get_json", unavailable)
    with use_metadata_cache(tmp_path, offline=False):
        online = get_ols_query().query_ols("fma", "FMA:10951")
    with use_metadata_cache(tmp_path, offline=True):
        offline = get_ols_query().query_ols("fma", "FMA:10951")
    assert online["errors"] == ["Service unavailable"]
    assert offline == online


def test_context_does_not_reuse_another_cache_annotations(tmp_path, monkeypatch):
    from pymetadata.core.annotation import RDFAnnotationData
    from pymetadata.core.miriam import BQB

    from info_nodes import metadata_cache, node

    original_path = node.CACHE_PATH
    original_resolver = node.resolve_annotation
    for label in ("first", "second"):
        monkeypatch.setattr(metadata_cache, "get_json", lambda url: {"label": label})
        root = tmp_path / label
        with use_metadata_cache(root, offline=False):
            resolved = node.resolve_annotation(
                BQB.IS, "https://bioregistry.io/CHMO:0000001"
            )
            assert isinstance(resolved, RDFAnnotationData)
            assert resolved.label == label
            assert node.CACHE_PATH == root
    assert node.CACHE_PATH == original_path
    assert node.resolve_annotation is original_resolver
