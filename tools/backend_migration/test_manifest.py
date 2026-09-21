"""Ensure corpus accounting cannot hide malformed or duplicate studies."""

import json

from tools.backend_migration.manifest import build_manifest


def test_manifest_hashes_without_changing_source(tmp_path):
    """Test manifest hashes without changing source."""
    folder = tmp_path / "drug" / "Example"
    folder.mkdir(parents=True)
    source = folder / "study.json"
    source.write_text(json.dumps({"sid": "PK1", "name": "Example"}))
    (folder / "reference.json").write_text("{}")
    original = source.read_bytes()
    result = build_manifest(tmp_path)
    assert result["study_count"] == 1
    assert result["studies"][0]["sid"] == "PK1"
    assert result["studies"][0]["path"] == "drug/Example"
    assert len(result["studies"][0]["files"]["study.json"]["sha256"]) == 64
    assert source.read_bytes() == original


def test_duplicate_sid_is_reported_not_overwritten(tmp_path):
    """Test duplicate sid is reported not overwritten."""
    for name in ("one", "two"):
        folder = tmp_path / name
        folder.mkdir()
        (folder / "study.json").write_text(json.dumps({"sid": "PK1", "name": name}))
    result = build_manifest(tmp_path)
    assert result["study_count"] == 2
    assert result["issues"][0]["code"] == "duplicate_sid"


def test_invalid_json_has_an_explicit_disposition(tmp_path):
    """Test invalid json has an explicit disposition."""
    (tmp_path / "study.json").write_text("{")
    result = build_manifest(tmp_path)
    assert result["study_count"] == 1
    assert result["studies"][0]["status"] == "invalid_json"


def test_integer_sid_is_a_supported_legacy_identity(tmp_path):
    """Test integer sid is a supported legacy identity."""
    (tmp_path / "study.json").write_text('{"sid": 123, "name": "Example"}')
    result = build_manifest(tmp_path)
    assert result["studies"][0]["status"] == "inventoried"
    assert result["studies"][0]["sid"] == "123"


def test_duplicate_json_keys_are_invalid(tmp_path):
    """Test duplicate json keys are invalid."""
    (tmp_path / "study.json").write_text('{"sid":"A", "sid":"B"}')
    assert build_manifest(tmp_path)["studies"][0]["status"] == "invalid_json"
