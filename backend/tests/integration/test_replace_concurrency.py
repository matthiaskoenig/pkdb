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


@pytest.fixture
def key_principal(ingestion_context, session_factory):
    from datetime import UTC, datetime, timedelta

    from pkdb_server.db.models.credentials import ApiKey

    _, principal = ingestion_context
    with session_factory.begin() as session:
        key = ApiKey(
            user_id=principal.user_id,
            name="batch",
            prefix="test",
            digest="a" * 64,
            scopes=["read", "studies:write"],
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        session.add(key)
        session.flush()
        return principal.model_copy(
            update={
                "credential_kind": "api_key",
                "credential_id": key.id,
                "scopes": frozenset(key.scopes),
            }
        )


def test_same_key_distinct_publications_overlap(
    ingestion_context, valid_bundle, session_factory, key_principal, monkeypatch
):
    from pkdb_server.db import replace

    ingestion, _ = ingestion_context
    first = ingestion.validate(valid_bundle, key_principal)
    changed = valid_bundle.model_copy(deep=True)
    changed.study["sid"] = "SECOND"
    changed.study["reference"] = "REF2"
    changed.reference["sid"] = "REF2"
    second = ingestion.validate(changed, key_principal)
    barrier = Barrier(2)
    original = replace.insert_graph

    def overlapping(*args):
        # Both publications must reach graph insertion while holding identity locks.
        barrier.wait(timeout=5)
        return original(*args)

    monkeypatch.setattr(replace, "insert_graph", overlapping)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda prepared: ingestion._publish(prepared, key_principal, []),
                [first, second],
            )
        )
    assert all(result.created for result in results)
    monkeypatch.setattr(replace, "insert_graph", original)
    for prepared, result in zip([first, second], results, strict=True):
        assert (
            read_study(prepared.study.sid, key_principal, session_factory)
            == prepared.study
        )
        serial = ingestion._publish(prepared, key_principal, [])
        assert serial.digest == result.digest
        assert serial.counts == result.counts
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Study)) == 2


@pytest.mark.parametrize("mutation", ["revoke", "disable", "role"])
def test_publication_identity_locks_block_mutations(
    session_factory, key_principal, mutation
):
    from datetime import UTC, datetime
    from threading import Event

    from sqlalchemy import update

    from pkdb_server.db.models.credentials import ApiKey
    from pkdb_server.services.authentication import revalidate_principal

    entered = Event()
    completed = Event()

    def mutate():
        with session_factory.begin() as session:
            entered.set()
            if mutation == "revoke":
                session.execute(
                    update(ApiKey)
                    .where(ApiKey.id == key_principal.credential_id)
                    .values(revoked_at=datetime.now(UTC))
                )
            else:
                values = (
                    {"active": False} if mutation == "disable" else {"role": "user"}
                )
                session.execute(
                    update(User)
                    .where(User.id == key_principal.user_id)
                    .values(**values)
                )
        completed.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with session_factory.begin() as session:
            revalidate_principal(key_principal, session, publication_lock=True)
            future = pool.submit(mutate)
            assert entered.wait(2)
            assert not completed.wait(0.15)
        future.result(timeout=5)
    assert completed.is_set()
