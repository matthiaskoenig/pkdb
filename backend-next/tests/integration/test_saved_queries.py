import pytest

from pkdb.schemas.queries import Predicate, QuerySpec
from pkdb.schemas.security import Principal
from pkdb.services.authorization import AuthorizationDenied
from pkdb.services.queries import QueryService


def test_saved_filter_is_not_a_capability(
    ingestion_context, valid_bundle, session_factory
):
    from pkdb.services.exports import ExportService

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
    from pkdb.services.exports import ExportLimit, ExportService

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

    from pkdb.db.models.studies import Study
    from pkdb.db.models.users import User
    from pkdb.services.exports import ExportService

    ingestion, creator = ingestion_context
    valid_bundle.study["access"] = "public"
    ingestion.replace(valid_bundle, creator)
    exports = ExportService(session_factory, QueryService(session_factory))
    public_id = exports.create_filter(QuerySpec(entity="studies"), Principal())
    owned_id = exports.create_filter(QuerySpec(entity="studies"), creator)
    with session_factory.begin() as session:
        session.execute(update(Study).values(access="private"))
    assert b"".join(exports.stream_export(public_id, "csv", Principal())) == b'""\n'
    with session_factory.begin() as session:
        session.execute(
            update(User).where(User.id == creator.user_id).values(active=False)
        )
    with pytest.raises(AuthorizationDenied, match="Active account"):
        next(exports.stream_export(owned_id, "csv", creator))


def test_expired_saved_filter_is_unavailable(ingestion_context, session_factory):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    from pkdb.db.models.saved_queries import SavedQuery
    from pkdb.services.exports import ExportService

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
