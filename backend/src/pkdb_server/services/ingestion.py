"""Prepare outside transactions, then publish under study and vocabulary locks."""

import hashlib
from datetime import UTC, datetime

from pkdb.domain.provenance import comment_authors
from pkdb.domain.validation import PROCESSING_VERSION, prepare_study
from pkdb.domain.vocabulary import vocabulary_hash
from pkdb.importers.folder import parse_bundle
from pkdb.schemas.prepared import PreparedStudy
from pkdb.schemas.replacement import ReplacementResult
from pkdb.schemas.security import Principal
from pkdb.schemas.source import SourceBundle
from pkdb.schemas.validation import fail
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from pkdb_server.config import Settings
from pkdb_server.db import replace
from pkdb_server.db.bootstrap import VOCABULARY_LOCK, load_vocabulary
from pkdb_server.db.models.files import StoredFile, StudyAttachment
from pkdb_server.db.models.studies import Study, StudyGrant
from pkdb_server.db.models.users import User
from pkdb_server.db.models.vocabulary import VocabularyVersion
from pkdb_server.files.store import FileStore, StagedFile, study_access
from pkdb_server.services.authorization import (
    AuthorizationDenied,
    authorize,
    authorize_creation,
)


class PublicationConflict(ValueError):
    pass


def sid_lock(sid: str) -> int:
    return int.from_bytes(hashlib.sha256(sid.encode()).digest()[:8], "big", signed=True)


class IngestionService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        file_store: FileStore,
        settings: Settings,
    ):
        self.session_factory = session_factory
        self.file_store = file_store
        self.settings = settings

    @staticmethod
    def _can_manage(principal, session):
        if principal.role != "admin":
            return False
        if principal.credential_kind == "internal":
            return True
        if principal.credential_kind != "session":
            return False
        from pkdb_server.services.credentials import require_admin_session

        require_admin_session(principal, session)
        return True

    def _principal(
        self, session: Session, principal: Principal, *, lock=False
    ) -> Principal:
        from pkdb_server.services.authentication import revalidate_principal

        return revalidate_principal(principal, session, lock=lock)

    def check_compatibility(
        self,
        expected_vocabulary_hash: str | None = None,
        expected_processing_version: str | None = None,
        *,
        session=None,
    ) -> None:
        if (
            expected_processing_version is not None
            and expected_processing_version != PROCESSING_VERSION
        ):
            raise PublicationConflict("processing_version_mismatch")
        if expected_vocabulary_hash is not None:
            if session is None:
                with self.session_factory() as current_session:
                    self.check_compatibility(
                        expected_vocabulary_hash, session=current_session
                    )
                return
            if vocabulary_hash(load_vocabulary(session)) != expected_vocabulary_hash:
                raise PublicationConflict("vocabulary_mismatch")

    def validate(self, bundle: SourceBundle, principal: Principal) -> PreparedStudy:
        if len(bundle.files) > self.settings.upload_max_files:
            fail("file_limit", "Too many source files")
        study = parse_bundle(bundle, max_rows=self.settings.upload_max_rows)
        with self.session_factory() as session:
            current = self._principal(session, principal)
            root = session.scalar(select(Study).where(Study.sid == study.sid))
            if root is None:
                authorize_creation(current)
                if (
                    not self._can_manage(current, session)
                    and study.metadata.access != "private"
                ):
                    fail(
                        "private_creation_required",
                        "New studies must be private until an administrator publishes them",
                    )
            else:
                authorize(current, "write", study_access(root, session))
            vocabulary = load_vocabulary(session)
        return prepare_study(study, vocabulary)

    def replace(
        self,
        bundle: SourceBundle,
        principal: Principal,
        *,
        expected_vocabulary_hash: str | None = None,
        expected_processing_version: str | None = None,
    ) -> ReplacementResult:
        self.check_compatibility(expected_vocabulary_hash, expected_processing_version)
        prepared = self.validate(bundle, principal)
        staged = []
        expected = {
            attachment.name: attachment for attachment in prepared.study.attachments
        }
        for name, path in bundle.files.items():
            with path.open("rb") as source:
                file = self.file_store.stage(principal, name, source)
            attachment = expected[name]
            if file.digest != attachment.sha256 or file.size != attachment.size:
                fail("source_changed", "Source file changed after validation")
            staged.append(file)
        return self._publish(
            prepared,
            principal,
            staged,
            expected_vocabulary_hash=expected_vocabulary_hash,
            expected_processing_version=expected_processing_version,
        )

    def replace_staged(self, bundle, principal: Principal) -> ReplacementResult:
        from pkdb_server.services.bundles import materialize_bundle

        with materialize_bundle(
            bundle, principal, self.file_store, self.settings
        ) as source:
            prepared = self.validate(source, principal)
        with self.session_factory() as session:
            rows = list(
                session.scalars(
                    select(StoredFile).where(StoredFile.id.in_(bundle.handles))
                )
            )
            if len(rows) != len(bundle.handles):
                raise PublicationConflict("staged_file_unavailable")
            staged = [StagedFile.model_validate(row) for row in rows]
        expected = {
            attachment.name: attachment for attachment in prepared.study.attachments
        }
        for file in staged:
            attachment = expected.get(file.original_name)
            if attachment is None or (attachment.sha256, attachment.size) != (
                file.digest,
                file.size,
            ):
                fail("source_changed", "Staged attachment changed after validation")
        return self._publish(prepared, principal, staged)

    def _publish(
        self,
        prepared: PreparedStudy,
        principal: Principal,
        staged: list[StagedFile],
        *,
        expected_vocabulary_hash: str | None = None,
        expected_processing_version: str | None = None,
    ) -> ReplacementResult:
        study = prepared.study
        try:
            with self.session_factory.begin() as session:
                session.execute(
                    text("SELECT pg_advisory_xact_lock_shared(:key)"),
                    {"key": VOCABULARY_LOCK},
                )
                session.execute(
                    text("SELECT pg_advisory_xact_lock(:key)"),
                    {"key": sid_lock(study.sid)},
                )
                self.check_compatibility(
                    expected_vocabulary_hash,
                    expected_processing_version,
                    session=session,
                )
                current = self._principal(session, principal, lock=True)
                can_manage = self._can_manage(current, session)
                version = session.get(VocabularyVersion, 1)
                if version is None or version.version != prepared.vocabulary_version:
                    raise PublicationConflict("vocabulary_changed")
                root = session.scalar(
                    select(Study).where(Study.sid == study.sid).with_for_update()
                )
                created = root is None
                if root is None:
                    authorize_creation(current)
                    if not can_manage and study.metadata.access != "private":
                        fail(
                            "private_creation_required",
                            "New studies must be private until an administrator publishes them",
                        )
                    root = Study(
                        sid=study.sid,
                        name=study.metadata.name,
                        access=study.metadata.access,
                        licence=study.metadata.licence,
                    )
                    session.add(root)
                else:
                    authorize(current, "write", study_access(root, session))
                    if not can_manage and (
                        root.access != study.metadata.access
                        or root.licence != study.metadata.licence
                    ):
                        raise AuthorizationDenied(
                            "Only administrators change visibility or licence"
                        )
                names = {
                    study.metadata.creator,
                    *study.metadata.collaborators,
                    *(curator.user for curator in study.metadata.curators),
                    *comment_authors(study),
                }
                users = {
                    user.username: user
                    for user in session.scalars(
                        select(User)
                        .where(User.username.in_(names))
                        .order_by(User.id)
                        .with_for_update(read=True)
                    )
                }
                if names - users.keys():
                    fail("unknown_user", "Study refers to an unknown user")
                creator_id = users[study.metadata.creator].id
                if not can_manage and creator_id != (
                    current.user_id if created else root.creator_id
                ):
                    raise AuthorizationDenied(
                        "Only administrators transfer study ownership"
                    )
                root.creator_id = creator_id
                root.name = study.metadata.name
                root.date = study.metadata.date
                root.access = study.metadata.access
                root.licence = study.metadata.licence
                root.source_digest = study.source_digest
                root.processing_version = prepared.processing_version
                root.vocabulary_version = prepared.vocabulary_version
                root.validation_report = prepared.report.model_dump(mode="json")
                root.source_manifest = {"sections": list(study.section_notes)}
                session.flush()
                locked_files = []
                for file in sorted(staged, key=lambda item: item.id):
                    row = session.scalar(
                        select(StoredFile)
                        .where(StoredFile.id == file.id)
                        .with_for_update()
                    )
                    if (
                        row is None
                        or not row.ready
                        or row.owner_id != current.user_id
                        or row.expires_at < datetime.now(UTC)
                    ):
                        raise PublicationConflict("staged_file_unavailable")
                    self.file_store.verify(file)
                    locked_files.append(row)
                replace.clear_children(session, root.id)
                replace.insert_graph(session, root, study)
                if created:
                    # Source contributor metadata never grants access implicitly.
                    session.add(
                        StudyGrant(
                            study_id=root.id, user_id=current.user_id, role="curator"
                        )
                    )
                    if can_manage:
                        grants = {(current.user_id, "curator")}
                        grants.update(
                            (users[c.user].id, "curator")
                            for c in study.metadata.curators
                        )
                        grants.update(
                            (users[name].id, "collaborator")
                            for name in study.metadata.collaborators
                        )
                        for user_id, role in sorted(
                            grants - {(current.user_id, "curator")}
                        ):
                            session.add(
                                StudyGrant(study_id=root.id, user_id=user_id, role=role)
                            )
                session.add_all(
                    StudyAttachment(
                        study_id=root.id, file_id=row.id, name=row.original_name
                    )
                    for row in locked_files
                )
                session.flush()
            return ReplacementResult(
                sid=study.sid,
                created=created,
                digest=study.source_digest,
                counts={
                    name: len(getattr(study, name))
                    for name in (
                        "groups",
                        "individuals",
                        "interventions",
                        "measurements",
                        "timecourses",
                        "attachments",
                    )
                },
                warnings=prepared.report.issues,
            )
        except (IntegrityError, replace.ReferenceConflict) as error:
            raise PublicationConflict(
                "Study conflicts with existing reference data"
            ) from error
