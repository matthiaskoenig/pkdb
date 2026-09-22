"""Test TSV creation from excel sheets."""

from pathlib import Path

from pkdb_data.management.tsv import build_tsvs

data_dir: Path = Path(__file__).parent.parent / "data"
xlsx_abernethy1985: Path = data_dir / "studies" / "Abernethy1985.xlsx"


def test_build_tsvs() -> None:
    """Test creation of TSV from excel."""
    build_tsvs(path_xlsx=xlsx_abernethy1985)
