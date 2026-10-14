"""The study pages of the website: built at upload, stored, served by audience (#963).

The documents come from `pkdb.studyformat.views`, the builder of the local curation app, so the
website shows a study as `pkdb curate` does.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from pkdb.studyformat.load import load_study
from pkdb.studyformat.tables import REFERENCE_JSON, STUDY_JSON
from pkdb.studyformat.views import (
    VIEW_VERSION,
    row_view,
    source_document,
    study_view,
    table_view,
)
from pkdb_server.db.models.views import StudyView


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
