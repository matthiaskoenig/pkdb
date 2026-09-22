"""Vocabulary conversion preserves scientific identifiers and choices."""

from tools.backend_migration.vocabulary import convert_vocabulary


def test_preserves_ids_and_resolves_choice_names():
    """Choice labels and numeric molecular metadata survive conversion."""
    nodes = [
        {
            "sid": "sex",
            "name": "sex",
            "ntype": "measurement_type",
            "dtype": "categorical",
            "measurement_type": {"units": [], "choices": ["male"]},
            "parents": [],
        },
        {
            "sid": "male",
            "name": "M",
            "ntype": "choice",
            "dtype": "undefined",
            "parents": ["sex"],
        },
        {
            "sid": "drug-id",
            "name": "drug",
            "ntype": "substance",
            "substance": {"mass": "500.0", "charge": "0", "formula": "C"},
            "parents": [],
        },
    ]
    snapshot = convert_vocabulary(nodes, time_required=set(), can_negative=set())
    by_id = {node["sid"]: node for node in snapshot["nodes"]}
    assert by_id["sex"]["definition"]["choices"] == ["M"]
    assert by_id["drug-id"]["definition"]["mass"] == 500.0
    assert by_id["male"]["parents"] == ["sex"]
