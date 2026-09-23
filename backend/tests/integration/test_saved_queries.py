import pytest

from pkdb.schemas.queries import Predicate, QuerySpec
from pkdb.schemas.security import Principal
from pkdb_server.services.authorization import AuthorizationDenied
from pkdb_server.services.queries import QueryService


def test_saved_filter_is_not_a_capability(
    ingestion_context, valid_bundle, session_factory
):
    from pkdb_server.services.exports import ExportService

    ingestion, creator = ingestion_context
    valid_bundle.study["access"] = "private"
    ingestion.replace(valid_bundle, creator)
    exports = ExportService(session_factory, QueryService(session_factory))
    query = QuerySpec(
        entity="studies",
        predicates=[Predicate(field="sid", value=valid_bundle.study["sid"])],
    )
    identifier = exports.create_filter(query, creator)
    with pytest.raises(AuthorizationDenied):
        next(exports.stream_export(identifier, "csv", Principal()))


def test_export_limits_release_capacity(
    ingestion_context, valid_bundle, session_factory
):
    from pkdb_server.services.exports import ExportLimit, ExportService

    ingestion, creator = ingestion_context
    ingestion.replace(valid_bundle, creator)
    exports = ExportService(session_factory, QueryService(session_factory))
    identifier = exports.create_filter(QuerySpec(entity="studies"), creator)
    exports.max_bytes = 1
    with pytest.raises(ExportLimit, match="byte limit"):
        next(exports.stream_export(identifier, "csv", creator))
    exports.max_bytes = 100_000
    for _ in range(3):
        stream = exports.stream_export(identifier, "csv", creator)
        assert next(stream).startswith(b",sid,")
        stream.close()


def test_export_rechecks_visibility_and_account(
    ingestion_context, valid_bundle, session_factory
):
    from sqlalchemy import update

    from pkdb_server.db.models.studies import Study
    from pkdb_server.db.models.users import User
    from pkdb_server.services.exports import ExportService

    ingestion, creator = ingestion_context
    valid_bundle.study["access"] = "private"
    ingestion.replace(valid_bundle, creator)
    # Fixture publication is an administrative state transition.
    with session_factory.begin() as session:
        session.execute(update(Study).values(access="public"))
    exports = ExportService(session_factory, QueryService(session_factory))
    public_id = exports.create_filter(QuerySpec(entity="studies"), Principal())
    owned_id = exports.create_filter(QuerySpec(entity="studies"), creator)
    with session_factory.begin() as session:
        session.execute(update(Study).values(access="private"))
    with pytest.raises(AuthorizationDenied, match="Authentication required"):
        next(exports.stream_export(public_id, "csv", Principal()))
    with session_factory.begin() as session:
        reader = User(username="export-reader", role="user", active=True)
        session.add(reader)
        session.flush()
        reader_principal = Principal(
            user_id=reader.id, username=reader.username, role=reader.role
        )
    assert (
        b"".join(exports.stream_export(public_id, "csv", reader_principal)) == b'""\n'
    )
    with session_factory.begin() as session:
        session.execute(
            update(User).where(User.id == creator.user_id).values(active=False)
        )
    from pkdb_server.services.authentication import AuthenticationFailed

    with pytest.raises(AuthenticationFailed, match="Inactive"):
        next(exports.stream_export(owned_id, "csv", creator))


def test_expired_saved_filter_is_unavailable(ingestion_context, session_factory):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    from pkdb_server.db.models.saved_queries import SavedQuery
    from pkdb_server.services.exports import ExportService

    _, creator = ingestion_context
    exports = ExportService(session_factory, QueryService(session_factory))
    identifier = exports.create_filter(QuerySpec(entity="studies"), creator)
    with session_factory.begin() as session:
        session.execute(
            update(SavedQuery)
            .where(SavedQuery.id == identifier)
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
    with pytest.raises(LookupError, match="expired"):
        next(exports.stream_export(identifier, "csv", creator))


def test_zip_snapshot_stays_consistent_during_atomic_replacement(
    ingestion_context, valid_bundle, session_factory, monkeypatch
):
    import csv
    from io import BytesIO, StringIO
    from zipfile import ZipFile

    from pkdb.schemas.filters import FilterSpec
    from pkdb_server.services.exports import ExportService

    ingestion, creator = ingestion_context
    ingestion.replace(valid_bundle, creator)
    queries = QueryService(session_factory)
    outputs = QuerySpec(
        entity="outputs", predicates=[Predicate(field="normed", value=True)]
    )
    before = queries.search(outputs, creator).items[0]["mean"]
    exports = ExportService(session_factory, queries)
    identifier = exports.create_filter(FilterSpec(), creator)
    original = exports.analysis.iter_rows
    replaced = False

    def replace_between_tables(session, entity, query, principal, **kwargs):
        nonlocal replaced
        yield from original(session, entity, query, principal, **kwargs)
        if entity == "studies" and not replaced:
            valid_bundle.study["outputset"]["outputs"][0]["mean"] *= 2
            ingestion.replace(valid_bundle, creator)
            replaced = True

    monkeypatch.setattr(exports.analysis, "iter_rows", replace_between_tables)

    def exported_mean():
        content = b"".join(exports.stream_export(identifier, "zip", creator))
        with ZipFile(BytesIO(content)) as archive:
            rows = list(csv.DictReader(StringIO(archive.read("outputs.csv").decode())))
            assert len(rows) == 1
            return float(rows[0]["mean"])

    assert exported_mean() == before
    assert replaced
    assert queries.search(outputs, creator).items[0]["mean"] == before * 2
    assert exported_mean() == before * 2


def test_saved_filter_rechecks_removed_curator(
    ingestion_context, valid_bundle, session_factory
):
    from sqlalchemy import delete, select

    from pkdb.schemas.filters import FilterSpec
    from pkdb_server.db.models.studies import Study, StudyGrant
    from pkdb_server.db.models.users import User
    from pkdb_server.services.exports import ExportService

    ingestion, creator = ingestion_context
    valid_bundle.study["access"] = "private"
    ingestion.replace(valid_bundle, creator)
    with session_factory.begin() as session:
        user = User(username="download-curator", role="curator", active=True)
        session.add(user)
        session.flush()
        actor = Principal(user_id=user.id, username=user.username, role=user.role)
        session.add(
            StudyGrant(
                study_id=session.scalar(select(Study.id)),
                user_id=user.id,
                role="curator",
            )
        )
    exports = ExportService(session_factory, QueryService(session_factory))
    identifier = exports.create_filter(FilterSpec(), actor)
    assert exports.overview(identifier, actor)["outputs"] == 1
    with session_factory.begin() as session:
        session.execute(delete(StudyGrant).where(StudyGrant.user_id == actor.user_id))
    assert exports.overview(identifier, actor)["outputs"] == 0
    from io import BytesIO
    from zipfile import ZipFile

    with ZipFile(
        BytesIO(b"".join(exports.stream_export(identifier, "zip", actor)))
    ) as archive:
        assert archive.read("outputs.csv") == b'""\n'
