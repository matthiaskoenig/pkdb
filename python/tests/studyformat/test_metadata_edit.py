import json

import pytest

import pkdb.studyformat.metadata as module
from pkdb.studyformat.metadata import (
    MetadataError,
    merge_patch,
    patch_metadata,
    read_metadata,
    write_metadata,
)
from pkdb.studyformat.revision import RevisionConflict


def test_merge_patch_follows_rfc_7386():
    target = {"a": 1, "b": {"c": 2, "d": 3}}
    patch = {"b": {"c": None, "e": 4}, "f": [1]}
    assert merge_patch(target, patch) == {"a": 1, "b": {"d": 3, "e": 4}, "f": [1]}
    assert merge_patch({"a": [1, 2]}, {"a": [3]}) == {"a": [3]}
    assert merge_patch({"a": 1}, "x") == "x"


def test_patch_writes_canonical_json(valid_study):
    document = read_metadata(valid_study)
    patch = {"licence": "closed", "descriptions": ["Quote."]}
    written = patch_metadata(valid_study, patch, document.revision)
    text = (valid_study / "study.json").read_text()
    assert json.loads(text)["licence"] == "closed"
    assert written.revision == read_metadata(valid_study).revision
    assert text.endswith("\n") and text.index('"licence"') < text.index(
        '"descriptions"'
    )


def test_invalid_patch_writes_nothing(valid_study):
    before = (valid_study / "study.json").read_bytes()
    with pytest.raises(MetadataError) as error:
        patch_metadata(valid_study, {"licence": "maybe"}, None)
    assert error.value.issues[0].code == "invalid_study_json"
    assert (valid_study / "study.json").read_bytes() == before


def test_missing_file_is_a_metadata_error(tmp_path):
    with pytest.raises(MetadataError) as error:
        read_metadata(tmp_path)
    assert error.value.issues[0].code == "missing_file"


def test_stale_revision_is_refused(valid_study):
    document = read_metadata(valid_study)
    patch_metadata(valid_study, {"licence": "closed"}, document.revision)
    with pytest.raises(RevisionConflict):
        write_metadata(valid_study, document.metadata, document.revision)


def test_changed_identifier_refreshes_reference(valid_study, monkeypatch):
    calls = []

    class Resolver:
        pass

    def fake_sync(folder, resolver):
        calls.append((folder, resolver))
        return "replaced reference.json"

    monkeypatch.setattr(module, "sync_reference", fake_sync)
    document = read_metadata(valid_study)
    patch = {"reference": {"pmid": "456"}}
    result = patch_metadata(valid_study, patch, document.revision, resolver=Resolver())
    unchanged = patch_metadata(
        valid_study, {"licence": "closed"}, result.revision, resolver=Resolver()
    )
    assert result.reference == "replaced reference.json" and len(calls) == 1
    assert unchanged.reference is None
