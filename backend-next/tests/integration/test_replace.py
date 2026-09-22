import pytest
from sqlalchemy import func, select

from pkdb.db.models.studies import Study
from pkdb.db.read import read_study
from pkdb.schemas.validation import StudyValidationError


def test_replacement_roundtrips_prepared_graph(
    ingestion_context, valid_bundle, session_factory
):
    ingestion, principal = ingestion_context
    prepared = ingestion.validate(valid_bundle, principal)
    result = ingestion.replace(valid_bundle, principal)
    assert result.created
    assert read_study(result.sid, principal, session_factory) == prepared.study


def test_invalid_replacement_preserves_published_graph(
    ingestion_context, valid_bundle, session_factory
):
    ingestion, principal = ingestion_context
    result = ingestion.replace(valid_bundle, principal)
    before = read_study(result.sid, principal, session_factory)
    broken = valid_bundle.model_copy(deep=True)
    broken.study["sid"] = ""
    with pytest.raises(StudyValidationError):
        ingestion.replace(broken, principal)
    assert read_study(result.sid, principal, session_factory) == before


def test_replacement_keeps_root_and_removes_omitted_children(
    ingestion_context, valid_bundle, session_factory
):
    ingestion, principal = ingestion_context
    ingestion.replace(valid_bundle, principal)
    with session_factory() as session:
        root = session.scalar(select(Study.id))
    valid_bundle.study.pop("outputset")
    result = ingestion.replace(valid_bundle, principal)
    assert not result.created
    assert read_study(result.sid, principal, session_factory).measurements == []
    with session_factory() as session:
        assert session.scalar(select(Study.id)) == root
        assert session.scalar(select(func.count()).select_from(Study)) == 1


def test_failure_after_deletion_rolls_back(
    ingestion_context, valid_bundle, session_factory, monkeypatch
):
    from pkdb.db import replace

    ingestion, principal = ingestion_context
    result = ingestion.replace(valid_bundle, principal)
    before = read_study(result.sid, principal, session_factory)
    real_clear = replace.clear_children

    def fail_after_clear(*args):
        real_clear(*args)
        raise RuntimeError("injected failure")

    monkeypatch.setattr(replace, "clear_children", fail_after_clear)
    with pytest.raises(RuntimeError, match="injected"):
        ingestion.replace(valid_bundle, principal)
    assert read_study(result.sid, principal, session_factory) == before
