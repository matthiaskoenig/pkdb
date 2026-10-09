"""Prepare outside transactions, then publish under study and vocabulary locks."""

import hashlib
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn

from sqlalchemy import func, or_, select, text, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from pkdb.domain.provenance import comment_authors
from pkdb.domain.validation import PROCESSING_VERSION, prepare_study
from pkdb.domain.vocabulary import vocabulary_hash
from pkdb.importers.folder import parse_bundle
from pkdb.references import ReferenceError, normalize_doi, normalize_pmid
from pkdb.schemas.prepared import PreparedStudy
from pkdb.schemas.replacement import ReplacementResult
from pkdb.schemas.security import Principal
from pkdb.schemas.source import SourceBundle, SourceLocation
from pkdb.schemas.study import CanonicalStudy
from pkdb.schemas.validation import fail
from pkdb.studyformat.tables import REFERENCE_JSON, STUDY_JSON
from pkdb.studyformat.validation import prepare_folder
from pkdb_server.config import Settings
from pkdb_server.db import replace
from pkdb_server.db.bootstrap import VOCABULARY_LOCK, load_vocabulary
from pkdb_server.db.models.files import StoredFile, StudyAttachment
from pkdb_server.db.models.studies import PublicationIdentifier, Study, StudyGrant
from pkdb_server.db.models.users import User
from pkdb_server.db.models.vocabulary import VocabularyVersion
from pkdb_server.db.publications import identifiers
from pkdb_server.files.store import FileStore, StagedFile, study_access
from pkdb_server.services.authorization import (
    Action,
    AuthorizationDenied,
    authorize,
    authorize_creation,
)


class PublicationConflict(ValueError):
    pass


class StudyChanged(Exception):
    """A study changed between reading its names and locking them; start again."""


# How often a transaction starts again when the study changes before its locks.
LOCK_ATTEMPTS = 3


def sid_lock(sid: str) -> int:
    return int.from_bytes(hashlib.sha256(sid.encode()).digest()[:8], "big", signed=True)


def issue_lock(issue: int) -> str:
    """The lock name of a GitHub issue number, which is no study identifier."""
    return f"issue #{issue}"


def lock_publication(
    session: Session,
    sid: str,
    pkdb_id: str | None,
    former: Iterable[str] = (),
    issue: int | None = None,
) -> set[str]:
    """Take the advisory locks of a publication of `sid` released as `pkdb_id`.

    A release locks its PKDB identifier too, so a study format 1 upload under
    that sid and a rename of the released study serialize. A publication that
    takes over other studies locks their sids (`former`) as well. A publication
    with an issue number locks the number, so publications that set the same
    number serialize and the later one finds the study of the earlier one. The
    locks are taken in sorted order, which avoids deadlocks. Returns the
    locked names.
    """
    names = {name for name in (sid, pkdb_id, *former) if name}
    if issue is not None:
        names.add(issue_lock(issue))
    for key in sorted(sid_lock(name) for name in names):
        session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
    return names


def is_located(sid: str) -> bool:
    """Whether `sid` is a study format 2 sid `<substance>/<name>`."""
    return "/" in sid


# The condition of is_located on stored studies.
LOCATED = func.strpos(Study.sid, "/") > 0


def publication_studies(
    session: Session, study: CanonicalStudy, *, lock: bool = False
) -> list[Study]:
    """The stored studies of the publication and source of `study`."""
    keys = identifiers(study.reference)
    publications = select(PublicationIdentifier.publication_id).where(
        tuple_(PublicationIdentifier.namespace, PublicationIdentifier.value).in_(keys)
    )
    statement = (
        select(Study)
        .where(
            Study.publication_id.in_(publications),
            Study.source_key == study.metadata.provenance.source_key,
        )
        .order_by(Study.sid)
    )
    return list(session.scalars(statement.with_for_update() if lock else statement))


def former_sids(session: Session, study: CanonicalStudy) -> set[str]:
    """The sids of the stored studies that `study` may take over.

    They are read before the publication locks them; stored_study checks the
    locked row again. A release may take over the study format 1 study of its
    PKDB identifier, and a study format 2 study the only study format 1 study
    of its publication and source or the study format 2 study with its issue
    number. A study format 2 study of the PKDB identifier is locked by the
    identifier.
    """
    names = set()
    release = study.metadata.release
    if release is not None:
        names.update(
            session.scalars(
                select(Study.sid).where(
                    or_(
                        Study.sid == release.pkdb_id,
                        Study.pkdb_id == release.pkdb_id,
                        Study.legacy_sid == release.pkdb_id,
                    )
                )
            )
        )
    if is_located(study.sid):
        same = publication_studies(session, study)
        if len(same) == 1:
            names.add(same[0].sid)
    former = {name for name in names if not is_located(name)}
    issue = study.metadata.issue
    if is_located(study.sid) and issue is not None:
        former.update(
            session.scalars(select(Study.sid).where(Study.issue == issue, LOCATED))
        )
    return former


def stored_study(
    session: Session,
    study: CanonicalStudy,
    principal: Principal,
    *,
    lock: bool = False,
    locked: set[str] | None = None,
) -> Study | None:
    """The stored study that an upload replaces, or None for a new study.

    That is the study with the same sid. A released study not yet stored under
    its sid takes over the study stored under its PKDB identifier, as sid
    (study format 1), as `pkdb_id` (a renamed folder) or as `legacy_sid`; the
    caller renames it. Otherwise a study format 2 study not yet stored under its
    sid takes over the study format 2 study with its issue number (a moved
    folder), else the study format 1 study of the same publication and source,
    when the principal may edit it; a takeover by issue number never changes a
    stored PKDB identifier. A PKDB identifier and an issue number name at most
    one study each. Refusals name other studies only when the principal
    may read them. With `locked`, the names that the caller locked,
    StudyChanged when a study taken over by issue number or a taken over study
    format 1 study is not among them.
    """

    def rows(*conditions):
        statement = select(Study).where(*conditions).order_by(Study.sid)
        return session.scalars(statement.with_for_update() if lock else statement).all()

    def allowed(action: Action, row: Study) -> bool:
        try:
            authorize(principal, action, study_access(row, session))
        except AuthorizationDenied:
            return False
        return True

    def readable(row: Study) -> bool:
        return allowed("read", row)

    def refuse(code: str, message: str, field: str) -> NoReturn:
        fail(
            code,
            message,
            SourceLocation(file=STUDY_JSON, path=tuple(field.split("."))),
            field=field,
        )

    release = study.metadata.release
    pkdb_id = release.pkdb_id if release is not None else None
    root = next(iter(rows(Study.sid == study.sid)), None)
    released = None
    if root is None and pkdb_id is not None:
        claimed = rows(
            or_(
                Study.sid == pkdb_id,
                Study.pkdb_id == pkdb_id,
                Study.legacy_sid == pkdb_id,
            )
        )
        if len(claimed) > 1:
            named = (
                f" ({', '.join(row.sid for row in claimed)})"
                if all(readable(row) for row in claimed)
                else ""
            )
            refuse(
                "duplicate_pkdb_id",
                f"{pkdb_id} identifies more than one stored study{named}; "
                "an administrator must remove one of them",
                "release.pkdb_id",
            )
        root = released = next(iter(claimed), None)
    issue = study.metadata.issue
    issued = None
    if root is None and issue is not None and is_located(study.sid):
        # A moved folder takes over the study with its issue number.
        match = next(iter(rows(Study.issue == issue, LOCATED)), None)
        if match is not None:
            if not allowed("write", match):
                raise PublicationConflict(
                    f"The study {match.sid} has issue #{issue}; uploading it as "
                    f"{study.sid} needs edit rights on {match.sid}"
                    if readable(match)
                    else "A study already has this issue"
                )
            if match.pkdb_id is not None:
                # A released study keeps its PKDB identifier, which the
                # lookup above would have found.
                raise PublicationConflict(
                    f"The study {match.sid} has issue #{issue} and is released "
                    f"as {match.pkdb_id}; upload it with that release"
                    if readable(match)
                    else "A study already has this issue"
                )
            root = issued = match
    if is_located(study.sid) and root is released:
        same = publication_studies(session, study, lock=lock)
        if len(same) == 1 and same[0] is not root:
            [match] = same
            if root is not None:
                raise PublicationConflict(
                    f"{pkdb_id} identifies the study {root.sid}, but the study "
                    f"{match.sid} has the same publication and source"
                    if readable(root) and readable(match)
                    else f"{pkdb_id} and the publication identify different studies"
                )
            if not is_located(match.sid):
                if not allowed("write", match):
                    raise PublicationConflict(
                        f"The study {match.sid} already exists for this publication "
                        f"and source; uploading it as {study.sid} needs edit rights "
                        f"on {match.sid}"
                        if readable(match)
                        else "A study already exists for this publication and source"
                    )
                root = match
    if (
        locked is not None
        and root is not None
        and root.sid not in locked
        and (root is issued or not is_located(root.sid))
    ):
        raise StudyChanged
    others = [] if root is None else [Study.id != root.id]
    if pkdb_id is not None:
        other = session.scalar(
            select(Study).where(
                or_(
                    Study.sid == pkdb_id,
                    Study.pkdb_id == pkdb_id,
                    Study.legacy_sid == pkdb_id,
                ),
                *others,
            )
        )
        if other is not None:
            refuse(
                "duplicate_pkdb_id",
                (
                    f"{pkdb_id} already identifies the study {other.sid}"
                    if readable(other)
                    else f"Another study already uses {pkdb_id}"
                )
                + "; each release has its own PKDB identifier",
                "release.pkdb_id",
            )
    if issue is not None:
        other = session.scalar(select(Study).where(Study.issue == issue, *others))
        if other is not None:
            refuse(
                "duplicate_issue",
                f"Issue #{issue} belongs to the study {other.sid}"
                if readable(other)
                else f"Issue #{issue} belongs to another study",
                "issue",
            )
    renamed = session.scalar(select(Study).where(Study.pkdb_id == study.sid, *others))
    if renamed is not None:
        refuse(
            "duplicate_pkdb_id",
            f"{study.sid} is now the study {renamed.sid}; upload its study format 2 folder"
            if readable(renamed)
            else f"Another study already uses {study.sid} as its PKDB identifier",
            "sid",
        )
    moved = session.scalar(select(Study).where(Study.legacy_sid == study.sid, *others))
    if moved is not None:
        raise PublicationConflict(
            f"{study.sid} is now the study {moved.sid}; upload its study format 2 folder"
            if readable(moved)
            else f"Another study was stored as {study.sid}"
        )
    return root


def check_publication_identifiers(study: CanonicalStudy) -> None:
    """Refuse PubMed IDs and DOIs that have no normalized form.

    Publications are matched by normalized identifiers. Study format 2 refuses
    such identifiers while loading; this also covers study format 1.
    """
    for field, normalizer in (("pmid", normalize_pmid), ("doi", normalize_doi)):
        value = getattr(study.reference, field)
        if value:
            try:
                normalizer(value)
            except ReferenceError as error:
                fail(
                    "invalid_publication_identifier",
                    f"{field} {value!r}: {error}",
                    SourceLocation(file=REFERENCE_JSON, path=(field,)),
                    field=field,
                )


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
        self,
        session: Session,
        principal: Principal,
        *,
        lock=False,
        publication_lock=False,
    ) -> Principal:
        from pkdb_server.services.authentication import revalidate_principal

        return revalidate_principal(
            principal, session, lock=lock, publication_lock=publication_lock
        )

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

    def validate(
        self, source: SourceBundle | Path, principal: Principal
    ) -> PreparedStudy:
        """Prepare a bundle or a study format 2 folder that the principal may write.

        A study format 2 folder is prepared as the client prepares it, with
        every validation layer. All its files except study.json and
        reference.json must be files of the study.
        """
        if isinstance(source, Path):
            with self.session_factory() as session:
                vocabulary = load_vocabulary(session)
            prepared = prepare_folder(
                source,
                vocabulary,
                max_rows=self.settings.upload_max_rows,
                max_files=self.settings.upload_max_files,
            )
            study = prepared.study
            # Files that the layout ignores, such as the generated workbook.
            unexpected = {path.name for path in source.iterdir()} - {
                STUDY_JSON,
                REFERENCE_JSON,
                *(item.name for item in study.attachments),
            }
            if unexpected:
                name = min(unexpected)
                fail(
                    "invalid_filename",
                    f"{name} is not a file of the study; send the files that "
                    "pkdb validate reads",
                    SourceLocation(file=name),
                )
        else:
            if len(source.files) > self.settings.upload_max_files:
                fail("file_limit", "Too many source files")
            study = parse_bundle(source, max_rows=self.settings.upload_max_rows)
            prepared = None
        check_publication_identifiers(study)
        with self.session_factory() as session:
            current = self._principal(session, principal)
            root = stored_study(session, study, current)
            if root is None:
                authorize_creation(current)
            else:
                authorize(current, "write", study_access(root, session))
            if prepared is None:
                prepared = prepare_study(study, load_vocabulary(session))
        return prepared

    def replace(
        self,
        source: SourceBundle | Path,
        principal: Principal,
        *,
        expected_vocabulary_hash: str | None = None,
        expected_processing_version: str | None = None,
        timings: dict[str, float] | None = None,
    ) -> ReplacementResult:
        timings = timings if timings is not None else {}
        started = time.monotonic()
        self.check_compatibility(expected_vocabulary_hash, expected_processing_version)
        prepared = self.validate(source, principal)
        timings["validation"] = time.monotonic() - started
        started = time.monotonic()
        staged = []
        expected = {
            attachment.name: attachment for attachment in prepared.study.attachments
        }
        files = (
            source.files
            if isinstance(source, SourceBundle)
            else {name: source / name for name in expected}
        )
        for name, path in files.items():
            with path.open("rb") as stream:
                file = self.file_store.stage(principal, name, stream)
            attachment = expected[name]
            if file.digest != attachment.sha256 or file.size != attachment.size:
                fail("source_changed", "Source file changed after validation")
            staged.append(file)
        timings["staging"] = time.monotonic() - started
        started = time.monotonic()
        result = self._publish(
            prepared,
            principal,
            staged,
            expected_vocabulary_hash=expected_vocabulary_hash,
            expected_processing_version=expected_processing_version,
        )
        timings["publication"] = time.monotonic() - started
        return result

    def _publish(
        self,
        prepared: PreparedStudy,
        principal: Principal,
        staged: list[StagedFile],
        *,
        expected_vocabulary_hash: str | None = None,
        expected_processing_version: str | None = None,
    ) -> ReplacementResult:
        for _ in range(LOCK_ATTEMPTS):
            try:
                return self._publish_once(
                    prepared,
                    principal,
                    staged,
                    expected_vocabulary_hash=expected_vocabulary_hash,
                    expected_processing_version=expected_processing_version,
                )
            except StudyChanged:
                continue
        raise PublicationConflict("The study changed during the upload; upload again")

    def _publish_once(
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
                release = study.metadata.release
                pkdb_id = release.pkdb_id if release else None
                locked = lock_publication(
                    session,
                    study.sid,
                    pkdb_id,
                    former_sids(session, study),
                    issue=study.metadata.issue,
                )
                self.check_compatibility(
                    expected_vocabulary_hash,
                    expected_processing_version,
                    session=session,
                )
                current = self._principal(
                    session,
                    principal,
                    lock=principal.credential_kind == "session",
                    publication_lock=principal.credential_kind != "session",
                )
                can_manage = self._can_manage(current, session)
                version = session.get(VocabularyVersion, 1)
                if version is None or version.version != prepared.vocabulary_version:
                    raise PublicationConflict("vocabulary_changed")
                root = stored_study(session, study, current, lock=True, locked=locked)
                created = root is None
                renamed_from = None
                if root is None:
                    authorize_creation(current)
                    root = Study(
                        sid=study.sid,
                        name=study.metadata.name,
                        access=study.metadata.access,
                        licence=study.metadata.licence,
                    )
                    session.add(root)
                else:
                    authorize(current, "write", study_access(root, session))
                    if not can_manage and root.licence != study.metadata.licence:
                        raise AuthorizationDenied(
                            "Only administrators change licence",
                            code="licence_change_forbidden",
                        )
                    if root.sid != study.sid:
                        # Rename on re-upload: the study keeps its row and data.
                        renamed_from, root.sid = root.sid, study.sid
                        if not is_located(renamed_from) and renamed_from != pkdb_id:
                            # Its study format 1 sid keeps redirecting to it.
                            root.legacy_sid = renamed_from
                        session.flush()
                from pkdb_server.db.publications import assign_publication

                assign_publication(session, root, study)
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
                if not created and not can_manage and creator_id != root.creator_id:
                    raise AuthorizationDenied(
                        "Only administrators transfer study ownership",
                        code="creator_change_forbidden",
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
                renamed_from=renamed_from,
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
