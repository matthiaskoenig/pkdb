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


def test_patterned_fields_have_plain_messages(valid_study):
    patch = {
        "creator": "Jane Doe",
        "reference": {"pmid": "0123", "doi": None},
        "provenance": {
            "kind": "automatic_curation",
            "source_key": "pkdb.ai",
            "method": "claude",
            "version": "1",
            "assets": [{"url": "https://example.org/a.pdf", "sha256": "abc"}],
            "run_id": "run-1",
        },
        "release": {"pkdb_id": "PK1", "date": "2026-09-28T10:00:00"},
    }
    with pytest.raises(MetadataError) as error:
        patch_metadata(valid_study, patch, None)
    messages = {issue.field: issue.message for issue in error.value.issues}
    assert messages == {
        "creator": "creator: A user name has no spaces.",
        "reference.pmid": (
            "reference.pmid: A PubMed ID has only digits and does not start with 0."
        ),
        "provenance.automatic_curation.assets.0.sha256": (
            "provenance.automatic_curation.assets.0.sha256: "
            "A SHA-256 has 64 characters 0-9 and a-f."
        ),
        "release.pkdb_id": (
            "release.pkdb_id: A release ID is PKDB and five digits, such as PKDB00198."
        ),
        "release.date": (
            "release.date: A date has the form YYYY-MM-DD, such as 2026-09-28."
        ),
    }


def test_empty_texts_and_user_names_have_plain_messages(valid_study):
    patch = {
        "creator": "",
        "curators": [{"user": "", "rating": 1}],
        "collaborators": [""],
        "descriptions": [""],
        "comments": [{"user": "mkoenig", "text": ""}],
        "notes": {"outputs": {"descriptions": [""], "comments": []}},
    }
    with pytest.raises(MetadataError) as error:
        patch_metadata(valid_study, patch, None)
    messages = {issue.field: issue.message for issue in error.value.issues}
    text = "Enter some text or remove this entry."
    assert messages == {
        "creator": "creator: Enter a user name.",
        "curators.0.user": "curators.0.user: Enter a user name.",
        "collaborators.0": f"collaborators.0: {text}",
        "descriptions.0": f"descriptions.0: {text}",
        "comments.0.text": f"comments.0.text: {text}",
        "notes.outputs.descriptions.0": f"notes.outputs.descriptions.0: {text}",
    }


def test_other_messages_stay_those_of_pydantic(valid_study):
    patch = {
        "licence": "maybe",
        "curators": [{"user": "mkoenig", "rating": 7}],
        "provenance": {"kind": "manual_curation", "source_key": ""},
    }
    with pytest.raises(MetadataError) as error:
        patch_metadata(valid_study, patch, None)
    messages = {issue.field: issue.message for issue in error.value.issues}
    assert messages == {
        "licence": "licence: Input should be 'open' or 'closed'",
        "curators.0.rating": "curators.0.rating: Input should be less than or equal to 5",
        "provenance.manual_curation.source_key": (
            "provenance.manual_curation.source_key: "
            "String should have at least 1 character"
        ),
    }


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


def test_failed_reference_refresh_keeps_study_json_written(valid_study, monkeypatch):
    def failing_sync(folder, resolver):
        raise module.ReferenceError("PubMed is unreachable")

    monkeypatch.setattr(module, "sync_reference", failing_sync)
    document = read_metadata(valid_study)
    result = patch_metadata(
        valid_study,
        {"reference": {"pmid": "456"}},
        document.revision,
        resolver=object(),
    )
    assert result.reference is None and "unreachable" in (result.reference_error or "")
    current = read_metadata(valid_study)
    assert current.metadata.reference is not None
    assert current.metadata.reference.pmid == "456"
    assert result.revision == current.revision


def test_refresh_reference_forces_the_refresh(valid_study, monkeypatch):
    calls = []
    monkeypatch.setattr(
        module, "sync_reference", lambda folder, resolver: calls.append(folder) or "ok"
    )
    document = read_metadata(valid_study)
    result = write_metadata(
        valid_study,
        document.metadata,
        document.revision,
        resolver=object(),
        refresh_reference=True,
    )
    assert result.reference == "ok" and calls == [valid_study]
    patched = patch_metadata(
        valid_study,
        {"reference": {"pmid": "123"}},
        None,
        resolver=object(),
        refresh_reference=True,
    )
    assert patched.reference == "ok" and len(calls) == 2
