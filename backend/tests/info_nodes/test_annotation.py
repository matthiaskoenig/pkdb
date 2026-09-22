"""Test annotations."""

from pymetadata.core.annotation import RDFAnnotation
from pymetadata.core.miriam import BQB

from pkdb_data.info_nodes.annotation import NodeAnnotation


def test_url_annotation() -> None:
    """Test url annotation."""
    a = NodeAnnotation(BQB.IS, "https://mypage/myid")
    assert a


def test_chebi_annotation() -> None:
    """Test chebi annotation."""
    a = NodeAnnotation(BQB.IS_VERSION_OF, "chebi/CHEBI:00012")
    assert a


def test_check_term_pass() -> None:
    """Test check term."""
    a = RDFAnnotation(BQB.IS, "chebi/CHEBI:000012")
    assert a.check_miriam_term() is True


def test_check_collection_fail() -> None:
    """Test failing collection."""
    a = RDFAnnotation(BQB.IS, "234234sdf/CHEBI:000012", validate=False)
    assert a.check_miriam_term() is False


def test_check_term_fail() -> None:
    """Test failing term."""
    a = RDFAnnotation(BQB.IS, "chebi/CHEB:000012", validate=False)
    assert a.check_miriam_term() is False
