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
from pathlib import Path
from urllib.parse import quote

from pydantic import ValidationError

from pkdb.curation.state import EngineState
from pkdb.schemas.review import Review
from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.jsonio import JsonFileError, load_json
from pkdb.studyformat.layout import scan_folder
from pkdb.studyformat.load import load_study
from pkdb.studyformat.metadata import MetadataError, read_metadata
from pkdb.studyformat.models import StudyMetadata
from pkdb.studyformat.raw import raw_lines
from pkdb.studyformat.review_edit import ReviewError, read_review
from pkdb.studyformat.revision import read_revision
from pkdb.studyformat.sources import source_view, study_sources
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


def _invalid(path: Path, issues: list[ValidationIssue]) -> dict:
    # The revision lets the app replace an invalid file.
    return {
        "revision": read_revision(path)[1],
        "value": None,
        "issues": [issue.model_dump(mode="json") for issue in issues],
    }


def _metadata_document(folder: Path) -> dict:
    try:
        document = read_metadata(folder)
    except MetadataError as error:
        return _invalid(folder / STUDY_JSON, error.issues)
    return {
        "revision": document.revision,
        "value": document.metadata.model_dump(mode="json", exclude_none=True),
        "issues": [],
    }


def _review_document(folder: Path) -> dict:
    try:
        document = read_review(folder)
    except ReviewError as error:
        return _invalid(folder / REVIEW_JSON, error.issues)
    return {
        "revision": document.revision,
        "value": document.review.model_dump(mode="json", exclude_none=True),
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
        """A key of everything the study page shows, cheap enough for every poll."""
        with self.lock:
            row = self._study_row(identity)
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
        return hashlib.sha256(data).hexdigest()

    def study_detail(self, identity: str) -> dict:
        with self.lock:
            row = self._study_row(identity)
            folder, root = row["_folder"], self.root
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
        study = load_study(_unlinked(folder, root))
        review = _review_document(folder)
        return {
            **detail,
            "metadata": _metadata_document(folder),
            "review": review,
            "acknowledged": _acknowledged(review["value"]),
            "sources": [dataclasses.asdict(source) for source in study_sources(study)],
            "files": sorted(study.layout.files, key=natural_key),
        }

    def study_table(self, identity: str, file: str) -> dict:
        study = load_study(self.study_folder(identity))
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
        view = source_view(load_study(self.study_folder(identity)), source)
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
