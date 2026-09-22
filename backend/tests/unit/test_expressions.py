"""Legacy source expressions have an explicit grammar; they are never code."""

import pytest

from pkdb.importers.expressions import bind_columns, split_entry
from pkdb.schemas.validation import StudyValidationError


def test_parallel_splits_broadcast_scalar_fields():
    assert split_entry({"name": "a||b", "value": "0||2", "unit": "mg"}) == [
        {"name": "a", "value": "0", "unit": "mg"},
        {"name": "b", "value": "2", "unit": "mg"},
    ]


def test_mismatched_splits_are_rejected():
    with pytest.raises(StudyValidationError):
        split_entry({"name": "a||b", "value": "1||2||3"})


def test_nested_mapping_preserves_zero():
    assert bind_columns({"characteristica": [{"mean": "col==x"}]}, {"x": 0}) == {
        "characteristica": [{"mean": 0}]
    }


def test_non_column_expression_is_rejected():
    with pytest.raises(StudyValidationError):
        bind_columns({"mean": "eval==1+1"}, {"x": 0})


def test_mapped_interventions_expand_cell_lists():
    template = split_entry({"interventions": "col==interventions"})[0]
    bound = bind_columns(template, {"interventions": "API10, CYC100"})
    assert split_entry(bound) == [{"interventions": ["API10", "CYC100"]}]
