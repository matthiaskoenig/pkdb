"""Test network creation."""

from pathlib import Path

from pkdb_data import RESOURCES_DIR
from pkdb_data.info_nodes.network.pkdb_network import create_graph


def test_info_node_network(tmp_path: Path) -> None:
    """Test creation of info node network for visualization."""
    info_nodes_json = RESOURCES_DIR / "json" / "info_nodes.json"

    sif_path = tmp_path / "pkdb_network.sif"
    nodes_table_path = tmp_path / "pkdb_nodes.tsv"

    create_graph(
        info_nodes_path=info_nodes_json,
        sif_path=sif_path,
        nodes_table_path=nodes_table_path,
    )
    assert sif_path.exists()
    assert nodes_table_path.exists()
