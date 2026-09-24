"""Local administrator maintenance using the same leases as publication."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from pkdb_server.db.models.audit import AuditEvent
from pkdb_server.db.models.credentials import ApiKey, BrowserSession
from pkdb_server.db.models.limits import WorkLease
from pkdb_server.db.models.saved_queries import SavedQuery
from pkdb_server.db.models.users import AccountThrottle, Token
from pkdb_server.files.cleanup import cleanup_expired_files, cleanup_untracked_files
from pkdb_server.services.profiles import ProfileService


def cleanup(session_factory, file_store, *, now=None):
    now = now or datetime.now(UTC)
    with session_factory.begin() as session:
        removed = session.execute(
            delete(SavedQuery)
            .where(SavedQuery.expires_at <= now)
            .returning(SavedQuery.id)
        )
        count = sum(1 for _ in removed)
        for model in (WorkLease, AccountThrottle):
            session.execute(delete(model).where(model.expires_at <= now))
        for model in (ApiKey, BrowserSession, Token):
            session.execute(
                delete(model).where(model.expires_at < now - timedelta(days=30))
            )
        session.execute(
            delete(AuditEvent).where(AuditEvent.created_at < now - timedelta(days=365))
        )
    return {
        "saved_queries": count,
        "orphan_avatars": ProfileService(
            session_factory, file_store.root
        ).cleanup_orphans(),
        "expired_files": cleanup_expired_files(now, session_factory, file_store),
        "untracked_files": cleanup_untracked_files(now, session_factory, file_store),
    }
