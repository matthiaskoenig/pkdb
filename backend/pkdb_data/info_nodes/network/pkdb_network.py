"""Create network graph of InfoNodes.

- creates network view
- creates SIF network file
- creates node attribute TSV
"""

import json
import logging
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path

import networkx
import networkx as nx
import pandas as pd
from pymetadata.console import console

from pkdb_data import RESOURCES_DIR

os.environ["PY4CYTOSCAPE_DETAIL_LOGGER_DIR"] = str(tempfile.gettempdir())
import py4cytoscape as p4c
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


def read_json(path: Path) -> dict | None:
    """Read info node json."""
    with open(path) as f:
        try:
            json_data: dict[str, str] = json.loads(
                f.read(), object_pairs_hook=dict_raise_on_duplicates
            )
        except json.decoder.JSONDecodeError as err:
            logger.warning("%s in %s", err, path)
            return None
        except ValueError as err:
            logger.warning("%s in %s", err, path)
            return None

    return json_data


def dict_raise_on_duplicates(
    ordered_pairs: Iterable[tuple[str, str]],
) -> dict[str, str]:
    """Reject duplicate keys."""
    d = {}
    for k, v in ordered_pairs:
        if k in d:
            raise ValueError(f"duplicate key: {k!r}")
        d[k] = v
    return d


def create_graph(
    info_nodes_path: Path, sif_path: Path, nodes_table_path: Path
) -> networkx.Graph:
    """Create graph and edges from given Info Nodes JSON.

    Stores the graph edges as SIF for import in cytoscape.
    """
    console.print(f"graph from info nodes: {info_nodes_path}")
    node_js = read_json(info_nodes_path)
    df_nodes = pd.DataFrame(node_js)
    links = []
    for _, row in df_nodes.iterrows():
        df = pd.DataFrame(row["parents"], columns=["parent"])
        df["node"] = row["sid"]
        links.append(df)
    df_edges: pd.DataFrame = pd.concat(links)
    df_edges["interaction"] = "is_a"

    graph: networkx.Graph = nx.from_pandas_edgelist(
        df_edges, source="node", target="parent", create_using=nx.Graph()
    )

    # export edges to SIF network format
    console.print(f"write edge file: {sif_path}")
    df_edges[["node", "interaction", "parent"]].to_csv(
        sif_path, sep="\t", index=False, header=False
    )
    # export nodes to table
    console.print(f"write nodes file: {nodes_table_path}")
    df_nodes[
        [
            "sid",
            "name",
            "ntype",
            "dtype",
            "label",
            "description",
            "annotations",
            "children",
        ]
    ].to_csv(nodes_table_path, sep="\t", index=False)

    return graph


def visualize_cytoscape(
    sif_path: Path,
    nodes_table_path: Path,
    style_path: Path,
    delete_session: bool = False,
) -> int | None:
    """Visualize the network in cytoscape.

    * Start cytoscape
    * Load SIF file via `File -> Import Network from file -> ./results/pkdb_network.sif`
    * Load node data via `File -> Import Table from file -> ./results/pkdb_nodes.tsv`
    * Load styles va `File -> Import Stylse from file -> ./results/pkdb_styles.xml`
    * Select network and apply style.
    """
    try:
        console.print(p4c.cytoscape_version_info())

        if delete_session:
            p4c.session.close_session(save_before_closing=False)

        networks_views = p4c.networks.import_network_from_file(str(sif_path))
        # console.print(f"{networks_views}")
        network = networks_views["networks"][0]
        p4c.set_current_view(network=network)  # set the base network

        # load node table data
        df = pd.read_csv(nodes_table_path, sep="\t")
        p4c.load_table_data(
            df,
            table="node",
            network=network,
            data_key_column="sid",
            table_key_column="name",
        )

        # load style and set style
        p4c.import_visual_styles(str(style_path))
        p4c.set_visual_style("pkdb", network=network)

        return int(network)

    except RequestException:
        logger.error(
            "Could not connect to a running Cytoscape instance. "
            "Start Cytoscape before running the python script."
        )
        return None


if __name__ == "__main__":
    from pkdb_data.log import enable_rich_logging

    enable_rich_logging()
    info_nodes_json = RESOURCES_DIR / "json" / "info_nodes.json"

    results_dir = Path(__file__).parent / "results"
    sif_path = results_dir / "pkdb_network.sif"
    nodes_table_path = results_dir / "pkdb_nodes.tsv"
    style_path = results_dir / "pkdb_styles.xml"

    create_graph(
        info_nodes_path=info_nodes_json,
        sif_path=sif_path,
        nodes_table_path=nodes_table_path,
    )
    visualize_cytoscape(
        sif_path=sif_path,
        nodes_table_path=nodes_table_path,
        style_path=style_path,
        delete_session=True,
    )
