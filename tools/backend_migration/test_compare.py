"""Catch lost values, accidental coercion, and overbroad snapshot exclusions."""

import pytest

from tools.backend_migration.compare import compare_records


@pytest.mark.parametrize(
    ("expected", "actual", "paths"),
    [
        ({"mean": None}, {"mean": 0}, ["$.mean"]),
        ({"count": True}, {"count": 1}, ["$.count"]),
        ({"sid": "A"}, {"sid": "B"}, ["$.sid"]),
        ({"value": 0}, {}, ["$.value"]),
        ({}, {"value": None}, ["$.value"]),
        ([1, 2], [2, 1], ["$[0]", "$[1]"]),
        ([1], [1, 2], ["$[1]"]),
        ({"mean": 1.0}, {"mean": 1.01}, ["$.mean"]),
        ({"value": [0, None]}, {"value": [0, None]}, []),
    ],
)
def test_reports_exact_differences(expected, actual, paths):
    """Test reports exact differences."""
    assert compare_records(expected, actual, ignored_paths=frozenset()) == paths


def test_only_explicit_volatile_path_is_ignored():
    """Test only explicit volatile path is ignored."""
    assert compare_records(
        {"request_id": "old", "record": {"request_id": "a"}},
        {"request_id": "new", "record": {"request_id": "b"}},
        ignored_paths=frozenset({"$.request_id"}),
    ) == ["$.record.request_id"]


def test_same_nan_is_not_silently_equal():
    """Test same nan is not silently equal."""
    assert compare_records(float("nan"), float("nan"), ignored_paths=frozenset()) == [
        "$"
    ]
