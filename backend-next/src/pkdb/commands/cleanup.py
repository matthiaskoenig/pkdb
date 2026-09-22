"""Local administrator maintenance using the same leases as publication."""

from datetime import UTC, datetime

from sqlalchemy import delete

from pkdb.db.models.drafts import ReferenceDraft, StudyDraft
from pkdb.db.models.saved_queries import SavedQuery
from pkdb.files.cleanup import cleanup_expired_files, cleanup_untracked_files


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
    return {
        "saved_queries": count,
        "drafts": draft_count,
        "expired_files": cleanup_expired_files(now, session_factory, file_store),
        "untracked_files": cleanup_untracked_files(now, session_factory, file_store),
    }
