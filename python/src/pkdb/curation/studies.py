"""Format 2 study folders for the curation engine: row summaries and the study page of the API.

`study_summary` reads leniently: a file that does not parse gives None or empty values, never an
exception. `StudiesMixin` reads engine attributes lock, root, studies and jobs, and uses engine
method _issue_for. It serves only files that the study registers: no symlink, nothing outside the
study folder.
"""

import dataclasses
import hashlib
import json
import os
import stat
from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote

from pydantic import ValidationError

from pkdb.curation.state import EngineState
from pkdb.preparation import MAX_FILES, MAX_ROWS
from pkdb.schemas.review import Review
from pkdb.schemas.validation import StudyValidationError, ValidationIssue
from pkdb.studyformat.jsonio import JsonFileError, load_json
from pkdb.studyformat.layout import Layout, scan_folder
from pkdb.studyformat.load import LoadedStudy, load_study
from pkdb.studyformat.metadata import MetadataDocument, MetadataError, read_metadata
from pkdb.studyformat.models import StudyMetadata
from pkdb.studyformat.raw import raw_lines
from pkdb.studyformat.review_edit import ReviewError, read_review
from pkdb.studyformat.revision import read_revision, revision_of
from pkdb.studyformat.sources import source_view, study_sources
from pkdb.studyformat.sync import conflict_data, sync_study
from pkdb.studyformat.tables import REVIEW_JSON, STUDY_JSON
from pkdb.studyformat.text import natural_key

IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


class AmbiguousStudy(ValueError):
    """Two folders of the workspace have the same identity `<substance>/<name>`."""

    def __init__(self, identity: str, paths: list[str]):
        super().__init__(
            f"{identity} is the identity of two folders: {', '.join(paths)}; rename one"
        )


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


def _issues(issues: list[ValidationIssue]) -> list[dict]:
    return [issue.model_dump(mode="json") for issue in issues]


def _document(folder: Path, layout: Layout, name: str, read: Callable) -> dict:
    """`study.json` or `review.json` as `{"revision", "value", "issues"}`; `value` None when invalid.

    A file that the layout does not register, such as a symlink or a folder, is never read: it
    gets the issues of the layout and no revision, or the `absent` revision when it is missing.
    """
    path = folder / name
    if name not in layout.files:
        return {
            "revision": None if os.path.lexists(path) else revision_of(None),
            "value": None,
            "issues": _issues(
                [
                    issue
                    for issue in layout.issues
                    if issue.source and issue.source.file == name
                ]
            ),
        }
    try:
        document = read(folder)
    except (MetadataError, ReviewError) as error:
        # The revision lets the app replace an invalid file.
        return {
            "revision": read_revision(path)[1],
            "value": None,
            "issues": _issues(error.issues),
        }
    model = (
        document.metadata if isinstance(document, MetadataDocument) else document.review
    )
    return {
        "revision": document.revision,
        "value": model.model_dump(mode="json", exclude_none=True),
        "issues": [],
    }


def _acknowledged(review: dict | None) -> list[dict]:
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
        }
        for item in (review["items"] if review else [])
        if item.get("acknowledges") and item["state"] != "dismissed"
    ]


def _unlinked(folder: Path, root: Path) -> Path:
    # The scan skips a folder that became a symlink but keeps its row; never read through it.
    if folder.is_symlink() or not folder.resolve().is_relative_to(root):
        raise LookupError(f"{folder} is not a study folder of the workspace")
    return folder


def _bounded(folder: Path) -> LoadedStudy:
    """The study within the upload limits; StudyValidationError beyond them."""
    return load_study(folder, max_rows=MAX_ROWS, max_files=MAX_FILES)


class StudiesMixin(EngineState):
    def _study_row(self, identity: str) -> dict:
        matches = [row for row in self.studies.values() if row["id"] == identity]
        if not matches:
            raise LookupError(f"{identity} is not a study of this workspace")
        if len(matches) > 1:
            raise AmbiguousStudy(identity, [row["path"] for row in matches])
        return matches[0]

    def study_folder(self, identity: str) -> Path:
        with self.lock:
            folder, root = self._study_row(identity)["_folder"], self.root
        return _unlinked(folder, root)

    def study_version(self, identity: str) -> str:
        """A key of everything the study page shows, cheap enough for every poll.

        The fingerprint hashes every file of the study, so the key also versions its tables and
        sources.
        """
        with self.lock:
            row = self._study_row(identity)
            folder, root = row["_folder"], self.root
            key = {
                "fingerprint": row["_fingerprint"],
                "status": row["status"],
                "mode": row["mode"],
                "report_id": row["report_id"],
                "sync": row["sync"],
                "issue": self._issue_for(row["summary"].get("issue")),
                "jobs": [job for job in self.jobs if job["study_id"] == identity],
            }
            data = json.dumps(key, sort_keys=True, default=str).encode()
        _unlinked(folder, root)
        return hashlib.sha256(data).hexdigest()

    def study_detail(self, identity: str) -> dict:
        with self.lock:
            row = self._study_row(identity)
            folder, root = row["_folder"], self.root
            conflicted = row["sync"]["status"] == "conflict"
            # A copy, so that the files are read outside the lock.
            detail = json.loads(
                json.dumps(
                    {
                        "id": row["id"],
                        "path": row["path"],
                        "status": row["status"],
                        "mode": row["mode"],
                        "sync": row["sync"],
                        "counts": row["counts"],
                        "summary": row["summary"],
                        "issue": self._issue_for(row["summary"].get("issue")),
                        "problems": row["problems"],
                        "jobs": [
                            job
                            for job in reversed(self.jobs)
                            if job["study_id"] == identity
                        ],
                        "report_id": row["report_id"],
                    }
                )
            )
        _unlinked(folder, root)
        try:
            study = _bounded(folder)
        except StudyValidationError as error:
            # Beyond the upload limits: the documents, and the limit as the first problem.
            layout = scan_folder(folder)
            limits = _issues(error.report.issues)
            detail["problems"] = [
                *limits,
                *(problem for problem in detail["problems"] if problem not in limits),
            ]
            sources, files = [], []
        else:
            layout = study.layout
            sources = [dataclasses.asdict(source) for source in study_sources(study)]
            files = sorted(layout.files, key=natural_key)
        review = _document(folder, layout, REVIEW_JSON, read_review)
        return {
            **detail,
            "metadata": _document(folder, layout, STUDY_JSON, read_metadata),
            "review": review,
            "acknowledged": _acknowledged(review["value"]),
            "conflicts": self._conflicts(folder) if conflicted else [],
            "sources": sources,
            "files": files,
        }

    def _conflicts(self, folder: Path) -> list[dict]:
        """The conflicting rows of the workbook and the tables, as the sync plans them."""
        try:
            result = sync_study(
                folder, self._local_vocabulary(), check=True, max_rows=MAX_ROWS
            )
        except OSError, ValueError:
            return []
        return [conflict_data(conflict) for conflict in result.conflicts]

    def study_table(self, identity: str, file: str) -> dict:
        study = _bounded(self.study_folder(identity))
        if (table := study.table(file)) is not None:
            header = table.spec.names
            return {
                "file": file,
                "kind": "table",
                "header": list(header),
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
                    {"line": line, "cells": list(cells)}
                    for line, cells in raw_lines(raw)
                ],
            }
        raise LookupError(f"{file} is not a table of {identity}")

    def study_source(self, identity: str, source: str) -> dict:
        view = source_view(_bounded(self.study_folder(identity)), source)
        image_url = None
        if view.image is not None:
            segments = (*identity.split("/"), "files", view.image)
            image_url = "/local/studies/" + "/".join(
                quote(s, safe="") for s in segments
            )
        return {**dataclasses.asdict(view), "image_url": image_url}

    def study_image(self, identity: str, file: str) -> tuple[bytes, str]:
        folder = self.study_folder(identity)
        media_type = IMAGE_TYPES.get(Path(file).suffix.lower())
        # Registered files are regular files at the top level of the folder, never symlinks.
        if media_type is None or file not in scan_folder(folder).files:
            raise LookupError(f"{file} is not an image of {identity}")
        path = folder / file
        if not path.resolve().is_relative_to(folder.resolve()):
            raise LookupError(f"{file} is outside the study folder")
        try:
            # A symlink placed after the check is not followed either.
            descriptor = os.open(
                path,
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0),
            )
        except OSError:
            raise LookupError(f"{file} cannot be read") from None
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise LookupError(f"{file} is not a regular file")
            return stream.read(), media_type
