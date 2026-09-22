"""Definition of substance information."""

# TODO annotations
# TODO hcc_atlas.py
# TODO reference values?
# TODO labels
# TODO names?
# TODO synonyms

import json
import logging

import pandas as pd
from pymetadata.console import console
from pymetadata.core.miriam import BQB

from pkdb_data.atlas.attend_disease_atlas import ATTEND_DISEASE_ATLAS_NODES
from pkdb_data.atlas.hcc_atlas import HCC_ATLAS_NODES
from pkdb_data.atlas.instrum_diagn_atlas import INSTRUM_DIAGN_ATLAS_NODES
from pkdb_data.atlas.lab_diagn_atlas import LAB_DIAGN_ATLAS_NODES
from pkdb_data.atlas.liver_status_atlas import LIVER_STATUS_ATLAS_NODES
from pkdb_data.atlas.pk_atlas import PK_ATLAS_NODES
from pkdb_data.atlas.subject_charact_atlas import SUBJ_CHARACT_ATLAS_NODES
from pkdb_data.info_nodes.node import (
    DType,
    InfoNode,
    NType,
)
from pkdb_data.management.manage import JSON_PATH


def _is_duplicate(nodes: pd.DataFrame, field: str) -> None:
    """Check for duplicate definitions of given field.

    :raises: ValueError
    """
    _duplicates = nodes[nodes[field].duplicated(keep="first")]
    _duplicates_no_undefined = _duplicates[_duplicates.ntype != NType.CHOICE]
    if not _duplicates_no_undefined.empty:
        ntype = _duplicates_no_undefined.ntype
        raise ValueError(
            f"For Dtype <{ntype.unique()}> the {field}s are not unique. "
            f"Detail: <{list(getattr(_duplicates_no_undefined, field))}> "
        )


def create_ontology_nodes() -> None:
    """Create all JSON files for info nodes upload."""
    logger = logging.getLogger(__name__)

    ATLAS_NODES: list[InfoNode] = [
        # All Info-nodes
        InfoNode(
            "patient",
            description="Patient",
            parents=[],
            dtype=DType.ABSTRACT,
        ),
        InfoNode(
            "laboratory-diagnostics",
            description="Laboratory diagnostics",
            parents=["patient"],
            dtype=DType.ABSTRACT,
        ),
        InfoNode(
            "instrumental-diagnostics",
            description="Instrumental diagnosis",
            parents=["patient"],
            dtype=DType.ABSTRACT,
        ),
        InfoNode(
            "subject-characteristics",
            description="Subject characteristics.",
            parents=["patient"],
            dtype=DType.ABSTRACT,
        ),
        InfoNode(
            "attendant-disease",
            description="Attendant disease.",
            parents=["patient"],
            dtype=DType.ABSTRACT,
        ),
        InfoNode(
            "pharmacokinetic-measurement",
            description="Pharmacokinetic measurement",
            parents=["patient"],
            dtype=DType.ABSTRACT,
        ),
        InfoNode(
            "liver-status",
            description="Liver status.",
            parents=["patient"],
            dtype=DType.ABSTRACT,
        ),
        InfoNode(
            sid="hcc",
            label="Hepatocellular carcinoma",
            description="Hepatocellular carcinoma",
            parents=["patient"],
            synonyms=["Hepatocellular carcinoma"],
            dtype=DType.ABSTRACT,
            annotations=[
                (BQB.IS, "ncit/C3099"),
                (BQB.IS, "doid/DOID:686"),
            ],
        ),
    ]

    # add nodes to nodes list
    nodes_df: pd.DataFrame
    nodes: list[InfoNode]
    for nodes in [
        PK_ATLAS_NODES,
        SUBJ_CHARACT_ATLAS_NODES,
        LAB_DIAGN_ATLAS_NODES,
        INSTRUM_DIAGN_ATLAS_NODES,
        LIVER_STATUS_ATLAS_NODES,
        ATTEND_DISEASE_ATLAS_NODES,
        HCC_ATLAS_NODES,
    ]:
        ATLAS_NODES.extend(nodes)

    # check that all parents exist as nodes and are defined in order
    sids = {n.sid: k for k, n in enumerate(ATLAS_NODES)}
    for k, n in enumerate(ATLAS_NODES):
        for parent in n.parents:
            if parent not in sids:
                logger.error(
                    "parent node with sid %r in node %r does not exist", parent, n.sid
                )
            elif sids[parent] > k:
                logger.error(
                    "parent node <%r> defined after child node <%r>, change order.",
                    parent,
                    n.sid,
                )

    nodes_df = pd.DataFrame([node.serialize(nodes) for node in ATLAS_NODES])

    _is_duplicate(nodes_df, "sid")

    console.print("[blue]serialize info nodes[/]")
    serialized_nodes = [node.serialize(nodes) for node in ATLAS_NODES]

    ontology_path = JSON_PATH / "atlas_ontology.json"
    console.print(f"[blue]write {ontology_path}[/]")
    with open(ontology_path, "w") as fp:
        json.dump(serialized_nodes, fp, indent=2)

    console.log(f"[green bold]Successfully created ontology: file://{ontology_path}[/]")


if __name__ == "__main__":
    from pkdb_data.log import enable_rich_logging

    enable_rich_logging()
    create_ontology_nodes()
