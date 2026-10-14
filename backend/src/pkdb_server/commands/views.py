"""Build the stored study pages of the website again (#963).

A stored page is stale when `VIEW_VERSION` changed since it was built. Only studies uploaded
with the texts of their JSON files can be rebuilt; the others get pages at their next upload.
"""

import shutil
import tempfile
from pathlib import Path

from sqlalchemy import delete, exists, func, select

from pkdb.studyformat.tables import REFERENCE_JSON, STUDY_JSON
from pkdb.studyformat.views import VIEW_VERSION
from pkdb_server.db.models.files import StoredFile, StudyAttachment
from pkdb_server.db.models.studies import Study
from pkdb_server.db.models.views import StudyView
from pkdb_server.services.study_views import build_views, store_views


def _stale():
    """The studies with JSON texts whose pages are missing or of another version."""
    current = exists(
        select(StudyView.study_id).where(
            StudyView.study_id == Study.id,
            StudyView.kind == "study",
            StudyView.version == VIEW_VERSION,
        )
    )
    return Study.study_json.is_not(None) & ~current


def stale_view_count(session) -> int:
    return session.scalar(select(func.count()).select_from(Study).where(_stale()))


def rebuild_views(session_factory, file_store, settings, *, everything=False) -> dict:
    """Build the pages of the stale studies (of every study with JSON texts with
    `everything`) from their stored files, one transaction per study."""
    condition = Study.study_json.is_not(None) if everything else _stale()
    with session_factory() as session:
        sids = list(
            session.scalars(select(Study.sid).where(condition).order_by(Study.sid))
        )
    rebuilt, failed = [], []
    for sid in sids:
        try:
            with session_factory.begin() as session:
                study = session.scalar(select(Study).where(Study.sid == sid))
                with tempfile.TemporaryDirectory() as directory:
                    folder = Path(directory).joinpath(*sid.split("/"))
                    folder.mkdir(parents=True)
                    (folder / STUDY_JSON).write_text(
                        study.study_json, encoding="utf-8", newline=""
                    )
                    (folder / REFERENCE_JSON).write_text(
                        study.reference_json, encoding="utf-8", newline=""
                    )
                    for name, key in session.execute(
                        select(StudyAttachment.name, StoredFile.storage_key)
                        .join(StoredFile)
                        .where(StudyAttachment.study_id == study.id)
                    ):
                        shutil.copyfile(file_store.path(key), folder / name)
                    views = build_views(
                        folder,
                        warnings=len((study.validation_report or {}).get("issues", [])),
                        max_rows=settings.upload_max_rows,
                        max_files=settings.upload_max_files,
                    )
                session.execute(delete(StudyView).where(StudyView.study_id == study.id))
                store_views(session, study.id, views)
            rebuilt.append(sid)
        except (OSError, ValueError) as error:
            failed.append({"sid": sid, "error": f"{type(error).__name__}: {error}"})
    return {"rebuilt": rebuilt, "failed": failed}
