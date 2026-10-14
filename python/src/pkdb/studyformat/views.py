"""The documents of the study page that the curation app and the website show (#963).

The local curation server (`pkdb curate`) builds its study page, its tables and its sources with
these functions, and the backend builds the same documents when a study folder is uploaded
(`study_view`, `row_view`, `table_view`, `source_document`) and stores them. The local server adds
its local state, such as sync, jobs and the files on disk; the backend adds the people, the
problems of the upload and the URLs of the files when it serves them, and `for_audience` strips
what the public does not see.
"""

import dataclasses
import json
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from pkdb.schemas.review import Review, ReviewTarget
from pkdb.studyformat.jsonio import JsonFileError, load_json
from pkdb.studyformat.layout import Layout, workbook_tables
from pkdb.studyformat.load import LoadedStudy
from pkdb.studyformat.metadata import read_metadata
from pkdb.studyformat.models import StudyMetadata
from pkdb.studyformat.raw import raw_lines
from pkdb.studyformat.review_edit import read_review
from pkdb.studyformat.sources import has_source, source_view, study_sources
from pkdb.studyformat.substances import study_substances
from pkdb.studyformat.sync import NEW_TABLE_KINDS
from pkdb.studyformat.tables import (
    INFO_CLASSES,
    KIND_LABELS,
    KIND_ORDER,
    RAW_KIND,
    TABLES,
    column_classes,
    table_file,
)
from pkdb.studyformat.targets import match_target
from pkdb.studyformat.text import natural_key
from pkdb.studyformat.validation import acknowledgement_scope

#: The version of the documents that the backend stores. Raise it when a document changes;
#: `pkdb-server rebuild-views` then builds the stored documents again.
VIEW_VERSION = 1

IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
#: The media types of the files that the file route serves: the images of the sources and the PDFs.
FILE_TYPES = {**IMAGE_TYPES, ".pdf": "application/pdf"}


def _read(path: Path) -> object | None:
    try:
        if path.is_symlink() or not path.is_file():
            return None
        return load_json(path.read_bytes())
    except JsonFileError, OSError:
        return None


def _object(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _user(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _curator_names(value: object) -> list[str]:
    names = []
    for item in value if isinstance(value, list) else []:
        name = _user(_object(item).get("user") if isinstance(item, dict) else item)
        if name:
            names.append(name)
    return names


def _review(folder: Path) -> tuple[str | None, int]:
    data = _read(folder / "review.json")
    try:
        review = Review.model_validate(data)
    except ValidationError:
        return None, 0
    return review.status, sum(1 for item in review.items if item.state == "open")


def _title(folder: Path) -> str | None:
    title = _object(_read(folder / "reference.json")).get("title")
    return title if isinstance(title, str) else None


def study_summary(folder: Path) -> dict:
    folder = Path(folder)
    raw = _object(_read(folder / "study.json"))
    try:
        study = StudyMetadata.model_validate(raw)
        creator = study.creator
        curators = [item.user for item in study.curators]
        issue = study.issue
        release = study.release.model_dump(mode="json") if study.release else None
        provenance = study.provenance.model_dump(mode="json")
    except ValidationError:
        creator = _user(raw.get("creator"))
        curators = _curator_names(raw.get("curators"))
        issue = raw.get("issue")
        issue = (
            issue if isinstance(issue, int) and not isinstance(issue, bool) else None
        )
        release = _object(raw.get("release"))
        release = (
            {"pkdb_id": release.get("pkdb_id"), "date": release.get("date")}
            if release.get("pkdb_id")
            else None
        )
        provenance = _object(raw.get("provenance"))
    kind = provenance.get("kind") if isinstance(provenance.get("kind"), str) else None
    status, open_items = _review(folder)
    return {
        "title": _title(folder),
        "review_status": status,
        "open_items": open_items,
        "curators": curators,
        "creator": creator,
        "release": release,
        "issue": issue,
        "provenance": {"kind": kind}
        | (
            {"method": provenance.get("method")} if kind == "automatic_curation" else {}
        ),
        "ai": kind == "automatic_curation",
    }


def targets(study: LoadedStudy | None, review: Review | None) -> dict:
    """What the target of each review item with a file selects, by item id.

    Nothing for a study beyond the upload limits or an invalid `review.json`.
    """
    if study is None or review is None:
        return {}
    return {
        item.id: dataclasses.asdict(match_target(study, item.target))
        for item in review.items
        if item.target is not None and item.target.file is not None
    }


def acknowledged(review: dict | None) -> list[dict]:
    """The warnings that review items acknowledge; a dismissed item no longer acknowledges."""
    return [
        {
            "id": item["id"],
            "code": item["acknowledges"],
            "target": item.get("target"),
            "text": item["text"],
            "author": item["author"],
            "resolved_by": item.get("resolved_by"),
            "resolved": item.get("resolved"),
            "scope": acknowledgement_scope(
                ReviewTarget.model_validate(item["target"])
                if item.get("target")
                else None
            ),
        }
        for item in (review["items"] if review else [])
        if item.get("acknowledges") and item["state"] != "dismissed"
    ]


# The kinds of tables for the app, in the order of the workbook sheets with the raw table last:
# their label and class of information, whether a table of the kind belongs to one source (the
# others name the source of each row), and whether Add table adds one.
TABLE_KINDS = tuple(
    {
        "kind": kind,
        "label": KIND_LABELS[kind],
        "info": INFO_CLASSES[kind],
        "per_source": kind == RAW_KIND or TABLES[kind].per_source,
        "addable": kind in NEW_TABLE_KINDS,
    }
    for kind in (*KIND_ORDER, RAW_KIND)
)


def study_tables(study: LoadedStudy) -> list[dict]:
    """The table files and raw tables of a study in the order of the workbook sheets.

    Each names its kind, its class of information, the source it belongs to (None for a table
    shared by several sources, which names the source of each row) and its number of data rows:
    the rows of a table below its header, the non-empty lines of a raw table. A file that could
    not be read has no count.
    """
    layout = study.layout
    sources = {table.name: table.source for table in layout.tables} | {
        raw.name: raw.source for raw in layout.raw_tables
    }
    entries = []
    for file, kind in workbook_tables(layout):
        if kind == RAW_KIND:
            raw = study.raw(file)
            rows = None if raw is None else len(raw_lines(raw))
        else:
            table = study.table(file)
            rows = None if table is None else len(table.rows)
        entries.append(
            {
                "file": file,
                "kind": kind,
                "info": INFO_CLASSES[kind],
                "source": sources[file],
                "rows": rows,
            }
        )
    return entries


# The tables whose rows the cells of other tables name, by which the app links a name to its row.
NAMED_KINDS = ("subjects", "interventions")


def name_lines(study: LoadedStudy | None) -> dict[str, dict]:
    """The file of subjects.tsv and interventions.tsv and the line of each name in it.

    The app links a name in a cell to the row of the name with it, without reading these
    tables. A name of two rows, which validation reports, has the line of the first. A table
    that is missing or could not be read, and a study beyond the upload limits, have no names.
    """
    found: dict[str, dict] = {}
    for kind in NAMED_KINDS:
        lines: dict[str, int] = {}
        if study is not None:
            for _, row in study.rows(kind):
                name = row.cells.get("name", "")
                if name and name not in lines:
                    lines[name] = row.line
        found[kind] = {"file": table_file(kind), "lines": lines}
    return found


def _text(value) -> str | None:
    if isinstance(value, bool) or not isinstance(value, str | int | float):
        return None
    return str(value)


def _author(value) -> str | None:
    if not isinstance(value, dict):
        return None
    name = " ".join(
        part
        for part in (value.get("first_name"), value.get("last_name"))
        if isinstance(part, str) and part.strip()
    )
    organization = value.get("organization")
    return name or (organization if isinstance(organization, str) else None) or None


def reference_summary(folder: Path) -> dict | None:
    path = Path(folder) / "reference.json"
    if not path.is_file() or path.is_symlink():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError, OSError:
        return {"error": "reference.json is not valid JSON"}
    if not isinstance(data, dict):
        return {"error": "reference.json is not valid JSON"}
    authors = data.get("authors")
    return {
        **{
            key: _text(data.get(key))
            for key in ("sid", "pmid", "doi", "title", "journal", "abstract")
        },
        "publication_date": _text(data.get("publication_date") or data.get("date")),
        "authors": [
            name
            for name in map(_author, authors if isinstance(authors, list) else [])
            if name
        ],
    }


def reference_match(study: dict | None, reference: dict | None) -> bool | None:
    """Whether `reference.json` has the PubMed ID and DOI that `study.json` names.

    None when `study.json` names neither or is invalid. DOIs compare case-insensitively, as
    validation compares them.
    """
    identifiers = {
        name: value
        for name, value in ((study or {}).get("reference") or {}).items()
        if name in {"pmid", "doi"} and value
    }
    if not identifiers:
        return None
    if not reference or "error" in reference:
        return False
    return all(
        (reference.get(name) or "").lower() == value.lower()
        if name == "doi"
        else reference.get(name) == value
        for name, value in identifiers.items()
    )


def people(study: dict | None, summary: dict, profile: Callable[[str], dict]) -> dict:
    """The creator, the curators with their ratings and the collaborators, with profiles.

    `study` is the valid `study.json`; without it, the names that the row summary could read.
    `profile` gives the profile of a username: the bundled roster in the local app, the
    accounts of the backend on the website.
    """
    if study is None:
        creator = summary.get("creator")
        curators = [{"user": user} for user in summary.get("curators", [])]
        collaborators = []
    else:
        creator = study.get("creator")
        curators = study.get("curators", [])
        collaborators = study.get("collaborators", [])
    return {
        "creator": profile(creator) if creator else None,
        "curators": [
            {
                "user": curator["user"],
                "rating": curator.get("rating"),
                "profile": profile(curator["user"]),
            }
            for curator in curators
        ],
        "collaborators": [profile(name) for name in collaborators],
    }


def paper_names(layout: Layout) -> list[str]:
    """The PDFs at the top of the study folder: `<name>.pdf` first, then the others by name.

    The suffix counts in any case. A hidden file (also an AppleDouble `._name.pdf`), a symlink
    or a folder is no paper: the scan registers none of them as an attachment.
    """
    files = [name for name in layout.attachments if Path(name).suffix.lower() == ".pdf"]
    return sorted(
        files, key=lambda name: (Path(name).stem != layout.study, natural_key(name))
    )


def table_view(study: LoadedStudy, file: str) -> dict | None:
    """The rows of a table file or a raw table of the study; None for any other file."""
    if (table := study.table(file)) is not None:
        header = table.spec.names
        return {
            "file": file,
            "kind": "table",
            "header": list(header),
            # What each column names, by which the app tints it; a raw table has none.
            "classes": list(column_classes(table.spec)),
            "rows": [
                {
                    "line": row.line,
                    "cells": [row.cells.get(name, "") for name in header],
                }
                for row in table.rows
            ],
        }
    if (raw := study.raw(file)) is not None:
        return {
            "file": file,
            "kind": "raw",
            "rows": [
                {"line": line, "cells": list(cells)} for line, cells in raw_lines(raw)
            ],
        }
    return None


def source_document(study: LoadedStudy, source: str) -> dict | None:
    """The view of a source of the study (`source_view`) as a document; None for no source."""
    if not has_source(study, source):
        return None
    # A KeyError from here on is a bug, not a missing source.
    return dataclasses.asdict(source_view(study, source))


def study_view(folder: Path, study: LoadedStudy) -> dict:
    """The study page of a valid study folder, as the backend stores it at upload.

    The documents as the local server reads them: `study.json` and `review.json` as their
    values, the reference, the sources, tables and targets of `study`. Without the people and
    the URLs of the files, which the backend adds when it serves the page, and with the
    substances that the tables name, by which the list of studies filters.
    """
    folder = Path(folder)
    layout = study.layout
    metadata = read_metadata(folder).metadata.model_dump(mode="json", exclude_none=True)
    review_model = read_review(folder).review
    review = review_model.model_dump(mode="json", exclude_none=True)
    reference = reference_summary(folder)
    return {
        "summary": study_summary(folder),
        "metadata": metadata,
        "review": review,
        "reference": reference,
        "reference_match": reference_match(metadata, reference),
        "acknowledged": acknowledged(review),
        "sources": [dataclasses.asdict(source) for source in study_sources(study)],
        "files": sorted(layout.files, key=natural_key),
        "papers": paper_names(layout),
        "tables": study_tables(study),
        "table_kinds": [dict(kind) for kind in TABLE_KINDS],
        "targets": targets(study, review_model),
        "name_lines": name_lines(study),
        "substances": list(study_substances(folder)),
    }


def row_view(view: dict, *, warnings: int) -> dict:
    """The row of a study in the list of studies: the summary of `view`, the substances that
    its tables name, and the number of warnings of its upload."""
    return {
        "summary": view["summary"],
        "substances": view["substances"],
        "warnings": warnings,
    }


Audience = Literal["public", "curator"]
ViewKind = Literal["study", "row", "table", "source"]

# The keys of a summary and of study.json that the public sees; anything else, such as the
# review status, the open items and the issue, belongs to the curation.
_PUBLIC_SUMMARY = ("title", "curators", "creator", "release", "provenance", "ai")
_PUBLIC_METADATA = (
    "format",
    "reference",
    "creator",
    "curators",
    "collaborators",
    "licence",
    "access",
    "provenance",
    "release",
    "descriptions",
    "comments",
    "notes",
)


def _public_summary(summary: dict) -> dict:
    public = {key: summary[key] for key in _PUBLIC_SUMMARY if key in summary}
    if "provenance" in public:
        public["provenance"] = {"kind": public["provenance"].get("kind")}
    return public


def _public_metadata(metadata: dict) -> dict:
    public = {key: metadata[key] for key in _PUBLIC_METADATA if key in metadata}
    if "curators" in public:
        public["curators"] = [
            {"user": curator["user"]} for curator in public["curators"]
        ]
    if "provenance" in public:
        public["provenance"] = {"kind": public["provenance"].get("kind")}
    return public


def _public_study(view: dict) -> dict:
    raw = {entry["file"] for entry in view["tables"] if entry["kind"] == RAW_KIND}
    return {
        **view,
        "summary": _public_summary(view["summary"]),
        "metadata": _public_metadata(view["metadata"]),
        "review": None,
        "acknowledged": [],
        "targets": {},
        "files": [],
        "papers": [],
        "tables": [entry for entry in view["tables"] if entry["kind"] != RAW_KIND],
        "sources": [
            {
                **source,
                "image": None,
                "raw": None,
                "raw_kind": None,
                "missing_image": None,
                "missing_raw": None,
                "tables": [name for name in source["tables"] if name not in raw],
            }
            for source in view["sources"]
        ],
    }


def _public_row(row: dict) -> dict:
    return {**row, "summary": _public_summary(row["summary"]), "warnings": 0}


def _public_table(table: dict) -> dict | None:
    return None if table["kind"] == RAW_KIND else table


def _public_source(source: dict) -> dict:
    return {
        **source,
        "image": None,
        "image_size": None,
        "raw_grid": None,
        "digitization": None,
        "overlay": [],
        "unmatched": [],
        "layout": "side_by_side",
        "mapped": [table for table in source["mapped"] if table["kind"] != RAW_KIND],
    }


_PUBLIC: dict[str, Callable[[dict], dict | None]] = {
    "study": _public_study,
    "row": _public_row,
    "table": _public_table,
    "source": _public_source,
}


def for_audience(kind: ViewKind, document: dict, audience: Audience) -> dict | None:
    """What `audience` sees of a document of kind `kind`; None for a raw table to the public.

    Curators, who may write the study, see the document as it is. The public sees the same keys
    with nothing of the curation in them: no review, review targets or acknowledged warnings,
    no issue, no curator ratings, no provenance beyond its kind, no list of the files of the study,
    no raw tables,
    no images and PDFs, and the plot of a figure without the figure (#963).
    """
    if audience == "curator":
        return document
    return _PUBLIC[kind](document)
