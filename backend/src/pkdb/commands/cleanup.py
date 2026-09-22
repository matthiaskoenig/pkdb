"""Local administrator maintenance using the same leases as publication."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from pkdb.db.models.credentials import ApiKey, BrowserSession
from pkdb.db.models.drafts import ReferenceDraft, StudyDraft
from pkdb.db.models.limits import WorkLease
from pkdb.db.models.mfa import AuditEvent
from pkdb.db.models.providers import OAuthTransaction
from pkdb.db.models.saved_queries import SavedQuery
from pkdb.db.models.users import AccountThrottle, Token
from pkdb.files.cleanup import cleanup_expired_files, cleanup_untracked_files
from pkdb.services.profiles import ProfileService


def cleanup(session_factory, file_store, *, now=None):
    now = now or datetime.now(UTC)
    with session_factory.begin() as session:
        removed = session.execute(
            delete(SavedQuery)
            .where(SavedQuery.expires_at <= now)
            .returning(SavedQuery.id)
        )
        count = sum(1 for _ in removed)
        draft_count = 0
        for model in (StudyDraft, ReferenceDraft):
            expired = session.execute(
                delete(model).where(model.expires_at <= now).returning(model.sid)
            )
            draft_count += sum(1 for _ in expired)
        for model in (OAuthTransaction, WorkLease, AccountThrottle):
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
        "drafts": draft_count,
        "orphan_avatars": ProfileService(
            session_factory, file_store.root
        ).cleanup_orphans(),
        "expired_files": cleanup_expired_files(now, session_factory, file_store),
        "untracked_files": cleanup_untracked_files(now, session_factory, file_store),
    }
