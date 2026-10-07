"""Format 2 study folders for the curation engine: row summaries and the study page of the API.

`study_summary` reads leniently: a file that does not parse gives None or empty values, never an
exception. `StudiesMixin` reads engine attributes lock, root, studies, jobs and offline, and uses
engine methods _issue_for, _local_vocabulary, _record_write, author and scan. It serves only files that the study
registers: no symlink, nothing outside the study folder. Its writes go through the library, which
takes `folder_lock`; anything that takes the engine lock runs before it.
"""

import dataclasses
import hashlib
import json
import os
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote

from pydantic import ValidationError

from pkdb.curation.launch import open_path
from pkdb.curation.metadata import people, reference_match, reference_summary
from pkdb.curation.state import EngineState
from pkdb.identity import Author
from pkdb.preparation import MAX_FILES, MAX_ROWS
from pkdb.references import ReferenceResolver
from pkdb.schemas.review import Review, ReviewTarget
from pkdb.schemas.validation import StudyValidationError, ValidationIssue
from pkdb.studyformat import metadata as study_metadata
from pkdb.studyformat import review_edit
from pkdb.studyformat.jsonio import JsonFileError, load_json
from pkdb.studyformat.layout import Layout, scan_folder
from pkdb.studyformat.load import LoadedStudy, load_study, validation_issues
from pkdb.studyformat.metadata import MetadataDocument, MetadataError, read_metadata
from pkdb.studyformat.models import StudyMetadata
from pkdb.studyformat.raw import raw_lines
from pkdb.studyformat.review_edit import (
    ReviewError,
    matching_warnings,
    read_review,
    warning_locations,
)
from pkdb.studyformat.revision import folder_lock, read_revision, revision_of
from pkdb.studyformat.sources import source_view, study_sources
from pkdb.studyformat.sync import SyncResult, add_table, conflict_data, sync_study
from pkdb.studyformat.tables import REVIEW_JSON, STUDY_JSON
from pkdb.studyformat.text import natural_key
from pkdb.studyformat.validation import validate_folder
from pkdb.studyformat.workbook.base import workbook_path

IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


class UnsafeFile(ValueError):
    """A file of the study that the app refuses to open or write, such as a symlink."""


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


def _review_error(issues: list[ValidationIssue]) -> ReviewError:
    return ReviewError("; ".join(issue.message for issue in issues), issues)


def _writable(
    folder: Path, name: str, error: Callable[[list[ValidationIssue]], Exception]
) -> None:
    """Refuse to write a document that the layout does not register, such as a symlink.

    The write would read it to check the revision, and a conflict would return its content.
    """
    if not os.path.lexists(folder / name):
        return
    layout = scan_folder(folder)
    if name not in layout.files:
        raise error(
            [
                issue
                for issue in layout.issues
                if issue.source and issue.source.file == name
            ]
        )


def _text(payload: dict, name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str):
        raise ValueError(f"Expected text in {name}")
    return value


def _optional_text(payload: dict, name: str) -> str | None:
    return None if payload.get(name) is None else _text(payload, name)


def _line(payload: dict) -> int | None:
    line = payload.get("line")
    if line is not None and (not isinstance(line, int) or isinstance(line, bool)):
        raise ValueError("Expected a line number")
    return line


def _located(line: int | None, column: str | None) -> str:
    parts = [f"line {line}"] if line is not None else []
    parts += [f"column {column}"] if column is not None else []
    return " ".join(parts) or "the file"


def _sync_result(result: SyncResult) -> dict:
    """A sync as the app reports it, like `pkdb tables sync` without the paths."""
    return {
        "ok": result.ok,
        "workbook_action": result.workbook_action,
        "changes": [
            {"file": change.file, "action": change.action} for change in result.changes
        ],
        "conflicts": [conflict_data(conflict) for conflict in result.conflicts],
        "issues": _issues(list(result.issues)),
    }


def _review_message(payload: dict, result: dict) -> str:
    """A review action as the activity of the study lists it."""
    item = result["item"]["id"] if "item" in result else payload.get("item")
    match payload["action"]:
        case "add":
            return f"Added review item {item}"
        case "reply":
            return f"Replied to review item {item}"
        case "status":
            return f"Set the review status to {payload['status']}"
        case "acknowledge":
            return f"Acknowledged warning {payload['code']} with review item {item}"
        case action:
            done = {"resolve": "Resolved", "dismiss": "Dismissed", "reopen": "Reopened"}
            return f"{done[action]} review item {item}"


def _sync_activity(done: str, sync: SyncResult) -> tuple[str, str]:
    """The message and status of a workbook action for the activity of the study."""
    if sync.ok:
        return done, "succeeded"
    if unresolved := sum(conflict.kept is None for conflict in sync.conflicts):
        return f"{done}; {unresolved} conflicts remain", "conflict"
    return f"{done}; the sync found errors", "failed"


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
                "message": row.get("message"),
                "last_upload": row["last_upload"],
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
                        "message": row.get("message"),
                        "last_upload": row["last_upload"],
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
        metadata = _document(folder, layout, STUDY_JSON, read_metadata)
        reference = reference_summary(folder)
        return {
            **detail,
            "metadata": metadata,
            "reference": reference,
            "reference_match": reference_match(metadata["value"], reference),
            # The study page shows the people without a second request for the roster.
            "people": people(metadata["value"], detail["summary"]),
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

    def _rescan(self) -> None:
        """Rescan after a write, so that the study ETag changes at once.

        The write succeeded; a failed scan is left to the watcher, which retries every second.
        """
        try:
            self.scan()
        except Exception:
            # Nothing is logged, since errors can carry paths and settings.
            pass

    def write_metadata(self, identity: str, revision: str, metadata: dict) -> dict:
        """Write `study.json`; a changed PubMed ID or DOI refreshes `reference.json`.

        The app always writes over the revision it read, never blindly.
        """
        # study.json records no author, but writes need a user (spec 7.4).
        self.author()
        folder = self.study_folder(identity)
        if not isinstance(revision, str):
            raise ValueError("Expected the revision of study.json that was read")
        try:
            model = StudyMetadata.model_validate(metadata)
        except ValidationError as error:
            raise MetadataError(
                validation_issues(error, STUDY_JSON, study_metadata.CODE)
            ) from None
        _writable(folder, STUDY_JSON, MetadataError)
        written = study_metadata.write_metadata(
            folder, model, revision, resolver=ReferenceResolver(offline=self.offline)
        )
        self._record_write(identity, "Saved study.json")
        self._rescan()
        return {
            "revision": written.revision,
            "reference": written.reference,
            "reference_error": written.reference_error,
        }

    def review_action(self, identity: str, payload: dict) -> dict:
        """Change `review.json` with `payload["action"]` as the current author.

        The app always writes over the revision it read, never blindly.
        """
        author = self.author()
        folder = self.study_folder(identity)
        revision = _text(payload, "revision")
        _writable(folder, REVIEW_JSON, _review_error)
        try:
            result = self._review_change(folder, author, revision, payload)
        except ValidationError as error:
            # A new item, target or reply that the review model refuses.
            raise _review_error(
                validation_issues(error, REVIEW_JSON, review_edit.CODE)
            ) from None
        self._record_write(identity, _review_message(payload, result))
        self._rescan()
        return result

    def _review_change(
        self, folder: Path, author: Author, revision: str, payload: dict
    ) -> dict:
        match payload.get("action"):
            case "add":
                # The review model validates the kind.
                kind: Any = payload.get("kind")
                target = payload.get("target")
                item, revision = review_edit.add_item(
                    folder,
                    author,
                    kind=kind,
                    text=_text(payload, "text"),
                    target=None
                    if target is None
                    else ReviewTarget.model_validate(target),
                    acknowledges=_optional_text(payload, "acknowledges"),
                    revision=revision,
                )
                return {
                    "revision": revision,
                    "item": item.model_dump(mode="json", exclude_none=True),
                }
            case "reply":
                revision = review_edit.reply(
                    folder,
                    author,
                    _text(payload, "item"),
                    _text(payload, "text"),
                    revision=revision,
                )
                return {"revision": revision}
            case "resolve" | "dismiss" | "reopen" as action:
                change = {
                    "resolve": review_edit.resolve,
                    "dismiss": review_edit.dismiss,
                    "reopen": review_edit.reopen,
                }[action]
                revision = change(
                    folder,
                    author,
                    _text(payload, "item"),
                    _optional_text(payload, "text"),
                    revision=revision,
                )
                return {"revision": revision}
            case "status":
                status = _text(payload, "status")
                # Chosen before the folder lock that the write takes.
                vocabulary = self._local_vocabulary() if status == "approved" else None
                revision = review_edit.set_status(
                    folder, author, status, vocabulary=vocabulary, revision=revision
                )
                return {"revision": revision}
            case "acknowledge":
                return self._acknowledge(folder, author, revision, payload)
            case action:
                raise ValueError(f"Unknown review action {action!r}")

    def _acknowledge(
        self, folder: Path, author: Author, revision: str, payload: dict
    ) -> dict:
        """Acknowledge the warnings of one location, as `pkdb review acknowledge` does."""
        code, file, text = (_text(payload, name) for name in ("code", "file", "text"))
        matches = matching_warnings(
            validate_folder(folder, self._local_vocabulary()).issues,
            code,
            file,
            _line(payload),
            _optional_text(payload, "column"),
        )
        locations = warning_locations(matches)
        if len(locations) != 1:
            named = ", ".join(
                _located(line, column)
                for line, column in sorted(
                    locations, key=lambda at: (at[0] or 0, at[1] or "")
                )
            )
            raise ReviewError(
                f"{len(matches)} warnings [{code}] match in {file} at {named}; give "
                "the line and column of one"
                if matches
                else f"No warning [{code}] in {file} matches"
            )
        item, revision = review_edit.acknowledge(
            folder, author, matches[0], text, revision=revision
        )
        return {
            "revision": revision,
            "item": item.model_dump(mode="json", exclude_none=True),
        }

    def _under_folder_lock[T](self, folder: Path, run: Callable[[Any], T]) -> T:
        """`run(vocabulary)` under the folder lock, as the watcher job syncs; then a rescan."""
        # Chosen before the folder lock, which is never held while waiting for self.lock.
        vocabulary = self._local_vocabulary()
        try:
            with folder_lock(folder):
                return run(vocabulary)
        finally:
            # A sync can have written some files before it failed.
            self._rescan()

    def tables_action(self, identity: str, payload: dict) -> dict:
        """Open the workbook, sync it, resolve its conflicts with `keep`, or add a sheet."""
        # The workbook and the tables record no author, but writes need a user (spec 7.4).
        self.author()
        folder = self.study_folder(identity)
        workbook = workbook_path(folder)
        if workbook.is_symlink():
            # Opening, reading or replacing it would reach outside the study folder.
            raise UnsafeFile(
                f"{workbook.name} is a symlink; replace it with the workbook itself"
            )
        action = payload.get("action")
        if action == "add":
            table, raw = (
                _optional_text(payload, "table"),
                _optional_text(payload, "raw"),
            )
            if (table is None) == (raw is None):
                raise ValueError(
                    "Give the name of a table or the source of a raw table"
                )
            # A raw table is named after the study folder.
            name = table if table is not None else f"{folder.name}_{raw}"
            added = self._under_folder_lock(
                folder, lambda vocabulary: add_table(folder, vocabulary, name)
            )
            synced = (
                _sync_result(added.sync)
                if added.sync is not None
                else {"workbook_action": "unchanged", "changes": [], "conflicts": []}
            )
            issues = [*(added.sync.issues if added.sync else ()), *added.issues]
            kind = "table" if table is not None else "raw table"
            self._record_write(
                identity,
                f"Added {kind} {added.table or name}"
                if added.ok
                else f"Could not add {kind} {name}",
                "succeeded" if added.ok else "failed",
            )
            return {
                **synced,
                "table": added.table,
                "ok": added.ok,
                "issues": _issues(issues),
            }
        if action not in {"open", "sync", "resolve"}:
            raise ValueError(f"Unknown tables action {action!r}")
        keep = payload.get("keep") if action == "resolve" else None
        if action == "resolve" and keep not in {"workbook", "tables"}:
            raise ValueError("Keep the workbook or the tables")
        sync = self._under_folder_lock(
            folder, lambda vocabulary: sync_study(folder, vocabulary, keep=keep)
        )
        result = _sync_result(sync)
        if action == "open":
            # A sync that failed is reported; the curator fixes it in the workbook.
            result["opened"] = sync.workbook.is_file()
            if result["opened"]:
                open_path(sync.workbook)
        done = {
            "open": "Opened the workbook",
            "sync": "Synced the workbook and the tables",
            "resolve": f"Resolved the sync conflicts, keeping the {keep}",
        }[action]
        self._record_write(identity, *_sync_activity(done, sync))
        return result
