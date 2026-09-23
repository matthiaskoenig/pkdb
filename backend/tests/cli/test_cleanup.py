from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from pkdb_server.db.models.saved_queries import SavedQuery


def test_cleanup_removes_only_expired_saved_filters(session_factory, tmp_path):
    from pkdb_server.commands.cleanup import cleanup
    from pkdb_server.files.store import FileStore

    now = datetime.now(UTC)
    with session_factory.begin() as session:
        expired = SavedQuery(criteria={}, expires_at=now - timedelta(seconds=1))
        live = SavedQuery(criteria={}, expires_at=now + timedelta(hours=1))
        session.add_all([expired, live])
        session.flush()
        live_id = live.id
    store = FileStore(tmp_path / "files", session_factory, 1_000_000)
    result = cleanup(session_factory, store, now=now)
    assert result["saved_queries"] == 1
    with session_factory() as session:
        assert list(session.scalars(select(SavedQuery.id))) == [live_id]
    assert cleanup(session_factory, store, now=now)["saved_queries"] == 0
