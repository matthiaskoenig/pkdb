"""Workspace selection, scanning and file resolution for the curation engine.

Reads and writes engine attributes: lock, scan_lock, root, studies, modes, recent_workspaces,
reference_previews, paused, queue, stop, wakeup, state_dir, _formats. Uses engine methods _save,
_enqueue_one, snapshot, _local_vocabulary and _sync_later.
"""

import json
import os
import time
from collections import Counter
from pathlib import Path
from uuid import uuid4

from pkdb.curation.jobs import fingerprint
from pkdb.curation.metadata import reference_summary
from pkdb.curation.state import EngineState
from pkdb.curation.studies import study_summary
from pkdb.preparation import source_hashes
from pkdb.schemas.validation import StudyValidationError
from pkdb.source_files import ignored_source
from pkdb.studyformat import is_v2_folder
from pkdb.studyformat.sync import workbook_check
from pkdb.studyformat.tables import STUDY_JSON
from pkdb.studyformat.validation import _FORMAT_2_FILES as FORMAT_2_FILES
from pkdb.studyformat.workbook.base import open_lock, workbook_path

RECENT_LIMIT = 10
DIRECTORY_LIMIT = 2000
# A workbook that cannot be planned, or tables that do not load.
UNKNOWN_SYNC = {"status": "unknown", "changes": 0, "conflicts": 0}
# A workbook that neither a job nor a plan checked yet.
NOT_CHECKED_SYNC = {"status": "not_checked", "changes": 0, "conflicts": 0}
# The workbooks that the watcher plans in one tick for rows that no job checks; a few per
# tick keep the start of a large workspace fast.
CHECK_LIMIT = 5


class WorkspaceError(ValueError):
    """A workspace or folder request that the curator can correct."""


def folder_kind(path):
    try:
        if (path / "studies").is_dir():
            return "repository"
        if (path / "study.json").is_file():
            return "study"
    except OSError:
        pass
    return "folder"


class WorkspaceMixin(EngineState):
    def select_workspace(self, path):
        root = self._folder(path, absolute=False)
        if self.state_dir.is_relative_to(root):
            raise WorkspaceError(
                "Application state must be outside the selected source workspace"
            )
        # A running scan finishes first; it would otherwise add rows of the old workspace.
        with self.scan_lock:
            with self.lock:
                if self.active:
                    raise WorkspaceError(
                        "Wait for the current job before changing workspace"
                    )
                self._cancel_pending()
                self.root = root
                self.studies = {}
            self._formats = {}
            self._scan(initial=True)
        with self.lock:
            self.recent_workspaces = [
                str(root),
                *(item for item in self.recent_workspaces if item != str(root)),
            ][:RECENT_LIMIT]
            self._save()
        return self.snapshot()

    def forget_workspace(self, path):
        with self.lock:
            self.recent_workspaces = [
                item for item in self.recent_workspaces if item != path
            ]
            self._save()
        return self.snapshot()

    @staticmethod
    def _folder(path, *, absolute=True):
        requested = Path(path).expanduser()
        if absolute and not requested.is_absolute():
            raise WorkspaceError(f"Enter an absolute folder path: {path}")
        try:
            folder = requested.resolve(strict=True)
        except FileNotFoundError:
            raise WorkspaceError(f"Folder does not exist: {requested}") from None
        except OSError:
            raise WorkspaceError(f"Folder cannot be read: {requested}") from None
        if not folder.is_dir():
            raise WorkspaceError(f"This path is not a folder: {requested}")
        return folder

    def list_directories(self, path=None):
        if path is None:
            path = self.root if self.root.is_dir() else Path.home()
        folder = self._folder(path)
        entries = []
        try:
            with os.scandir(folder) as iterator:
                for entry in iterator:
                    if entry.name.startswith("."):
                        continue
                    try:
                        if not entry.is_dir():
                            continue
                    except OSError:
                        continue
                    entries.append(entry.name)
        except PermissionError:
            raise WorkspaceError(f"Permission denied: {folder}") from None
        except OSError:
            raise WorkspaceError(f"Folder cannot be read: {folder}") from None
        entries.sort(key=lambda name: (name.casefold(), name))
        truncated = len(entries) > DIRECTORY_LIMIT
        entries = entries[:DIRECTORY_LIMIT]
        return {
            "path": str(folder),
            "parent": None if folder.parent == folder else str(folder.parent),
            "home": str(Path.home()),
            "kind": folder_kind(folder),
            "truncated": truncated,
            "entries": [
                {
                    "name": name,
                    "path": str(folder / name),
                    "kind": folder_kind(folder / name),
                }
                for name in entries
            ],
        }

    def _row(self, folder, root):
        identifier = f"{folder.parent.name}/{folder.name}"
        path = folder.relative_to(root).as_posix()
        uploads = [
            job["upload"]
            for job in self.jobs
            if job["study_id"] == identifier and job.get("upload")
        ]
        return {
            "id": identifier,
            "name": folder.name,
            "path": path,
            "duplicate": False,
            "substance": folder.parent.name,
            "mode": "validate",
            "status": "discovered",
            "stale": True,
            "files": [],
            "problems": [],
            "last_upload": uploads[-1] if uploads else None,
            "progress": None,
            "report_id": None,
            "summary": {},
            "reference": None,
            "sync": dict(NOT_CHECKED_SYNC),
            "counts": {"errors": 0, "warnings": 0},
            "_folder": folder,
            "_fingerprint": None,
            "_signature": None,
            "_changed_at": time.monotonic(),
            "_pending": False,
            "_blocked": False,
            # The action of a queued job that pausing canceled, queued again on resume.
            "_resume_action": None,
        }

    def scan(self, initial=False):
        """Scan the workspace for study changes; one scan runs at a time.

        The watcher, jobs, app writes and workspace switches all scan through the scan lock,
        which is never taken while holding the engine lock or a folder lock.
        """
        with self.scan_lock:
            self._scan(initial)

    def _scan(self, initial):
        # A scan of a workspace that was replaced meanwhile stops before it changes a row:
        # its keys and paths are relative to the old root.
        with self.lock:
            root = self.root
        folders = {
            p.parent
            for p in root.rglob("study.json")
            if not p.is_symlink() and not ignored_source(p.relative_to(root))
        }
        with self.lock:
            if self.root is not root:
                return
            folders.update(row["_folder"] for row in self.studies.values())
        format1 = 0
        for folder in sorted(folders):
            key = folder.relative_to(root).as_posix()
            try:
                if folder.is_symlink() or not folder.resolve().is_relative_to(root):
                    continue
                if not self._is_v2(folder):
                    with self.lock:
                        if self.root is not root:
                            return
                        self.studies.pop(key, None)
                    if (folder / "study.json").is_file():
                        format1 += 1
                    continue
                with self.lock:
                    if self.root is not root:
                        return
                    row = self.studies.setdefault(key, self._row(folder, root))
                paths = sorted(
                    p
                    for p in folder.rglob("*")
                    if not ignored_source(p.relative_to(folder))
                )
                files = [
                    (
                        p.relative_to(folder).as_posix(),
                        p.stat().st_size,
                        p.stat().st_mtime_ns,
                    )
                    for p in paths
                    if p.is_file()
                ]
                # Opening or closing the workbook changes its sync status, not the source.
                signature = (files, open_lock(workbook_path(folder)) is not None)
                if signature == row["_signature"]:
                    continue
                hashes = source_hashes(folder)
                digest = fingerprint(hashes)
                summary = study_summary(folder)
                # The initial job of each study syncs it and records the state of its
                # workbook, and the watcher plans the workbooks of the other rows; planning
                # every workbook here would delay each workspace switch.
                sync = dict(NOT_CHECKED_SYNC) if initial else self._sync_state(folder)
                with self.lock:
                    if self.root is not root:
                        return
                    old = row["_fingerprint"]
                    waited = row["status"] == "waiting"
                    was_open = row["_signature"] is not None and row["_signature"][1]
                    closed = was_open and not signature[1]
                    behind = (
                        sync["status"] == "changed"
                        or row["sync"]["status"] == "workbook_open"
                    )
                    row.update(
                        files=[{"id": name, "path": name} for name in hashes],
                        summary=summary,
                        reference=reference_summary(folder),
                    )
                    # Set again below or by the next scheduling while it still applies.
                    row.pop("message", None)
                    # A running job records the state after its sync itself.
                    if row["sync"]["status"] != "syncing":
                        row["sync"] = sync
                    row["_signature"] = signature
                    row["_fingerprint"] = digest
                    if old != digest or waited:
                        row["_changed_at"] = time.monotonic()
                        row["stale"] = True
                        if not row["_blocked"]:
                            row["status"] = "changed" if old else "discovered"
                        # An initial scan validates locally, never uploads a backlog.
                        row["_pending"] = True
                        row["_initial"] = initial or old is None
                        # A new save follows the save action, not a paused job.
                        row["_resume_action"] = None
                    if closed and behind and self.active != row["id"]:
                        # The workbook lacks the tables and is closed now: sync it. A
                        # running job handles a close itself when it ends.
                        self._sync_later(row)
                    for job in self.jobs:
                        if (
                            job.get("study_id") == row["id"]
                            and job.get("status") == "unknown"
                        ):
                            row["_blocked"] = True
                            row["status"] = "unknown"
                    row["mode"] = self.modes.get(self._context(), {}).get(
                        row["id"], "validate"
                    )
            except (OSError, StudyValidationError) as error:
                with self.lock:
                    if self.root is not root:
                        return
                    row = self.studies.setdefault(key, self._row(folder, root))
                    self._wait(row, error)
        with self.lock:
            if self.root is not root:
                return
            self.format1_folders = format1
            self._formats = {
                folder: self._formats[folder]
                for folder in folders
                if folder in self._formats
            }
            counts = Counter(r["id"] for r in self.studies.values())
            for row in self.studies.values():
                row["duplicate"] = counts[row["id"]] > 1

    def _is_v2(self, folder):
        """`is_v2_folder`, decided again only when study.json or a format 2 file changed.

        Only scans call it, one at a time, so the remembered decisions need no lock. The
        inode and the status change time tell a same-size edit that kept the modification
        time, as `cp -p`, `rsync -t` and `tar x` write it.
        """
        try:
            stat = (folder / STUDY_JSON).stat()
        except OSError:
            return is_v2_folder(folder)
        key = (
            stat.st_size,
            stat.st_mtime_ns,
            stat.st_ino,
            stat.st_ctime_ns,
            *(os.path.lexists(folder / name) for name in FORMAT_2_FILES),
        )
        remembered = self._formats.get(folder)
        if remembered is None or remembered[0] != key:
            remembered = self._formats[folder] = (key, is_v2_folder(folder))
        return remembered[1]

    def _wait(self, row, error):
        """Wait for readable source files; the first scan that reads them queues a job again.

        Called with the engine lock held.
        """
        row["status"] = "waiting"
        row["stale"] = True
        row["message"] = (
            "Waiting for readable source files"
            if isinstance(error, OSError)
            else "Symlinked source files are not accepted"
        )
        # Nothing to validate until then; a job now would only fail again.
        row["_pending"] = False
        row["_resume_action"] = None
        # The next scan reads the folder again, also when its files return to the state of
        # the last scan; it queues a job once they can be read.
        row["_signature"] = None

    def _sync_state(self, folder):
        """Whether the workbook and the tables of a folder are in step, as the row shows it.

        Never raises: a workbook that cannot be planned has the status `unknown`.
        """
        state = {"status": "no_workbook", "changes": 0, "conflicts": 0}
        try:
            if not workbook_path(folder).exists():
                return state
            check = workbook_check(folder, self._local_vocabulary())
        except Exception:
            return dict(UNKNOWN_SYNC)
        if check is None:
            return state
        changes, conflicts = len(check["changes"]), check["conflicts"]
        if conflicts:
            status = "conflict"
        elif check["action"] == "close_to_update":
            status = "workbook_open"
        elif not check["ok"]:
            # The tables do not load or the workbook cannot be read.
            status = "unknown"
        elif changes or check["action"] in {"created", "regenerated"}:
            # The tables lack workbook edits, or the workbook lacks the tables.
            status = "changed"
        else:
            status = "in_sync"
        return {"status": status, "changes": changes, "conflicts": conflicts}

    def _watch(self):
        while not self.stop.wait(1):
            try:
                self.scan()
                self.schedule_changes()
                self._check_workbooks()
            except Exception:
                # The watcher retries every second and must outlive any failure; nothing
                # is logged, since errors can carry paths and settings.
                continue

    def _check_workbooks(self, limit=CHECK_LIMIT):
        """Plan the workbooks of rows that are not checked and that no job will check.

        Rows without an initial job, such as rows with the save action Off, duplicates and
        blocked rows, show the state of their workbook this way. The plans run outside the
        engine lock and the folder lock, and a row that a job or a scan checked meanwhile
        keeps the state that they recorded.
        """
        with self.lock:
            root = self.root
            rows = [
                (key, row)
                for key, row in self.studies.items()
                if row["sync"]["status"] == "not_checked" and not self._job_ahead(row)
            ][:limit]
        for key, row in rows:
            sync = self._sync_state(row["_folder"])
            with self.lock:
                if (
                    self.root is root
                    and self.studies.get(key) is row
                    and row["sync"]["status"] == "not_checked"
                ):
                    row["sync"] = sync

    def _job_ahead(self, row):
        """Whether a job of the row is queued or running, or will be once it settles.

        Called with the engine lock held.
        """
        if row["id"] in self.queue or self.active == row["id"]:
            return True
        return (
            row["_pending"]
            and not self.paused
            and self._automatic_action(row) not in {None, "suspended"}
        )

    def _automatic_action(self, row):
        """The action of the job that scheduling queues for a pending row.

        The action of a queued job that pausing canceled, else a validation for an initial
        job, else the save action. None for a row that scheduling skips: blocked, a
        duplicate, or with the save action Off and no canceled job; "suspended" for an
        upload while no authorized account is connected. Called with the engine lock held.
        """
        if row["_blocked"] or row["duplicate"]:
            return None
        action = row["_resume_action"]
        if action is None:
            if row["mode"] == "off":
                return None
            action = "validate" if row.get("_initial") else row["mode"]
        if action == "upload" and (
            self.offline or not self.account or not self.can_upload
        ):
            return "suspended"
        return action

    def schedule_changes(self):
        with self.lock:
            if self.paused:
                return
            for row in self.studies.values():
                if not row["_pending"] or time.monotonic() - row["_changed_at"] < 1:
                    continue
                action = self._automatic_action(row)
                if action == "suspended":
                    row["message"] = (
                        "Upload on save suspended: connect an authorized account"
                    )
                if action in {None, "suspended"} or self.active == row["id"]:
                    continue
                row["_pending"] = False
                row["_initial"] = False
                self._enqueue_one(row, action, automatic=True)

    def resolve_file(self, study_id, file=None):
        with self.lock:
            row = self._selected([study_id])[0]
            folder = row["_folder"]
            if not is_v2_folder(folder):
                raise ValueError("The folder is no longer a study format 2 folder")
            if file is None:
                target = folder
            else:
                # Diagnostics often contain a basename; resolve only a unique registered file.
                names = [entry["path"] for entry in row["files"]]
                matches = [
                    name for name in names if name == file or Path(name).name == file
                ]
                if len(matches) != 1:
                    raise ValueError("Choose a registered, unambiguous source file")
                target = folder / matches[0]
            for part in (target, *target.parents):
                if part == self.root.parent:
                    break
                if part.is_symlink():
                    raise ValueError("Symlinks cannot be opened")
            if target.is_file() and target.suffix.lower() not in {
                ".json",
                ".xlsx",
                ".xls",
                ".csv",
                ".tsv",
                ".txt",
                ".md",
                ".pdf",
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
                ".tif",
                ".tiff",
                ".ods",
            }:
                raise ValueError(
                    "This file type cannot be opened by the curation app; reveal its folder instead"
                )
            resolved = target.resolve(strict=True)
            if not resolved.is_relative_to(self.root) or not resolved.is_relative_to(
                folder
            ):
                raise ValueError("File is outside the workspace")
            return resolved

    def reference_action(self, action, body):
        from pkdb.references import (
            ReferenceError,
            ReferenceResolver,
            preview_reference,
            save_reference,
        )

        with self.lock:
            folder = self.resolve_file(body["id"])
            workspace = self.root
            offline = self.offline
            if action == "read":
                path = folder / "reference.json"
                if path.is_symlink():
                    raise ReferenceError("Reference source must not be a symlink")
                return {
                    "reference": json.loads(path.read_text()) if path.exists() else {}
                }
            if action == "save":
                token = body["token"]
                entry = self.reference_previews.get(token)
                if not entry or entry[0] != folder:
                    raise ReferenceError("Reference preview expired; preview again")
                save_reference(folder, entry[1])
                del self.reference_previews[token]
        if action == "save":
            # The scan lock is never taken while holding the engine lock.
            self.scan()
            return {"ok": True}
        resolver = ReferenceResolver(
            offline=offline, refresh=body.get("refresh", False)
        )
        if action == "search":
            return {"candidates": resolver.search(body["citation"])}
        if action != "preview":
            raise ReferenceError("Unknown reference action")
        preview = preview_reference(
            folder,
            body.get("input", {}),
            resolver,
            reset_overrides=body.get("reset_overrides", False),
        )
        with self.lock:
            if self.root != workspace or self.resolve_file(body["id"]) != folder:
                raise ReferenceError("Workspace changed during lookup; preview again")
            token = uuid4().hex
            while len(self.reference_previews) >= 20:
                self.reference_previews.pop(next(iter(self.reference_previews)))
            self.reference_previews[token] = (folder, preview)
        return {**preview, "token": token}
