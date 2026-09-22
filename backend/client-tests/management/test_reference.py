"""Test reference."""

from io import StringIO
from pathlib import Path

import pytest
from Bio import Entrez
from pkdb_data.management.reference import create_reference_for_pmid, reference_filename
from pkdb_data.management.utils import read_json


@pytest.mark.parametrize("pmid", ["4029248", "10877011"])
def test_create_reference_for_pmid(
    pmid: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test creation of reference from valid pmid."""
    xml = """<PubmedArticleSet><PubmedArticle><MedlineCitation>
    <DateCompleted><Year>1985</Year><Month>05</Month><Day>01</Day></DateCompleted>
    <Article><Journal><Title>Test journal</Title></Journal>
    <ArticleTitle>Test publication</ArticleTitle>
    <AuthorList><Author><ForeName>Test</ForeName><LastName>Author</LastName>
    </Author></AuthorList></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"""

    def fetch(**kwargs):
        assert kwargs == {"db": "pubmed", "id": int(pmid), "retmode": "xml"}
        return StringIO(xml)

    monkeypatch.setattr(Entrez, "efetch", fetch)
    create_reference_for_pmid(study_name=pmid, pmid=pmid, output_path=tmp_path)
    reference_path = tmp_path / reference_filename
    assert reference_path.exists()
    json = read_json(reference_path)
    assert json
    assert "pmid" in json
    assert json["pmid"] == int(pmid)
    assert json["title"] == "Test publication"
    assert json["date"] == "1985-05-01"
    assert json["authors"] == [{"first_name": "Test", "last_name": "Author"}]


@pytest.mark.parametrize("pmid", ["Abernethy1985"])
def test_create_reference_for_no_pmid(pmid: str, tmp_path: Path) -> None:
    """Test creation of reference for invalid pmid."""
    create_reference_for_pmid(study_name=pmid, pmid=pmid, output_path=tmp_path)
    reference_path = tmp_path / reference_filename
    assert reference_path.exists()
    json = read_json(reference_path)
    assert json
    assert "pmid" not in json
