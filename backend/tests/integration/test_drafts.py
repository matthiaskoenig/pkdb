from copy import deepcopy

import pytest

from pkdb.schemas.security import Principal
from pkdb.schemas.validation import StudyValidationError
from pkdb_server.db.read import read_study


def core_and_sections(bundle):
    payload = deepcopy(bundle.study)
    sections = {
        key: payload.pop(key, None)
        for key in (
            "groupset",
            "interventionset",
            "individualset",
            "outputset",
            "dataset",
        )
    }
    payload["files"] = []
    return payload, sections


def test_draft_is_invisible_and_replacement_failure_preserves_publication(
    ingestion_context, valid_bundle, session_factory
):
    from pkdb_server.services.drafts import DraftConflict, DraftService

    ingestion, creator = ingestion_context
    valid_bundle.study["access"] = "private"
    service = DraftService(session_factory, ingestion)
    service.stage_reference(valid_bundle.reference, creator)
    core, sections = core_and_sections(valid_bundle)
    service.begin(core["sid"], creator, core)
    with pytest.raises(LookupError):
        read_study(core["sid"], creator, session_factory)
    with pytest.raises(DraftConflict):
        service.begin(core["sid"], creator, core)
    service.patch(
        core["sid"],
        creator,
        {
            "groupset": sections["groupset"],
            "interventionset": sections["interventionset"],
        },
    )
    with pytest.raises(DraftConflict):
        service.finalize(core["sid"], creator)
    service.patch(core["sid"], creator, {"outputset": sections["outputset"]})
    service.patch(core["sid"], creator, {"dataset": sections["dataset"] or {}})
    result = service.finalize(core["sid"], creator)
    assert result.sid == core["sid"]
    published = read_study(core["sid"], creator, session_factory)
    assert service.finalize(core["sid"], creator).sid == core["sid"]
    service.begin(core["sid"], creator, core)
    sections["outputset"]["outputs"][0]["unit"] = "invalid-unit"
    service.patch(core["sid"], creator, sections)
    with pytest.raises(StudyValidationError):
        service.finalize(core["sid"], creator)
    assert read_study(core["sid"], creator, session_factory) == published


def test_overlapping_finalize_rejects_new_generation(
    ingestion_context, valid_bundle, session_factory, monkeypatch
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from pkdb_server.services.drafts import DraftConflict, DraftService

    ingestion, creator = ingestion_context
    service = DraftService(session_factory, ingestion)
    service.stage_reference(valid_bundle.reference, creator)
    core, sections = core_and_sections(valid_bundle)
    service.begin(core["sid"], creator, core)
    service.patch(core["sid"], creator, sections)
    entered, release = Event(), Event()
    original = ingestion.replace_staged

    def paused(*args):
        entered.set()
        assert release.wait(5)
        return original(*args)

    monkeypatch.setattr(ingestion, "replace_staged", paused)
    with ThreadPoolExecutor(max_workers=2) as pool:
        finalization = pool.submit(service.finalize, core["sid"], creator)
        assert entered.wait(5)
        try:
            with pytest.raises(DraftConflict):
                service.begin(core["sid"], creator, core)
        finally:
            release.set()
        assert finalization.result(timeout=5).sid == core["sid"]
    service.begin(core["sid"], creator, core)
    with pytest.raises(DraftConflict):
        service.finalize(core["sid"], creator)


def test_expired_and_foreign_drafts_cannot_finalize(
    ingestion_context, valid_bundle, session_factory
):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    from pkdb_server.db.models.drafts import StudyDraft
    from pkdb_server.db.models.users import User
    from pkdb_server.services.drafts import DraftConflict, DraftService

    ingestion, creator = ingestion_context
    service = DraftService(session_factory, ingestion)
    service.stage_reference(valid_bundle.reference, creator)
    core, sections = core_and_sections(valid_bundle)
    service.begin(core["sid"], creator, core)
    service.patch(core["sid"], creator, sections)
    with session_factory.begin() as session:
        user = User(username="other-draft-owner", role="curator", active=True)
        session.add(user)
        session.flush()
        other = Principal(user_id=user.id, username=user.username, role=user.role)
    with pytest.raises(LookupError):
        service.finalize(core["sid"], other)
    with session_factory.begin() as session:
        session.execute(
            update(StudyDraft).values(
                expires_at=datetime.now(UTC) - timedelta(seconds=1)
            )
        )
    with pytest.raises(DraftConflict):
        service.finalize(core["sid"], creator)
    with pytest.raises(LookupError):
        read_study(core["sid"], creator, session_factory)


def test_foreign_attachment_handle_cannot_be_used_in_draft(
    ingestion_context, valid_bundle, session_factory
):
    from io import BytesIO

    from pkdb_server.db.models.drafts import LegacyFileHandle
    from pkdb_server.db.models.users import User
    from pkdb_server.services.authorization import AuthorizationDenied
    from pkdb_server.services.drafts import DraftService

    ingestion, creator = ingestion_context
    staged = ingestion.file_store.stage(creator, "owned.txt", BytesIO(b"private bytes"))
    with session_factory.begin() as session:
        alias = LegacyFileHandle(file_id=staged.id)
        user = User(username="foreign-files", role="curator", active=True)
        session.add_all([alias, user])
        session.flush()
        file_id = alias.id
        actor = Principal(user_id=user.id, username=user.username, role=user.role)
    core, sections = core_and_sections(valid_bundle)
    core["creator"] = actor.username
    core["files"] = [file_id]
    service = DraftService(session_factory, ingestion)
    service.stage_reference(valid_bundle.reference, actor)
    service.begin(core["sid"], actor, core)
    service.patch(core["sid"], actor, sections)
    with pytest.raises(AuthorizationDenied):
        service.finalize(core["sid"], actor)
    with pytest.raises(LookupError):
        read_study(core["sid"], actor, session_factory)
