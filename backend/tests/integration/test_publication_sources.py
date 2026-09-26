import pytest
from sqlalchemy import func, select

from pkdb.schemas.provenance import DataImport
from pkdb_server.db.models.studies import Publication, Study
from pkdb_server.db.read import read_study
from pkdb_server.services.ingestion import PublicationConflict


def imported(bundle, sid="OSP_EXAMPLE"):
    other = bundle.model_copy(deep=True)
    other.study.update(sid=sid, name=sid, reference=sid + ":reference")
    other.reference.update(sid=sid + ":reference", title="Independent OSP metadata")
    other.study["provenance"] = dict(
        kind="data_import",
        source_key="osp.observed-data",
        release="v1.9",
        revision="abcdef",
        importer="pkdb.osp",
        importer_version="1",
        assets=[dict(url="https://example.org/data.xlsx", sha256="0" * 64)],
    )
    return other


def test_same_publication_different_sources_and_repeat_import(
    ingestion_context,
    valid_bundle,
    session_factory,
):
    service, principal = ingestion_context
    valid_bundle.reference.update(pmid="12345", doi="10.1234/example")
    manual = service.replace(valid_bundle, principal)
    before = read_study(manual.sid, principal, session_factory)
    automatic = imported(valid_bundle)
    automatic.reference.pop("pmid")  # DOI alias joins the shared publication.
    automatic.study["groupset"]["groups"][0]["count"] = None
    result = service.replace(automatic, principal)
    assert result.created
    automatic.study["provenance"]["release"] = "v2.0"
    assert not service.replace(automatic, principal).created
    restored = read_study(result.sid, principal, session_factory)
    assert isinstance(restored.metadata.provenance, DataImport)
    assert restored.metadata.provenance.release == "v2.0"
    assert restored.groups[0].count is None
    assert read_study(manual.sid, principal, session_factory) == before
    with session_factory() as session:
        roots = list(session.scalars(select(Study)))
        assert len(roots) == 2
        assert roots[0].publication_id == roots[1].publication_id
        assert roots[0].reference_id != roots[1].reference_id
        assert session.scalar(select(func.count()).select_from(Publication)) == 1
    duplicate = imported(valid_bundle, "OSP_DUPLICATE")
    with pytest.raises(PublicationConflict, match="already exists"):
        service.replace(duplicate, principal)
    automatic.study["provenance"]["source_key"] = "another-source"
    with pytest.raises(PublicationConflict, match="acquisition source"):
        service.replace(automatic, principal)
    assert read_study(manual.sid, principal, session_factory) == before


def test_identifier_change_rejected_and_enrichment_allowed(
    ingestion_context,
    valid_bundle,
    session_factory,
):
    service, principal = ingestion_context
    valid_bundle.reference.update(pmid="12345")
    result = service.replace(valid_bundle, principal)
    valid_bundle.reference.update(doi="10.1234/example")
    service.replace(valid_bundle, principal)
    before = read_study(result.sid, principal, session_factory)
    valid_bundle.reference.update(pmid="99999")
    with pytest.raises(PublicationConflict, match="identifier conflicts"):
        service.replace(valid_bundle, principal)
    assert read_study(result.sid, principal, session_factory) == before
