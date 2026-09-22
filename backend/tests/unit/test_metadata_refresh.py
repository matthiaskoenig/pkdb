"""Forced refresh is staged and cannot destroy the last valid vocabulary."""

import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def generator(tmp_path, monkeypatch):
    script = Path(__file__).resolve().parents[3] / "scripts/update_vocabulary.py"
    spec = importlib.util.spec_from_file_location("vocabulary_generator", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    definitions = tmp_path / "info_nodes"
    cache = definitions / "cache"
    cache.mkdir(parents=True)
    (cache / "old.json").write_text('{"old": true}\n')
    output = tmp_path / "bootstrap"
    output.mkdir()
    for name in ("provenance.json", "vocabulary.json"):
        (output / name).write_text('{"previous": true}\n')
    monkeypatch.setattr(module, "DEFINITIONS", definitions)
    monkeypatch.setattr(module, "CACHE", cache)
    monkeypatch.setattr(
        "sys.argv", [str(script), "--refresh-cache", "--output", str(output)]
    )
    return module, cache, output


def test_forced_refresh_starts_empty_and_replaces_old_cache(generator, monkeypatch):
    module, cache, output = generator

    def compile_fresh(staged_cache, *, offline):
        assert not offline
        assert list(staged_cache.iterdir()) == []
        (staged_cache / "new.json").write_text('{"fresh": true}\n')
        return {
            "provenance.json": '{"metadata_issues": []}\n',
            "vocabulary.json": '{"nodes": []}\n',
        }

    monkeypatch.setattr(module, "compile_vocabulary", compile_fresh)
    assert module.main() == 0
    assert not (cache / "old.json").exists()
    assert json.loads((cache / "new.json").read_text()) == {"fresh": True}
    assert json.loads((output / "vocabulary.json").read_text()) == {"nodes": []}


def test_failed_refresh_preserves_cache_and_generated_output(generator, monkeypatch):
    module, cache, output = generator
    before = {p: p.read_bytes() for root in (cache, output) for p in root.iterdir()}

    def fail(staged_cache, *, offline):
        assert list(staged_cache.iterdir()) == []
        (staged_cache / "partial.json").write_text("{}")
        raise ValueError("Required metadata unavailable")

    monkeypatch.setattr(module, "compile_vocabulary", fail)
    assert module.main() == 1
    assert {
        p: p.read_bytes() for root in (cache, output) for p in root.iterdir()
    } == before
