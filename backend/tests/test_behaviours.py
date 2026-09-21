"""Test the model behaviours."""

from pkdb_app.behaviours import map_field


def test_map_field() -> None:
    """Every field gets its map field."""
    assert map_field(["value", "mean"]) == ["value_map", "mean_map"]
