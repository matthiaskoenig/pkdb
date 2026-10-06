import json

import pytest
from pydantic import ValidationError

from pkdb.studyformat.jsonio import MAX_DEPTH, JsonFileError, dump_json, load_json
from pkdb.studyformat.models import (
    Review,
    StudyMetadata,
    canonical_review_json,
    canonical_study_json,
)

STUDY = {
    "format": 2,
    "reference": {"pmid": "27129716"},
    "creator": "changlinh",
    "curators": [{"user": "changlinh", "rating": 1}],
    "licence": "closed",
    "access": "private",
}
ITEM = {
    "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2AB",
    "kind": "uncertainty",
    "text": "Legend does not say SD or SE.",
    "author": "mkoenig",
    "created": "2026-10-05T10:12:00Z",
}


def test_load_json_rejects_duplicates_and_nan():
    with pytest.raises(JsonFileError) as duplicate:
        load_json(b'{"a": 1, "a": 2}')
    assert duplicate.value.code == "duplicate_key"
    with pytest.raises(JsonFileError) as nan:
        load_json(b'{"a": NaN}')
    assert nan.value.code == "invalid_json"
    with pytest.raises(JsonFileError) as syntax:
        load_json(b'{"reference":,}')
    assert syntax.value.code == "invalid_json"
    assert "line 1" in str(syntax.value)


@pytest.mark.parametrize(
    "data",
    [
        b"[" * 100_000 + b"]" * 100_000,
        b'{"a": ' + b"[" * 100_000 + b"]" * 100_000 + b"}",
        b'{"issue": ' + b"9" * 5000 + b"}",
        b'{"rating": 1e999}',
        b'{"rating": -1e999}',
        b"1e400",
    ],
    ids=["deep", "deep_value", "long_integer", "inf", "minus_inf", "top_level_inf"],
)
def test_load_json_rejects_hostile_input(data):
    with pytest.raises(JsonFileError) as error:
        load_json(data)
    assert error.value.code == "invalid_json"


def test_load_json_accepts_exactly_the_maximum_depth():
    data = b"[" * MAX_DEPTH + b"]" * MAX_DEPTH
    value = load_json(data)
    for _ in range(MAX_DEPTH - 1):
        assert isinstance(value, list) and len(value) == 1
        value = value[0]
    assert value == []


def test_load_json_rejects_one_level_beyond_the_maximum_depth():
    data = b"[" * (MAX_DEPTH + 1) + b"]" * (MAX_DEPTH + 1)
    with pytest.raises(JsonFileError) as error:
        load_json(data)
    assert error.value.code == "invalid_json"
    assert f"nested deeper than {MAX_DEPTH} levels" in str(error.value)


def test_load_json_does_not_count_brackets_inside_strings():
    brackets = "[" * 1000
    escaped = '\\"' + "{" * 1000
    text = '{"a": "' + brackets + ']]", "b": "' + escaped + '"}'
    assert load_json(text.encode()) == {"a": brackets + "]]", "b": '"' + "{" * 1000}


def test_load_json_counts_depth_after_a_string_ending_in_an_escaped_backslash():
    deep = "[" * (MAX_DEPTH + 1) + "]" * (MAX_DEPTH + 1)
    with pytest.raises(JsonFileError) as error:
        load_json(('{"a": "x\\\\", "b": ' + deep + "}").encode())
    assert error.value.code == "invalid_json"
    assert "nested deeper" in str(error.value)


def test_load_json_keeps_ordinary_numbers():
    assert load_json(b'{"a": 1e300, "b": 2.5, "c": -3}') == {
        "a": 1e300,
        "b": 2.5,
        "c": -3,
    }


def test_dump_json_keeps_unicode_and_ends_with_newline():
    assert dump_json({"name": "Dahlström"}) == '{\n  "name": "Dahlström"\n}\n'


def test_canonical_study_json_order_and_defaults():
    study = StudyMetadata.model_validate(
        {
            **STUDY,
            "release": {"pkdb_id": "PKDB01237", "date": "2026-09-28"},
            "issue": 2158,
            "notes": {
                "outputs": {"descriptions": []},
                "subjects": {"descriptions": ["Q"]},
            },
            "provenance": {"kind": "manual_curation"},
        }
    )
    text = canonical_study_json(study)
    data = json.loads(text)
    assert list(data) == [
        "format",
        "reference",
        "creator",
        "curators",
        "licence",
        "access",
        "issue",
        "release",
        "notes",
    ]
    assert data["notes"] == {"subjects": {"descriptions": ["Q"]}}
    assert canonical_study_json(StudyMetadata.model_validate(data)) == text


@pytest.mark.parametrize(
    "change",
    [
        {"format": 1},
        {"reference": {}},
        {"reference": {"pmid": "PMID123"}},
        {"reference": {"doi": "doi:10.1/x"}},
        {"release": {"pkdb_id": "PKDB1237", "date": "2026-09-28"}},
        {"licence": "public"},
        {"groupset": {}},
        {"sid": "PKDB00198"},
        {"creator": ""},
        {"curators": [{"user": "a", "rating": 6}]},
        {"notes": {"groups": {}}},
    ],
)
def test_study_metadata_rejects(change):
    with pytest.raises(ValidationError):
        StudyMetadata.model_validate({**STUDY, **change})


def test_manual_reference_is_absent():
    data = dict(STUDY)
    del data["reference"]
    assert StudyMetadata.model_validate(data).reference is None


def test_canonical_review_json_sorts_items():
    later = {**ITEM, "id": "01JB0000000000000000000000"}
    review = Review.model_validate(
        {
            "status": "in_review",
            "items": [later, {**ITEM, "target": {"file": "outputs_Tab2.tsv"}}],
        }
    )
    data = json.loads(canonical_review_json(review))
    assert [item["id"] for item in data["items"]] == [ITEM["id"], later["id"]]
    assert data["items"][0]["target"] == {"file": "outputs_Tab2.tsv"}
    assert data["items"][0]["state"] == "open"
    assert data["items"][0]["created"] == "2026-10-05T10:12:00Z"
    assert "reviewers" not in data


@pytest.mark.parametrize(
    "change",
    [
        {"id": "not-a-ulid"},
        {"kind": "note"},
        {"state": "resolved"},
        {"resolved_by": "mkoenig", "resolved": "2026-10-06T08:00:00Z"},
        {"created": "2026-10-05T10:12:00"},
        {"target": {"rows": {"label": "x"}}},
        {"text": ""},
    ],
)
def test_review_item_rejects(change):
    with pytest.raises(ValidationError):
        Review.model_validate({"status": "draft", "items": [{**ITEM, **change}]})


def test_resolved_item():
    item = {
        **ITEM,
        "state": "resolved",
        "resolved_by": "mkoenig",
        "resolved": "2026-10-06T08:00:00Z",
    }
    assert (
        Review.model_validate({"status": "approved", "items": [item]}).items[0].state
        == "resolved"
    )


def test_canonical_study_json_writes_whole_ratings_as_integers():
    study = StudyMetadata.model_validate(
        {
            **STUDY,
            "curators": [
                {"user": "a", "rating": 1},
                {"user": "b", "rating": 2.5},
                {"user": "c"},
                {"user": "d", "rating": 3.0},
            ],
        }
    )
    text = canonical_study_json(study)
    ratings = [line.strip() for line in text.splitlines() if '"rating"' in line]
    assert ratings == ['"rating": 1', '"rating": 2.5', '"rating": 0', '"rating": 3']
    assert canonical_study_json(StudyMetadata.model_validate_json(text)) == text
