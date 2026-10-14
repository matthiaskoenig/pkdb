"""The study pages of the website: built at upload, stored, served by audience (#963).

The documents come from `pkdb.studyformat.views`, the builder of the local curation app, so the
website shows a study as `pkdb curate` does.
"""

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from pkdb.issues.github import DEFAULT_REPOSITORY
from pkdb.schemas.security import Principal, StudyAccess
from pkdb.studyformat.load import load_study
from pkdb.studyformat.substances import folder_index, folder_substances
from pkdb.studyformat.tables import REFERENCE_JSON, STUDY_JSON
from pkdb.studyformat.views import (
    FILE_TYPES,
    VIEW_VERSION,
    Audience,
    for_audience,
    people,
    row_view,
    source_document,
    study_view,
    table_view,
)
from pkdb_server.db.models.files import StoredFile, StudyAttachment
from pkdb_server.db.models.studies import Study, StudyGrant
from pkdb_server.db.models.users import User
from pkdb_server.db.models.views import StudyView
from pkdb_server.db.queries import visibility
from pkdb_server.files.store import FileStore, study_access
from pkdb_server.services.authorization import AuthorizationDenied, authorize, may_write
from pkdb_server.services.profiles import FALLBACK_URL, public_profile


@dataclass(frozen=True)
class BuiltViews:
    """The documents of a study folder and the texts of its two JSON files."""

    study_json: str
    reference_json: str
    documents: tuple[tuple[str, str, dict], ...]


def _plain(document: dict) -> dict:
    # As the database gives it back: lists for tuples.
    return json.loads(json.dumps(document))


def build_views(
    folder: Path, *, warnings: int, max_rows: int | None, max_files: int | None
) -> BuiltViews:
    """The documents of a validated study folder at `<substance>/<name>`."""
    study = load_study(folder, max_rows=max_rows, max_files=max_files)
    view = study_view(folder, study)
    documents: list[tuple[str, str, dict]] = [
        ("study", "", view),
        ("row", "", row_view(view, warnings=warnings)),
    ]
    for entry in view["tables"]:
        if (table := table_view(study, entry["file"])) is not None:
            documents.append(("table", entry["file"], table))
    for source in view["sources"]:
        if (document := source_document(study, source["source"])) is not None:
            documents.append(("source", source["source"], document))
    return BuiltViews(
        study_json=(folder / STUDY_JSON).read_text(encoding="utf-8"),
        reference_json=(folder / REFERENCE_JSON).read_text(encoding="utf-8"),
        documents=tuple((kind, key, _plain(doc)) for kind, key, doc in documents),
    )


def store_views(session: Session, study_id: int, views: BuiltViews) -> None:
    """Add the documents of `views`; the caller removed the old ones (`clear_children`)."""
    session.add_all(
        StudyView(
            study_id=study_id,
            kind=kind,
            key=key,
            version=VIEW_VERSION,
            document=document,
        )
        for kind, key, document in views.documents
    )


def view_url(sid: str, *parts: str) -> str:
    """The URL of the study page of `sid`, or of a part of it."""
    return "/".join(
        ["/api/v2/studies", *(quote(s, safe="") for s in sid.split("/")), "view"]
        + [quote(part, safe="") for part in parts]
    )


def issue_state(number: int | None) -> dict | None:
    """The issue of a study as the curation app shows it, without asking GitHub."""
    if number is None:
        return None
    return {
        "number": number,
        "state": None,
        "labels": [],
        "assignees": [],
        "url": f"https://github.com/{DEFAULT_REPOSITORY}/issues/{number}",
    }


def _profiles(session, usernames) -> dict[str, dict]:
    users = session.scalars(select(User).where(User.username.in_(set(usernames))))
    found = {user.username: public_profile(user) for user in users}
    return {
        name: found.get(name)
        or {
            "username": name,
            "display_name": name,
            "title": None,
            "affiliation": None,
            "avatar_url": FALLBACK_URL,
        }
        for name in usernames
    }


class StudyViews:
    """Reads the stored study pages for a principal; LookupError for anything it may not read."""

    def __init__(self, session_factory: sessionmaker, file_store: FileStore):
        self.session_factory = session_factory
        self.file_store = file_store

    def _open(self, session, sid: str, principal: Principal):
        root = session.scalar(select(Study).where(Study.sid == sid))
        if root is None or root.creator_id is None:
            raise LookupError(sid)
        access = study_access(root, session)
        try:
            authorize(principal, "read", access)
        except AuthorizationDenied:
            raise LookupError(sid) from None
        audience: Audience = "curator" if may_write(principal, access) else "public"
        return root, audience

    def _document(self, session, study_id: int, kind: str, key: str) -> dict:
        document = session.scalar(
            select(StudyView.document).where(
                StudyView.study_id == study_id,
                StudyView.kind == kind,
                StudyView.key == key,
            )
        )
        if document is None:
            raise LookupError(key)
        return document

    def study(self, sid: str, principal: Principal) -> dict:
        with self.session_factory() as session:
            root, audience = self._open(session, sid, principal)
            stored = self._document(session, root.id, "study", "")
            # An administrator changes access and licence without an upload, which builds
            # the page: the database has them.
            metadata = {
                **stored["metadata"],
                "access": root.access,
                "licence": root.licence,
            }
            page = for_audience("study", {**stored, "metadata": metadata}, audience)
            if page is None:
                raise LookupError(sid)
            curator = audience == "curator"
            names = {
                name
                for name in (
                    page["metadata"].get("creator"),
                    *(c["user"] for c in page["metadata"].get("curators", [])),
                    *page["metadata"].get("collaborators", []),
                )
                if name
            }
            profiles = _profiles(session, names)
            files = (
                {
                    attachment.name: file
                    for attachment, file in session.execute(
                        select(StudyAttachment, StoredFile)
                        .join(StoredFile)
                        .where(StudyAttachment.study_id == root.id)
                    )
                }
                if curator
                else {}
            )
            problems = (
                [
                    {**issue, "acknowledgeable": False}
                    for issue in (root.validation_report or {}).get("issues", [])
                ]
                if curator
                else []
            )
            return {
                "id": sid,
                "audience": audience,
                **page,
                "people": people(
                    page["metadata"], page["summary"], profiles.__getitem__
                ),
                "issue": issue_state(root.issue) if curator else None,
                "problems": problems,
                "counts": {"errors": 0, "warnings": len(problems)},
                "papers": [
                    {
                        "file": name,
                        "url": view_url(sid, "files", name),
                        "bytes": files[name].size,
                        "version": files[name].digest[:16],
                    }
                    for name in page["papers"]
                    if name in files
                ],
                "sources": [
                    {
                        **source,
                        "image_url": view_url(sid, "files", source["image"])
                        if source["image"]
                        else None,
                    }
                    for source in page["sources"]
                ],
            }

    def table(self, sid: str, file: str, principal: Principal) -> dict:
        with self.session_factory() as session:
            root, audience = self._open(session, sid, principal)
            table = for_audience(
                "table", self._document(session, root.id, "table", file), audience
            )
            if table is None:
                raise LookupError(file)
            return table

    def source(self, sid: str, name: str, principal: Principal) -> dict:
        with self.session_factory() as session:
            root, audience = self._open(session, sid, principal)
            source = for_audience(
                "source", self._document(session, root.id, "source", name), audience
            )
            if source is None:
                raise LookupError(name)
            image = source["image"]
            return {
                **source,
                "image_url": view_url(sid, "files", image) if image else None,
            }

    def file(self, sid: str, name: str, principal: Principal) -> tuple[Path, str]:
        """The path and media type of an image or PDF of the study, for curators only."""
        media_type = FILE_TYPES.get(Path(name).suffix.lower())
        if media_type is None or "/" in name or name.startswith("."):
            raise LookupError(name)
        with self.session_factory() as session:
            root, audience = self._open(session, sid, principal)
            if audience != "curator":
                raise LookupError(name)
            # Only a study with a stored page: its files are the ones the page names.
            self._document(session, root.id, "study", "")
            key = session.scalar(
                select(StoredFile.storage_key)
                .join(StudyAttachment)
                .where(
                    StudyAttachment.study_id == root.id, StudyAttachment.name == name
                )
            )
            if key is None:
                raise LookupError(name)
            return self.file_store.path(key), media_type

    def rows(self, principal: Principal) -> dict:
        with self.session_factory() as session:
            records = session.execute(
                select(
                    Study.id,
                    Study.sid,
                    Study.access,
                    Study.licence,
                    Study.creator_id,
                    Study.issue,
                    StudyView.document,
                )
                .join(
                    StudyView,
                    (StudyView.study_id == Study.id) & (StudyView.kind == "row"),
                )
                .where(visibility(principal), Study.creator_id.is_not(None))
                .order_by(Study.sid)
            ).all()
            grants = defaultdict(set)
            for grant in session.scalars(
                select(StudyGrant).where(
                    StudyGrant.study_id.in_([record.id for record in records]),
                    StudyGrant.role == "curator",
                )
            ):
                grants[grant.study_id].add(grant.user_id)
            folders = folder_index({record.sid.split("/")[0] for record in records})
            rows, names = [], set()
            for study in records:
                document = study.document
                access = StudyAccess(
                    sid=study.sid,
                    access=study.access,
                    licence=study.licence,
                    creator_id=study.creator_id,
                    curator_ids=frozenset(grants[study.id]),
                )
                curator = may_write(principal, access)
                row = for_audience("row", document, "curator" if curator else "public")
                if row is None:
                    continue
                substance, name = study.sid.split("/", 1)
                names.update(row["summary"].get("curators", []))
                if creator := row["summary"].get("creator"):
                    names.add(creator)
                rows.append(
                    {
                        "id": study.sid,
                        "name": name,
                        "substance": substance,
                        "substances": folder_substances(
                            substance, row["substances"], folders
                        ),
                        "summary": row["summary"],
                        "counts": {"errors": 0, "warnings": row["warnings"]},
                        "issue": issue_state(study.issue) if curator else None,
                        "curator": curator,
                    }
                )
            return {"rows": rows, "profiles": _profiles(session, names)}
