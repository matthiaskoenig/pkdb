"""Definition of information tree.

Here all the possible info_nodes are collected.
Dependencies between the nodes are important.
"""

import logging
from copy import deepcopy

from info_nodes.definitions.anthropometry import ANTHROPOMETRY_NODES
from info_nodes.definitions.calculation_type import CALCULATION_NODES
from info_nodes.definitions.demographics import DEMOGRAPHICS_NODES
from info_nodes.definitions.disease import DISEASE_NODES
from info_nodes.definitions.dosing import (
    ADMINISTRATION_FORM_NODES,
    ADMINISTRATION_ROUTE_NODES,
    APPLICATION_NODES,
    DOSING_NODES,
)
from info_nodes.definitions.ethnicity import ETHNICITY_NODES
from info_nodes.definitions.genetics import GENETICS_NODES
from info_nodes.definitions.imaging import IMAGING_MEASUREMENT_NODES
from info_nodes.definitions.lifestyle import LIFESTYLE_NODES
from info_nodes.definitions.measurement import MEASUREMENT_NODES
from info_nodes.definitions.medical_procedure import MEDICAL_PROCEDURE_NODES
from info_nodes.definitions.method import METHOD_NODES
from info_nodes.definitions.specie import SPECIE_NODES
from info_nodes.definitions.substance import SUBSTANCE_NODES
from info_nodes.definitions.tissue import TISSUE_NODES
from info_nodes.graph import NodeIndex
from info_nodes.node import Choice, DType, InfoNode, NType

logger = logging.getLogger(__name__)


def _check_names(nodes: list[InfoNode]) -> None:
    """Names identify non-choice definitions within each authored group."""
    seen = set()
    for node in nodes:
        if node.ntype == NType.CHOICE:
            continue
        if node.name in seen:
            raise ValueError(f"Duplicate node name {node.name!r}")
        seen.add(node.name)


def collect_nodes() -> NodeIndex:
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
        _check_names(nodes)
        NODES.extend(deepcopy(nodes))

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
                        description=f"{info_node.label}: yes.",
                        parents=[sid],
                        name="Y",
                        label=f"{sid}",
                    ),
                    Choice(
                        f"{sid}-NO",
                        description=f"{info_node.label}: no.",
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
                    description=f"{info_node.label}: not reported.",
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
                description=f"All substances for {substance_node}.",
                parents=[f"{substance_node}"],
                name="substances all",
            )
        )

    NODES.extend(SUBSTANCE_SET_NODES)

    return NodeIndex(NODES)
