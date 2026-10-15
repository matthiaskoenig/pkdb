"""Build the stored study pages of the website again (#963).

A stored page is stale when `VIEW_VERSION` changed since it was built. Only studies uploaded
with the texts of their JSON files can be rebuilt; the others get pages at their next upload.
"""

import shutil
import sys
import tempfile
from pathlib import Path

from sqlalchemy import delete, exists, func, select
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from pkdb.studyformat.tables import REFERENCE_JSON, STUDY_JSON
from pkdb.studyformat.views import VIEW_VERSION
from pkdb_server.db.models.files import StoredFile, StudyAttachment
from pkdb_server.db.models.studies import Study
from pkdb_server.db.models.views import StudyView
from pkdb_server.services.study_views import (
    build_views,
    store_views,
    warning_count,
)


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


#: How many studies the command rebuilds between two reports of its progress on stderr.
PROGRESS_EVERY = 100


def _error(error: Exception) -> str:
    # The text of a database error can hold credentials or data, which the CLI redacts.
    if isinstance(error, SQLAlchemyError):
        return type(error).__name__
    return f"{type(error).__name__}: {error}"


def _rebuild(session_factory, file_store, settings, sid: str) -> bool:
    """Build the pages of `sid` from its stored files; False for a study that is gone."""
    with session_factory.begin() as session:
        # Lock the row like an upload does: a concurrent upload waits for this
        # rebuild or is read committed, so texts, files and pages share one state.
        study = session.scalar(select(Study).where(Study.sid == sid).with_for_update())
        if study is None:
            return False  # deleted or renamed since the list was read
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
            documents = build_views(
                folder,
                warnings=warning_count(study.validation_report),
                max_rows=settings.upload_max_rows,
                max_files=settings.upload_max_files,
            )
        session.execute(delete(StudyView).where(StudyView.study_id == study.id))
        store_views(session, study.id, documents)
    return True


def rebuild_views(session_factory, file_store, settings, *, everything=False) -> dict:
    """Build the pages of the stale studies (of every study with JSON texts with
    `everything`) from their stored files, one transaction per study.

    A study that fails is reported in `failed` and the others go on. A database that is gone
    (`OperationalError`) ends the run with the type of the error in `error`. The progress goes
    to stderr every `PROGRESS_EVERY` studies, so stdout keeps one JSON object.
    """
    condition = Study.study_json.is_not(None) if everything else _stale()
    with session_factory() as session:
        sids = list(
            session.scalars(select(Study.sid).where(condition).order_by(Study.sid))
        )
    rebuilt, failed = [], []
    for done, sid in enumerate(sids, 1):
        try:
            if _rebuild(session_factory, file_store, settings, sid):
                rebuilt.append(sid)
        except OperationalError as error:
            return {"rebuilt": rebuilt, "failed": failed, "error": type(error).__name__}
        except Exception as error:
            failed.append({"sid": sid, "error": _error(error)})
        if done % PROGRESS_EVERY == 0:
            print(f"rebuilt {done} of {len(sids)}", file=sys.stderr, flush=True)
    return {"rebuilt": rebuilt, "failed": failed, "error": None}
