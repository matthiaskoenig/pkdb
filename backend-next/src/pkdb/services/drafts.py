"""Serialize legacy generations and publish only sealed complete bundles."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text

from pkdb.db.models.drafts import LegacyFileHandle, ReferenceDraft, StudyDraft
from pkdb.db.models.files import StoredFile
from pkdb.db.models.studies import Study
from pkdb.files.store import study_access
from pkdb.importers.folder import META_KEYS, SECTIONS
from pkdb.importers.structure import validate_json_tree
from pkdb.schemas.bundle import StagedBundle
from pkdb.schemas.replacement import ReplacementResult
from pkdb.schemas.validation import fail
from pkdb.services.authorization import (
    AuthorizationDenied,
    authorize,
    authorize_creation,
)
from pkdb.services.ingestion import sid_lock


class DraftConflict(ValueError):
    pass


class DraftService:
    def __init__(self, session_factory, ingestion):
        self.session_factory = session_factory
        self.ingestion = ingestion

    def actor(self, session, principal, sid=None):
        current = self.ingestion._principal(session, principal)
        root = session.scalar(select(Study).where(Study.sid == sid)) if sid else None
        if root is None:
            authorize_creation(current)
        else:
            authorize(current, "write", study_access(root, session))
        return current, root

    @staticmethod
    def lock(session, actor, sid):
        acquired = session.scalar(
            text("SELECT pg_try_advisory_xact_lock(:key)"),
            {"key": sid_lock(f"legacy-draft:{actor.user_id}:{sid}")},
        )
        if not acquired:
            raise DraftConflict("Another draft operation is in progress")

    @staticmethod
    def identifier(value):
        if type(value) not in (str, int) or not 0 < len(str(value)) <= 255:
            fail(
                "invalid_sid", "SID must be a nonempty identifier up to 255 characters"
            )
        return str(value)

    def stage_reference(self, payload, principal):
        validate_json_tree(payload, "reference.json")
        if not isinstance(payload, dict):
            fail("invalid_reference", "Reference must be an object")
        sid = self.identifier(payload.get("sid"))
        with self.session_factory.begin() as session:
            actor, _ = self.actor(session, principal)
            self.lock(session, actor, "reference:" + sid)
            row = session.get(ReferenceDraft, (actor.user_id, sid))
            if row is None:
                row = ReferenceDraft(owner_id=actor.user_id, sid=sid)
                session.add(row)
            row.payload = deepcopy(payload)
            row.expires_at = datetime.now(UTC) + timedelta(hours=24)
        return payload

    def read_reference(self, sid, principal):
        with self.session_factory.begin() as session:
            actor, _ = self.actor(session, principal)
            row = self.reference(session, actor, sid)
            return deepcopy(row.payload)

    def reference(self, session, actor, sid):
        self.lock(session, actor, "reference:" + sid)
        row = session.get(ReferenceDraft, (actor.user_id, sid))
        if row is None or row.expires_at <= datetime.now(UTC):
            raise LookupError("Active reference draft unavailable")
        return row

    def patch_reference(self, sid, values, principal):
        validate_json_tree(values, "reference.json")
        if not isinstance(values, dict) or not values:
            fail("invalid_reference", "Expected a nonempty reference patch")
        if "sid" in values and self.identifier(values["sid"]) != sid:
            fail("invalid_sid", "Reference SID cannot be changed")
        with self.session_factory.begin() as session:
            actor, _ = self.actor(session, principal)
            row = self.reference(session, actor, sid)
            row.payload = {**row.payload, **deepcopy(values)}
            return deepcopy(row.payload)

    def read(self, sid, principal):
        with self.session_factory.begin() as session:
            actor, _ = self.actor(session, principal, sid)
            draft = self.active(session, actor, sid)
            return {**deepcopy(draft.payload), "generation": str(draft.id)}

    def begin(self, sid, principal, core):
        validate_json_tree(core, "study.json")
        sid = self.identifier(sid)
        if (
            not isinstance(core, dict)
            or str(core.get("sid")) != sid
            or set(core) - META_KEYS - {"sid", "reference", "files"}
        ):
            fail("invalid_core", "Expected only study core metadata")
        aliases = core.get("files", [])
        if (
            not isinstance(aliases, list)
            or any(type(value) is not int or value <= 0 for value in aliases)
            or len(aliases) > self.ingestion.settings.upload_max_files
            or len(aliases) != len(set(aliases))
        ):
            fail(
                "invalid_handles",
                "Expected a bounded list of unique integer attachment handles",
            )
        with self.session_factory.begin() as session:
            actor, _ = self.actor(session, principal, sid)
            self.lock(session, actor, sid)
            old = session.scalar(
                select(StudyDraft)
                .where(StudyDraft.owner_id == actor.user_id, StudyDraft.sid == sid)
                .with_for_update()
            )
            if old is not None:
                if old.expires_at > datetime.now(UTC):
                    raise DraftConflict("An active draft already exists")
                session.delete(old)
                session.flush()
            reference_sid = self.identifier(core.get("reference"))
            reference = session.get(ReferenceDraft, (actor.user_id, reference_sid))
            if reference is None or reference.expires_at <= datetime.now(UTC):
                fail(
                    "missing_reference", "Stage the reference before beginning a study"
                )
            draft = StudyDraft(
                owner_id=actor.user_id,
                sid=sid,
                payload=deepcopy(core),
                reference=deepcopy(reference.payload),
                sealed=False,
                expires_at=datetime.now(UTC) + timedelta(hours=24),
            )
            session.add(draft)
            session.flush()
            return {**draft.payload, "generation": str(draft.id)}

    def active(self, session, actor, sid):
        self.lock(session, actor, sid)
        draft = session.scalar(
            select(StudyDraft)
            .where(StudyDraft.owner_id == actor.user_id, StudyDraft.sid == sid)
            .with_for_update()
        )
        if draft is None or draft.expires_at <= datetime.now(UTC):
            raise LookupError("Active draft unavailable")
        return draft

    def patch(self, sid, principal, values):
        validate_json_tree(values, "study.json")
        if (
            not isinstance(values, dict)
            or not values
            or set(values) - SECTIONS.keys() - META_KEYS
        ):
            fail("invalid_patch", "Unknown or empty draft patch")
        with self.session_factory.begin() as session:
            actor, _ = self.actor(session, principal, sid)
            draft = self.active(session, actor, sid)
            draft.payload = {**draft.payload, **deepcopy(values)}
            # The original uploader sends dataset last, including {} when absent.
            draft.sealed = (
                "dataset" in values
                and {"groupset", "interventionset"} <= draft.payload.keys()
            )
            return {**draft.payload, "generation": str(draft.id)}

    def finalize(self, sid, principal):
        with self.session_factory.begin() as session:
            actor = self.ingestion._principal(session, principal)
            self.lock(session, actor, sid)
            actor, root = self.actor(session, principal, sid)
            draft = session.scalar(
                select(StudyDraft)
                .where(StudyDraft.owner_id == actor.user_id, StudyDraft.sid == sid)
                .with_for_update()
            )
            if draft is None:
                if root is None:
                    raise LookupError("Study and draft unavailable")
                return ReplacementResult(
                    sid=sid, created=False, digest=root.source_digest, counts={}
                )
            if draft.expires_at <= datetime.now(UTC) or not draft.sealed:
                raise DraftConflict("Draft is expired or incomplete")
            study = deepcopy(draft.payload)
            aliases = study.pop("files", [])
            if not isinstance(aliases, list) or any(
                type(alias) is not int for alias in aliases
            ):
                fail("invalid_handles", "Legacy files must be integer handle IDs")
            handles = (
                list(
                    session.execute(
                        select(LegacyFileHandle.id, StoredFile)
                        .join(StoredFile, StoredFile.id == LegacyFileHandle.file_id)
                        .where(LegacyFileHandle.id.in_(aliases))
                    )
                )
                if aliases
                else []
            )
            if len(handles) != len(aliases) or any(
                row.owner_id != actor.user_id for _, row in handles
            ):
                raise AuthorizationDenied("Attachment handle unavailable")
            names = {str(alias): row.original_name for alias, row in handles}

            def restore(value):
                if isinstance(value, list):
                    return [restore(item) for item in value]
                if isinstance(value, dict):
                    return {
                        key: "||".join(
                            names.get(item.strip(), item.strip())
                            for item in str(item_value).split("||")
                        )
                        if key in {"source", "figure", "image"}
                        and isinstance(item_value, (str, int))
                        else restore(item_value)
                        for key, item_value in value.items()
                    }
                return value

            bundle = StagedBundle(
                study=restore(study),
                reference=draft.reference,
                handles=[row.id for _, row in handles],
            )
            result = self.ingestion.replace_staged(bundle, actor)
            session.delete(draft)
            return result

    def delete(self, sid, principal):
        with self.session_factory.begin() as session:
            actor = self.ingestion._principal(session, principal)
            self.lock(session, actor, sid)
            session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": sid_lock(sid)}
            )
            actor, root = self.actor(session, principal, sid)
            draft = session.scalar(
                select(StudyDraft)
                .where(StudyDraft.owner_id == actor.user_id, StudyDraft.sid == sid)
                .with_for_update()
            )
            if root is None and draft is None:
                raise LookupError("Study unavailable")
            if root is not None:
                authorize(actor, "delete", study_access(root, session))
                session.delete(root)
            if draft is not None:
                session.delete(draft)
