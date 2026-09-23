from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import event, func, select

from pkdb_server.db.models.studies import Study
from pkdb_server.db.models.users import User
from pkdb_server.db.models.vocabulary import VocabularyVersion
from pkdb_server.db.read import assemble_study, read_study
from pkdb_server.services.authentication import AuthenticationFailed
from pkdb_server.services.ingestion import PublicationConflict


def test_concurrent_first_upload_has_one_complete_root(
    ingestion_context, valid_bundle, session_factory
):
    ingestion, principal = ingestion_context
    first = ingestion.validate(valid_bundle, principal)
    changed = valid_bundle.model_copy(deep=True)
    changed.study["outputset"]["outputs"][0]["mean"] = 7.0
    second = ingestion.validate(changed, principal)
    barrier = Barrier(2)

    def publish(prepared):
        barrier.wait(timeout=5)
        return ingestion._publish(prepared, principal, [])

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(publish, [first, second]))
    assert sum(result.created for result in results) == 1
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Study)) == 1
    assert read_study(first.study.sid, principal, session_factory) in (
        first.study,
        second.study,
    )


def test_old_snapshot_sees_entire_previous_graph(
    ingestion_context, valid_bundle, session_factory
):
    ingestion, principal = ingestion_context
    result = ingestion.replace(valid_bundle, principal)
    with session_factory() as reader:
        reader.connection(execution_options={"isolation_level": "REPEATABLE READ"})
        root = reader.scalar(select(Study).where(Study.sid == result.sid))
        before = assemble_study(root, reader)
        changed = valid_bundle.model_copy(deep=True)
        changed.study.pop("outputset")
        ingestion.replace(changed, principal)
        assert assemble_study(root, reader) == before
    assert read_study(result.sid, principal, session_factory).measurements == []


@pytest.mark.parametrize("change", ["vocabulary", "authorization"])
def test_mutable_state_is_rechecked(
    ingestion_context, valid_bundle, session_factory, change
):
    ingestion, principal = ingestion_context
    prepared = ingestion.validate(valid_bundle, principal)
    with session_factory.begin() as session:
        if change == "vocabulary":
            session.get(VocabularyVersion, 1).version = "new"
        else:
            session.get(User, principal.user_id).active = False
    with pytest.raises(
        PublicationConflict if change == "vocabulary" else AuthenticationFailed
    ):
        ingestion._publish(prepared, principal, [])
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Study)) == 0


def test_failure_before_commit_preserves_previous_graph(
    ingestion_context, valid_bundle, session_factory
):
    ingestion, principal = ingestion_context
    result = ingestion.replace(valid_bundle, principal)
    before = read_study(result.sid, principal, session_factory)

    def reject_commit(session):
        raise RuntimeError("injected commit failure")

    event.listen(session_factory, "before_commit", reject_commit)
    try:
        with pytest.raises(RuntimeError, match="injected commit"):
            ingestion.replace(valid_bundle, principal)
    finally:
        event.remove(session_factory, "before_commit", reject_commit)
    assert read_study(result.sid, principal, session_factory) == before


def test_measurement_query_count_is_bounded(
    ingestion_context, valid_bundle, session_factory
):
    ingestion, principal = ingestion_context
    engine = session_factory.kw["bind"]
    counts = []
    for size in [10, 1000]:
        bundle = valid_bundle.model_copy(deep=True)
        template = bundle.study["outputset"]["outputs"][0]
        bundle.study["outputset"]["outputs"] = [
            dict(template, mean=float(index)) for index in range(size)
        ]
        statements = []

        def count_statement(
            connection, cursor, statement, parameters, context, executemany
        ):
            statements.append(statement)

        event.listen(engine, "before_cursor_execute", count_statement)
        try:
            ingestion.replace(bundle, principal)
        finally:
            event.remove(engine, "before_cursor_execute", count_statement)
        counts.append(len(statements))
    assert counts[1] <= counts[0] + 12
