"""Test reference."""

from pathlib import Path

import pytest

from pkdb_data.management.reference import create_reference_for_pmid, reference_filename
from pkdb_data.management.utils import read_json


@pytest.mark.parametrize("pmid", ["4029248", "10877011"])
def test_create_reference_for_pmid(pmid: str, tmp_path: Path) -> None:
    """Test creation of reference from valid pmid."""
    create_reference_for_pmid(study_name=pmid, pmid=pmid, output_path=tmp_path)
    reference_path = tmp_path / reference_filename
    assert reference_path.exists()
    json = read_json(reference_path)
    assert json
    assert "pmid" in json
    assert json["pmid"] == int(pmid)


@pytest.mark.parametrize("pmid", ["Abernethy1985"])
def test_create_reference_for_no_pmid(pmid: str, tmp_path: Path) -> None:
    """Test creation of reference for invalid pmid."""
    create_reference_for_pmid(study_name=pmid, pmid=pmid, output_path=tmp_path)
    reference_path = tmp_path / reference_filename
    assert reference_path.exists()
    json = read_json(reference_path)
    assert json
    assert "pmid" not in json
