"""Definition of information tree.

Here all the possible info_nodes are collected.
Dependencies between the nodes are important.
"""

import logging

import pandas as pd
from pymetadata.console import console

from pkdb_data.info_nodes.definitions.anthropometry import ANTHROPOMETRY_NODES
from pkdb_data.info_nodes.definitions.calculation_type import CALCULATION_NODES
from pkdb_data.info_nodes.definitions.demographics import DEMOGRAPHICS_NODES
from pkdb_data.info_nodes.definitions.disease import DISEASE_NODES
from pkdb_data.info_nodes.definitions.dosing import (
    ADMINISTRATION_FORM_NODES,
    ADMINISTRATION_ROUTE_NODES,
    APPLICATION_NODES,
    DOSING_NODES,
)
from pkdb_data.info_nodes.definitions.ethnicity import ETHNICITY_NODES
from pkdb_data.info_nodes.definitions.genetics import GENETICS_NODES
from pkdb_data.info_nodes.definitions.imaging import IMAGING_MEASUREMENT_NODES
from pkdb_data.info_nodes.definitions.lifestyle import LIFESTYLE_NODES
from pkdb_data.info_nodes.definitions.measurement import MEASUREMENT_NODES
from pkdb_data.info_nodes.definitions.medical_procedure import MEDICAL_PROCEDURE_NODES
from pkdb_data.info_nodes.definitions.method import METHOD_NODES
from pkdb_data.info_nodes.definitions.specie import SPECIE_NODES
from pkdb_data.info_nodes.definitions.substance import SUBSTANCE_NODES
from pkdb_data.info_nodes.definitions.tissue import TISSUE_NODES
from pkdb_data.info_nodes.node import Choice, DType, InfoNode, NType

logger = logging.getLogger(__name__)


def _is_duplicate(nodes_df: pd.DataFrame, field: str) -> None:
    """Check for duplicate definitions of given field."""
    _duplicates = nodes_df[nodes_df[field].duplicated(keep="first")]
    _duplicates_no_undefined = _duplicates[_duplicates.ntype != NType.CHOICE]
    if not _duplicates_no_undefined.empty:
        ntype = _duplicates_no_undefined.ntype
        raise ValueError(
            f"For Dtype <{ntype.unique()}> the {field}s are not unique. "
            f"Detail: <{list(getattr(_duplicates_no_undefined, field))}> "
        )


def collect_nodes() -> list[InfoNode]:
    """Collect and create all info nodes."""
    ROOT = "root"
    INTERVENTION = "intervention"  # only used on intervention
    MEASUREMENT = "measurement"  # only used on output/time course

    NODES: list[InfoNode] = [
        InfoNode(ROOT, ROOT, parents=[]),
        InfoNode(INTERVENTION, "intervention", parents=[], dtype=DType.ABSTRACT),
        InfoNode(MEASUREMENT, "measurement", parents=[], dtype=DType.ABSTRACT),
    ]

    # add nodes to nodes list
    nodes_df: pd.DataFrame
    nodes: list[InfoNode]
    for nodes in [
        MEASUREMENT_NODES,
        IMAGING_MEASUREMENT_NODES,
        ANTHROPOMETRY_NODES,
        DEMOGRAPHICS_NODES,
        LIFESTYLE_NODES,
        DISEASE_NODES,
        SPECIE_NODES,
        ETHNICITY_NODES,
        GENETICS_NODES,
        MEDICAL_PROCEDURE_NODES,
        DOSING_NODES,
        ADMINISTRATION_ROUTE_NODES,
        APPLICATION_NODES,
        ADMINISTRATION_FORM_NODES,
        TISSUE_NODES,
        METHOD_NODES,
        SUBSTANCE_NODES,
        CALCULATION_NODES,
    ]:
        nodes_df = pd.DataFrame([node.serialize(nodes) for node in nodes])
        _is_duplicate(nodes_df, "name")

        NODES.extend(nodes)

    # ----------------------
    # Query management
    # ----------------------
    for node in NODES:
        node.query_metadata()

    # -------------------------------------
    # Boolean nodes
    # -------------------------------------
    BOOLEAN_NODES = []
    for info_node in NODES:
        sid = info_node.sid
        # YES/NO info_nodes
        if info_node.dtype == DType.BOOLEAN:
            BOOLEAN_NODES.extend(
                [
                    Choice(
                        sid=f"{sid}-YES",
                        description=f"Yes {info_node.name}.",
                        parents=[sid],
                        name="Y",
                        label=f"{sid}",
                    ),
                    Choice(
                        f"{sid}-NO",
                        description=f"No {info_node.name}.",
                        parents=[sid],
                        name="N",
                        label=f"No {sid}",
                    ),
                ]
            )
        # NR info_nodes
        if info_node.dtype in [
            DType.BOOLEAN,
            DType.CATEGORICAL,
            DType.NUMERIC_CATEGORICAL,
        ]:
            BOOLEAN_NODES.append(
                Choice(
                    sid=f"{sid}-Not-Reported",
                    name="NR",
                    label=f"Not reported {info_node.name}",
                    description=f"Not Reported {info_node.name}.",
                    parents=[sid],
                )
            )

    NODES.extend(BOOLEAN_NODES)

    # -------------------------------------
    # Substance set nodes
    # -------------------------------------
    substance_all_nodes = [
        "medication-duration",
        "medication-amount",
        "medication",
        "dosing",
        "qualitative-dosing",
        "abstinence",
        "consumption",
        "metabolic-ratio",
        "metabolic-phenotype",
        "auc_inf",
        "auc_end",
        "auc_relative",
        "auc_per_dose",
        "aumc_inf",
        "amount",
        "cumulative-amount",
        "concentration",
        "concentration_unbound",
        "clearance",
        "clearance_unbound",
        "clearance_partial",
        "clearance_intrinsic",
        "clearance_renal",
        "clearance_intrinsic_unbound",
        "clearance_renal_unbound",
        "vd",
        "vd_unbound",
        "thalf",
        "tmax",
        "oro-cecal-transit-time",
        "mrt",
        "cmax",
        "kel",
        "kabs",
        "thalf_absorption",
        "fraction_absorbed",
        "plasma_binding",
        "fraction_unbound",
        "recovery",
        "egp",
        "ra",
        "rd",
        "secretion-rate",
    ]

    SUBSTANCE_SET_NODES = []
    for substance_node in substance_all_nodes:
        SUBSTANCE_SET_NODES.append(
            InfoNode(
                sid=f"{substance_node}-substances-all",
                description=f"{substance_node} substances all",
                parents=[f"{substance_node}"],
                name="substances all",
            )
        )

    NODES.extend(SUBSTANCE_SET_NODES)

    # check that all parents exist as nodes and are defined in order
    sids = {n.sid: k for k, n in enumerate(NODES)}
    for k, n in enumerate(NODES):
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

    nodes_df = pd.DataFrame([node.serialize(nodes) for node in NODES])
    _is_duplicate(nodes_df, "sid")

    return NODES


if __name__ == "__main__":
    from pkdb_data.log import enable_rich_logging

    enable_rich_logging()
    nodes: list[InfoNode] = collect_nodes()
    nodes_dict = {node.sid: node for node in nodes}
    console.print(nodes_dict)
    node_t1dm = nodes_dict["type-1-diabetes-mellitus"]
    console.print(node_t1dm.xrefs)
    node_caf = nodes_dict["caf"]
    console.print(node_caf.xrefs)
