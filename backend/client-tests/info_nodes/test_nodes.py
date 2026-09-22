"""Test nodes functionality."""

import pytest
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
from pkdb_data.info_nodes.definitions.lifestyle import LIFESTYLE_NODES
from pkdb_data.info_nodes.definitions.measurement import MEASUREMENT_NODES
from pkdb_data.info_nodes.definitions.medical_procedure import MEDICAL_PROCEDURE_NODES
from pkdb_data.info_nodes.definitions.method import METHOD_NODES
from pkdb_data.info_nodes.definitions.specie import SPECIE_NODES
from pkdb_data.info_nodes.definitions.substance import SUBSTANCE_NODES
from pkdb_data.info_nodes.definitions.tissue import TISSUE_NODES
from pkdb_data.info_nodes.node import InfoNode, Substance
from pkdb_data.info_nodes.nodes import collect_nodes
from pymetadata.core.miriam import BQB


@pytest.mark.parametrize(
    "nodes",
    [
        MEASUREMENT_NODES,
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
    ],
)
def test_node_set(nodes: list[InfoNode]) -> None:
    """Test given set of nodes."""
    assert nodes
    assert isinstance(nodes, list)


def test_collect_nodes() -> None:
    """Test collection of all nodes."""
    nodes = collect_nodes()
    assert nodes
    assert isinstance(nodes, list)


def test_substance() -> None:
    """Test substance."""
    s = Substance(
        sid="talinolol",
        description="Talinolol is a beta-blocker and subtrate of the P-glycoprotein. "
        "Talinolol contains a stereocenter and consists of two enantiomers. "
        "This is a racemate, i.e. a 1: 1 mixture of (R)- and the (S)-forms.",
        annotations=[
            (BQB.IS, "chebi/CHEBI:135533"),
            (BQB.IS, "pubchem.compound/68770"),
        ],
        synonyms=["57460-41-0", "Cordanum"],
    )
    assert s
