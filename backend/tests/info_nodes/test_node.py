"""Test info node functionality."""

from pymetadata.core.miriam import BQB

from pkdb_data.info_nodes.node import Substance


def test_substance() -> None:
    """Test substance."""
    s1 = Substance(sid="coffee", name="coffee", description="coffee")
    assert s1
    assert s1.annotations == []
    assert s1.sid == "coffee"
    assert s1.name == "coffee"


def test_substance_with_chebi() -> None:
    """Test substance with chebi information."""
    s = Substance(
        sid="13cmet",
        name="13C-methacetin",
        description="13C-methacetin",
        annotations=[(BQB.IS, "chebi/CHEBI:139355")],
    )

    assert s
    assert s.chebi()
    assert s.chebi() == "CHEBI:139355"
