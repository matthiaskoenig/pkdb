"""Test the helper functions."""

import pytest
from rest_framework import serializers

from pkdb_app.utils import (
    _validate_not_allowed_key,
    _validate_required_key,
    _validate_required_key_and_value,
    _validate_required_key_and_value_or_nr,
    clean_import,
    create_choices,
    create_if_exists,
    list_duplicates,
    recursive_iter,
    set_keys,
)


def test_list_duplicates() -> None:
    """Only the items which occur more than once are returned, once each."""
    assert sorted(list_duplicates(["a", "b", "a", "c", "a", "c"])) == ["a", "c"]
    assert list_duplicates(["a", "b"]) == []


def test_create_choices() -> None:
    """Strings are their own key, other items provide `key`."""

    class Item:
        key = "item"

    assert create_choices(["a", Item()]) == [("a", "a"), ("item", "item")]


def test_create_if_exists() -> None:
    """The value is copied only when the source has the key."""
    assert create_if_exists({"a": 1}, "a", {}, "b") == {"b": 1}
    assert create_if_exists({"a": 1}, "x", {}, "b") == {}


def test_clean_import() -> None:
    """Empty values and nan are dropped, everything else is kept."""
    data = {"a": 1, "b": "", "c": " ", "d": float("nan"), "e": "NA", "f": "text"}
    assert clean_import(data) == {"a": 1, "e": "NA", "f": "text"}


def test_recursive_iter() -> None:
    """The nested structure is flattened to key tuples."""
    data = {"a": {"b": 1}, "c": [2, {"d": 3}], "e": []}
    assert dict(recursive_iter(data)) == {
        ("a", "b"): 1,
        ("c", 0): 2,
        ("c", 1, "d"): 3,
        ("e",): None,
    }


def test_set_keys() -> None:
    """The value is set at the nested key."""
    data = {"a": {"b": 1}}
    set_keys(data, 2, "a", "b")
    assert data == {"a": {"b": 2}}


def test_validate_required_key_and_value() -> None:
    """A missing key and a null value are errors."""
    _validate_required_key_and_value({"a": 1}, "a")
    with pytest.raises(serializers.ValidationError):
        _validate_required_key_and_value({}, "a")
    with pytest.raises(serializers.ValidationError):
        _validate_required_key_and_value({"a": None}, "a", details="details")


def test_validate_required_key_and_value_or_nr() -> None:
    """The value `NR` (not reported) is accepted and becomes None."""
    attrs = {"a": "NR"}
    _validate_required_key_and_value_or_nr(attrs, "a")
    assert attrs == {"a": None}
    with pytest.raises(serializers.ValidationError):
        _validate_required_key_and_value_or_nr({}, "a")


def test_validate_required_key() -> None:
    """Only the key is required, the value can be None."""
    _validate_required_key({"a": None}, "a")
    with pytest.raises(serializers.ValidationError):
        _validate_required_key({}, "a")


def test_validate_not_allowed_key() -> None:
    """The key must not exist."""
    _validate_not_allowed_key({}, "a")
    with pytest.raises(serializers.ValidationError):
        _validate_not_allowed_key({"a": 1}, "a")
