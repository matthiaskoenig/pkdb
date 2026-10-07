"""Serialized scientific jobs of the curation engine.

Reads and writes engine attributes: lock, jobs, queue, active, studies, modes, paused, stop,
wakeup, api_key, account, can_upload, offline, endpoint, cache, vocabulary, root. Uses engine
methods _save, snapshot, _context, _connection_status, connect, scan, _sync_state and _wait.
"""

import hashlib
import json
import os
import time
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pkdb.cache import (
    atomic_json,
    bundled_vocabulary,
)
from pkdb.client import Client
from pkdb.curation.state import EngineState
from pkdb.curation.studies import AmbiguousStudy
from pkdb.domain.validation import PROCESSING_VERSION
from pkdb.domain.vocabulary import vocabulary_hash
from pkdb.errors import ClientError, CompatibilityError, SourceChangedError
from pkdb.preparation import prepare, source_hashes
from pkdb.schemas.validation import StudyValidationError, ValidationReport
from pkdb.studyformat import is_v2_folder
from pkdb.studyformat.pipeline import PipelineResult, sync_and_format
from pkdb.studyformat.revision import folder_lock
from pkdb.studyformat.sync import conflict_data
from pkdb.studyformat.workbook.base import open_lock, workbook_path


def now():
    return datetime.now(UTC).isoformat()


def duplicate_message(identifier):
    return f"Rename one of the folders with identity {identifier} before uploading"


def fingerprint(hashes):
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def describe(pipeline: PipelineResult) -> str | None:
    """The table files that the pipeline wrote and removed, in words, as pkdb upload says it."""
    from pkdb.batch import _described

    synced = {change.file: change for sync in pipeline.syncs for change in sync.changes}
    formatted = pipeline.formatted.changes if pipeline.formatted else []
    parts = [
        *_described(
            list(synced.values()),
            "wrote {} from the workbook",
            "removed {}, which the workbook no longer holds",
        ),
        *_described(formatted, "formatted {}", "removed {} without rows"),
    ]
    text = "; ".join(parts)
    return text[0].upper() + text[1:] if text else None


def issue_counts(report: dict) -> dict:
    """The errors and warnings of a report, from its counts when it has them."""
    issues = report.get("issues", [])
    return {
        "errors": report.get(
            "error_count", sum(issue.get("severity") == "error" for issue in issues)
        ),
        "warnings": report.get(
            "warning_count", sum(issue.get("severity") == "warning" for issue in issues)
        ),
    }


def conflict_entries(pipeline: PipelineResult) -> list[dict]:
    """The conflicts of the last sync, as pkdb tables sync lists them."""
    return [conflict_data(conflict) for conflict in pipeline.syncs[-1].conflicts]


def stamp(path: Path) -> tuple[int, int] | None:
    """The size and modification time of a file, which a save changes; None when missing."""
    try:
        status = path.stat()
    except OSError:
        return None
    return status.st_size, status.st_mtime_ns


def sync_state(pipeline: PipelineResult) -> dict:
    """The sync status of a row after the pipeline, from its last sync.

    It is the status that a plan of the workbook would give right after the sync, without
    reading the workbook again.
    """
    if not pipeline.syncs:
        return {"status": "no_workbook", "changes": 0, "conflicts": 0}
    last = pipeline.syncs[-1]
    conflicts = len(last.conflicts)
    if conflicts:
        status = "conflict"
    elif last.workbook_action == "close_to_update":
        # Also when replacing the workbook failed although no lock file shows it open.
        status = "workbook_open"
    elif last.workbook_action == "sync_again":
        # The tables lack the save of the workbook during the sync.
        status = "changed"
    elif not last.ok:
        status = "unknown"
    else:
        status = "in_sync"
    return {"status": status, "changes": 0, "conflicts": conflicts}


def stop_message(pipeline: PipelineResult) -> str:
    """Why a sync stopped the pipeline before validation, with conflicts or a later save."""
    if pipeline.stopped == "saved_again":
        return "The workbook was saved during the sync; its last save is not in the tables yet"
    return "Resolve the conflict between the workbook and the tables"


class JobsMixin(EngineState):
    def _enqueue_one(self, row, action, automatic=False):
        if row["_blocked"]:
            raise ValueError("Reconcile the unknown upload before starting another job")
        if row["duplicate"] and action == "upload":
            raise ValueError(duplicate_message(row["id"]))
        if action == "upload" and (
            self.offline or not self.endpoint or not self.api_key
        ):
            raise ValueError("Upload requires a connected endpoint and API key")
        existing = self.queue.get(row["id"])
        if existing:
            existing["status"] = "canceled"
        job = {
            "id": uuid4().hex,
            "study_id": row["id"],
            # Keeps activity readable after switching to another workspace.
            "study_name": row["name"],
            "action": action,
            "status": "queued",
            "stage": "queued",
            "created_at": now(),
            "message": "Queued",
            "automatic": automatic,
            "endpoint": self.endpoint,
            "persistence": "not_attempted",
            "report_id": None,
        }
        self._remember(job)
        self.queue[row["id"]] = job
        row["_pending"] = False
        row["_initial"] = False
        row["status"] = "queued"
        self._save()
        self.wakeup.set()
        return job

    def _remember(self, job):
        """Add a job to the history, which keeps the last 100 finished jobs."""
        self.jobs.append(job)
        protected = [
            j for j in self.jobs if j["status"] in {"queued", "running", "unknown"}
        ]
        finished = [j for j in self.jobs if j not in protected][-100:]
        self.jobs = sorted(protected + finished, key=lambda j: j["created_at"])

    def _record_write(self, identity, message, status="succeeded"):
        """List a write of the app in the activity of the study; it starts nothing."""
        with self.lock:
            self._remember(
                {
                    "id": uuid4().hex,
                    "study_id": identity,
                    "study_name": identity.rsplit("/", 1)[-1],
                    "action": "write",
                    "status": status,
                    "created_at": now(),
                    "message": message,
                    "automatic": False,
                    "report_id": None,
                }
            )
            self._save()

    def enqueue(self, ids, action):
        if action not in {"validate", "validate_remote", "upload"}:
            raise ValueError("Choose validate or upload")
        with self.lock:
            rows = self._selected(ids)
            if any(row["_blocked"] for row in rows):
                raise ValueError("Reconcile unknown uploads first")
            for row in rows:
                if action == "upload" and row["duplicate"]:
                    raise ValueError(duplicate_message(row["id"]))
            if action in {"upload", "validate_remote"} and (
                self.offline or not self.endpoint or not self.api_key
            ):
                raise ValueError(
                    "Remote actions require a connected endpoint and API key"
                )
            result = [self._enqueue_one(row, action) for row in rows]
        return result

    def _selected(self, ids):
        if not isinstance(ids, list) or not ids or len(ids) > 1000:
            raise ValueError("Select between 1 and 1000 studies")
        if any(not isinstance(identifier, str) for identifier in ids):
            raise ValueError("Study is not in this workspace")
        rows = []
        for identifier in dict.fromkeys(ids):
            matches = [row for row in self.studies.values() if row["id"] == identifier]
            if not matches:
                raise ValueError("Study is not in this workspace")
            if len(matches) > 1:
                raise AmbiguousStudy(identifier, [row["path"] for row in matches])
            rows.append(matches[0])
        return rows

    def _row_of(self, identifier):
        return next(
            (row for row in self.studies.values() if row["id"] == identifier), None
        )

    def set_mode(self, ids, mode):
        if mode not in {"validate", "upload", "off"}:
            raise ValueError("Unknown save action")
        with self.lock:
            if mode == "upload" and (
                self.offline or not self.account or not self.can_upload
            ):
                raise ValueError(
                    "Connect an authorized PK-DB account before enabling uploads on save"
                )
            for row in self._selected(ids):
                row["mode"] = mode
                row["_pending"] = False  # Mode changes are not saves.
                self.modes.setdefault(self._context(), {})[row["id"]] = mode
            self._save()
        return self.snapshot()

    def _cancel_pending(self):
        for job in self.queue.values():
            job["status"] = "canceled"
        self.queue.clear()

    def set_paused(self, paused):
        with self.lock:
            self.paused = bool(paused)
            if paused:
                for identifier in self.queue:
                    if row := self._row_of(identifier):
                        row["_pending"] = True
                self._cancel_pending()
            self._save()
        self.wakeup.set()
        return self.snapshot()

    def report(self, identifier):
        if not any(job["report_id"] == identifier for job in self.jobs):
            raise ValueError("Unknown report")
        return json.loads(
            (self.state_dir / "reports" / f"{identifier}.json").read_text()
        )

    def _worker(self):
        while not self.stop.is_set():
            self.wakeup.wait(1)
            self.wakeup.clear()
            while not self.stop.is_set():
                with self.lock:
                    if not self.queue or self.paused:
                        break
                    identifier = next(iter(self.queue))
                    job = self.queue.pop(identifier)
                    self.active = identifier
                    job["status"] = "running"
                try:
                    self.run_job(job)
                finally:
                    with self.lock:
                        self.active = None
                        self._save()

    def _sync_later(self, row):
        """Queue a validation whose sync regenerates the closed workbook; it needs no upload.

        A pending or queued job of the study syncs, and so regenerates, the workbook itself.
        """
        if row["_pending"] or row["id"] in self.queue:
            return
        # An initial job only validates, whatever the save action of the study.
        row.update(_pending=True, _initial=True, _changed_at=time.monotonic())

    def _local_vocabulary(self):
        """The vocabulary of local work: the cached one of the endpoint, else the bundled one."""
        with self.lock:
            endpoint = self.endpoint
        if endpoint:
            try:
                return self.cache.load(endpoint)
            except OSError, ValueError:
                pass
        return bundled_vocabulary()

    def _server_validate(self, client, prepared):
        with prepared.source() as source, ExitStack() as stack:
            parts = source.parts(stack)
            headers = {
                **client._headers(required=True),
                "X-PKDB-Report-Version": "2",
                "X-PKDB-Vocabulary-Hash": prepared.vocabulary_hash,
                "X-PKDB-Processing-Version": PROCESSING_VERSION,
            }
            return client._request(
                "POST", source.validation_path, headers=headers, files=parts
            ).json()

    def run_job(self, job):
        from pkdb.references import ReferenceError, ReferenceResolver, sync_reference

        with self.lock:
            row = self._row_of(job["study_id"])
            if row is None:
                job.update(status="canceled", message="Study is not in this workspace")
                self._save()
                return
            if not is_v2_folder(row["_folder"]):
                job.update(
                    status="canceled",
                    message="The folder is no longer a study format 2 folder",
                )
                self._save()
                return
            if job["action"] == "upload" and row["duplicate"]:
                job.update(status="canceled", message=duplicate_message(row["id"]))
                self._save()
                return
            if row["_blocked"]:
                job.update(
                    status="canceled",
                    message="A previous upload has an unknown outcome; reconcile it first",
                )
                self._save()
                return
        expected = row["_fingerprint"]
        outcome = {"persistence": "not_attempted", "report": {"issues": []}}
        workbook = workbook_path(row["_folder"])
        # A lock file of the workbook at the start or in the sync: closing it during
        # this job, which scans skip, is handled when the job ends.
        was_open = open_lock(workbook) is not None

        def progress(event):
            with self.lock:
                job["stage"] = event.stage
                row["progress"] = {
                    "stage": event.stage,
                    "completed": event.completed,
                    "total": event.total,
                }
                row["status"] = (
                    "uploading"
                    if event.stage in {"transfer", "response", "commit"}
                    else "validating"
                )
                if event.stage == "transfer":
                    # Persist before a potentially ambiguous write for restart recovery.
                    self._save()

        try:
            with self.lock:
                row["status"] = "validating"
            # The reference is written before the source of this job is fixed below; a
            # failed lookup is reported after the sync, which needs no reference.
            try:
                change = sync_reference(
                    row["_folder"], ReferenceResolver(offline=self.offline)
                )
                reference_error = None
            except ReferenceError as error:
                change, reference_error = None, error
            if change:
                outcome["reference_updated"] = change
            # Chosen before the folder lock, which is never held while waiting for self.lock.
            local = self._local_vocabulary()
            with self.lock:
                row["sync"] = {**row["sync"], "status": "syncing"}
            stamps = {}

            def stage(name):
                if name == "format":
                    # The workbook as the sync left it; a later save is not in the tables.
                    stamps["format"] = stamp(workbook)

            pipeline, saved_after_sync = None, False
            try:
                # App writes take the same lock, so the formatter never overwrites one.
                with folder_lock(row["_folder"]):
                    pipeline = sync_and_format(row["_folder"], local, on_stage=stage)
                    # The source this job validates; any later save belongs to the next job.
                    synced_source = fingerprint(source_hashes(row["_folder"]))
                    saved_after_sync = (
                        "format" in stamps and stamp(workbook) != stamps["format"]
                    )
            finally:
                # The last sync tells the state of the workbook, unless the pipeline failed
                # or the workbook was saved after the sync; then a plan, which never raises.
                synced = (
                    sync_state(pipeline)
                    if pipeline is not None and not saved_after_sync
                    else self._sync_state(row["_folder"])
                )
                with self.lock:
                    row["sync"] = synced
            last = pipeline.syncs[-1] if pipeline.syncs else None
            was_open = was_open or (last is not None and last.lock is not None)
            outcome["pipeline_issues"] = [
                issue.model_dump(mode="json") for issue in pipeline.issues
            ]
            if tables := describe(pipeline):
                outcome["tables_updated"] = tables
            if pipeline.stopped == "sync" and not pipeline.syncs[-1].conflicts:
                # Tables that do not load or a workbook that cannot be read are reported
                # like validation problems.
                raise StudyValidationError(
                    ValidationReport(issues=list(pipeline.issues))
                )
            if pipeline.stopped in {"sync", "saved_again"}:
                outcome["conflicts"] = conflict_entries(pipeline)
                # The conflicts count as problems of the study, as the sync reports them.
                outcome["report"] = ValidationReport(
                    issues=list(pipeline.issues)
                ).model_dump(mode="json")
                job.update(status="conflict", message=stop_message(pipeline))
                row.update(status="conflict", stale=True)
                return  # The finally block writes the report.
            if synced_source != expected:
                # Outside the engine lock, which the scan takes for each row.
                self.scan()
                with self.lock:
                    # This job validates the repaired source; a save after it stays pending.
                    row.update(
                        status="validating",
                        _pending=row["_fingerprint"] != synced_source,
                    )
                expected = synced_source
            if saved_after_sync:
                # The workbook was saved after the sync read it, so the tables are stale. A
                # save after the folder lock changes the source that the checks below expect.
                raise SourceChangedError("A workbook save superseded this validation")
            if reference_error is not None:
                raise reference_error
            if pipeline.stopped == "format":
                # Tables that cannot be formatted are reported like validation problems.
                raise StudyValidationError(
                    ValidationReport(issues=list(pipeline.issues))
                )
            with Client(
                job["endpoint"] or "http://localhost",
                api_key=self.api_key,
                cache=self.cache,
                progress=progress,
            ) as client:
                if self.offline or not job["endpoint"]:
                    vocabulary = local
                else:
                    vocabulary = self._vocabulary(client)
                prepared = prepare(
                    row["_folder"], vocabulary=vocabulary, progress=progress
                )
                if (
                    fingerprint(dict(prepared.file_hashes)) != expected
                    or fingerprint(source_hashes(row["_folder"])) != expected
                ):
                    raise SourceChangedError("A newer save superseded this validation")
                outcome.update(
                    report=prepared.report.model_dump(mode="json"),
                    source_fingerprint=expected,
                    vocabulary_hash=prepared.vocabulary_hash,
                    processing_version=PROCESSING_VERSION,
                    source_digest=prepared.study.source_digest,
                    sid=prepared.study.sid,
                )
                job.update(
                    source_digest=prepared.study.source_digest, sid=prepared.study.sid
                )
                if job["action"] == "validate_remote":
                    if self.offline or not job["endpoint"]:
                        raise ValueError(
                            "Server validation requires a connected endpoint"
                        )
                    remote = self._server_validate(client, prepared)
                    outcome.update(
                        server_report=remote,
                        report=remote.get("report", outcome["report"]),
                    )
                if job["action"] == "upload":
                    if self.paused or self.stop.is_set():
                        raise SourceChangedError("Upload paused before transfer")
                    try:
                        result = client.upload(prepared)
                    except CompatibilityError as error:
                        if error.persistence not in {"not_attempted", "not_saved"}:
                            raise
                        refreshed = self._vocabulary(client)
                        if vocabulary_hash(refreshed) == prepared.vocabulary_hash:
                            raise
                        prepared = prepare(
                            row["_folder"], vocabulary=refreshed, progress=progress
                        )
                        if (
                            fingerprint(dict(prepared.file_hashes)) != expected
                            or fingerprint(source_hashes(row["_folder"])) != expected
                            or self.paused
                            or self.stop.is_set()
                        ):
                            raise SourceChangedError(
                                "Source changed or upload paused"
                            ) from error
                        outcome.update(
                            report=prepared.report.model_dump(mode="json"),
                            vocabulary_hash=prepared.vocabulary_hash,
                            source_digest=prepared.study.source_digest,
                            sid=prepared.study.sid,
                        )
                        job.update(
                            source_digest=prepared.study.source_digest,
                            sid=prepared.study.sid,
                        )
                        # Exactly one retry, only when the previous attempt could not save.
                        result = client.upload(prepared)
                    outcome.update(
                        result=result.model_dump(mode="json"),
                        persistence="created" if result.created else "replaced",
                        server_report=client.last_upload_report,
                    )
                    row["last_upload"] = {
                        "persistence": outcome["persistence"],
                        "at": now(),
                        "endpoint": job["endpoint"],
                        "url": result.url,
                    }
                    # Jobs persist, so the outcome survives restarts of the local service.
                    job["upload"] = row["last_upload"]
                job.update(
                    status="succeeded",
                    message="Uploaded"
                    if job["action"] == "upload"
                    else "Validation passed",
                )
                row["status"] = "valid"
                row["stale"] = fingerprint(source_hashes(row["_folder"])) != expected
                if row["stale"]:
                    row["status"] = "changed"
        except SourceChangedError:
            job.update(
                status="canceled",
                message="Source changed or paused; latest revision remains pending",
            )
            row.update(status="changed", stale=True)
            row["_pending"] = True
            row["_changed_at"] = time.monotonic()
        except StudyValidationError as error:
            outcome["report"] = error.report.model_dump(mode="json")
            try:
                current = fingerprint(source_hashes(row["_folder"])) == expected
            except (OSError, StudyValidationError) as unreadable:
                # A symlink or an unreadable file: the first scan that reads the files
                # queues a job again, instead of a new job every second.
                job.update(
                    status="failed",
                    message="Could not read the source files; see the study",
                )
                with self.lock:
                    self._wait(row, unreadable)
            else:
                job.update(
                    status="failed" if current else "canceled",
                    message="Validation found problems"
                    if current
                    else "Source changed; diagnostics belong to a previous save",
                )
                row.update(
                    status="invalid" if current else "changed", stale=not current
                )
                if not current:
                    row["_pending"] = True
                    row["_changed_at"] = time.monotonic()
        except ReferenceError as error:
            job.update(status="failed", message=self._safe(str(error)))
            row.update(status="failed", stale=True)
        except ClientError as error:
            if job["action"] != "upload":
                error.persistence = "not_attempted"
            outcome.update(persistence=error.persistence, request_id=error.request_id)
            if error.report:
                outcome["report"] = error.report.model_dump(mode="json")
            job.update(
                status="unknown" if error.persistence == "unknown" else "failed",
                message=self._safe(str(error)),
            )
            row["status"] = job["status"]
            if job["action"] == "upload" and error.persistence == "unknown":
                row["_blocked"] = True
            if (
                error.status_code in {401, 403}
                or isinstance(error, CompatibilityError)
                or error.report is None
            ):
                self.paused = True
        except OSError, ValueError:
            job.update(
                status="failed",
                message="Could not read or validate source files; check paths and saved contents",
            )
            row.update(status="failed", stale=True)
        except Exception:
            uncertain = (
                job["action"] == "upload"
                and job.get("stage") in {"transfer", "upload", "response", "commit"}
                and outcome["persistence"] not in {"created", "replaced"}
            )
            job.update(
                status="unknown" if uncertain else "failed",
                message="Unexpected job failure; inspect the report before retrying",
            )
            if uncertain:
                outcome["persistence"] = "unknown"
            row["_blocked"] = uncertain
            row["status"] = job["status"]
        finally:
            with self.lock:
                if (
                    was_open
                    and open_lock(workbook) is None
                    and row["sync"]["status"] in {"changed", "workbook_open"}
                ):
                    # The workbook lacks the tables and was closed during this job.
                    self._sync_later(row)
                job["persistence"] = outcome["persistence"]
                job["report_id"] = job["id"]
                outcome.update(job=job.copy(), endpoint=job["endpoint"])
                (self.state_dir / "reports").mkdir(exist_ok=True)
                atomic_json(
                    self.state_dir / "reports" / f"{job['id']}.json",
                    json.loads(self._safe(json.dumps(outcome))),
                )
                row["report_id"] = job["id"]
                row["problems"] = json.loads(
                    self._safe(json.dumps(outcome["report"].get("issues", [])))
                )
                row["counts"] = issue_counts(outcome["report"])
                row["report_complete"] = outcome["report"].get("complete", True)
                row["report_truncated"] = outcome["report"].get("truncated", False)
                row["report_incomplete"] = (
                    row["report_truncated"] or not row["report_complete"]
                )
                row["progress"] = None
                self._save()

    def _safe(self, value):
        for secret in (self.api_key, os.environ.get("GH_TOKEN")):
            if secret:
                value = value.replace(secret, "[redacted]")
        return value

    def resume(self, ids=None):
        with self.lock:
            rows = self._selected(ids) if ids else list(self.studies.values())
        for row in rows:
            if not row["_blocked"]:
                continue
            job = next(
                j
                for j in reversed(self.jobs)
                if j["study_id"] == row["id"] and j["status"] == "unknown"
            )
            if (
                self.offline
                or job["endpoint"] != self.endpoint
                or not job.get("source_digest")
            ):
                raise ValueError(
                    "Inspect the original server before retrying the unknown upload"
                )
            with Client(self.endpoint, api_key=self.api_key) as client:
                publication = client.publication(job["sid"]).model_dump()
            if publication.get("digest") != job["source_digest"]:
                raise ValueError(
                    "Server publication differs; outcome cannot be established automatically"
                )
            job.update(
                status="succeeded",
                persistence="reconciled",
                message="Server publication matches the attempted snapshot",
            )
            row["_blocked"] = False
            row["status"] = "changed"
        return self.set_paused(False)

    def cancel_jobs(self, ids):
        if not isinstance(ids, list):
            raise ValueError("Select queued jobs")
        with self.lock:
            for identifier, job in list(self.queue.items()):
                if job["id"] in ids:
                    job.update(status="canceled", message="Canceled before starting")
                    self.queue.pop(identifier)
                    if row := self._row_of(identifier):
                        row["_pending"] = False
                        row["status"] = "changed"
            self._save()
        return self.snapshot()

    def clear_history(self):
        with self.lock:
            self.jobs = [
                j for j in self.jobs if j["status"] in {"queued", "running", "unknown"}
            ]
            keep = {j["report_id"] for j in self.jobs if j.get("report_id")}
            for path in (self.state_dir / "reports").glob("*.json"):
                if path.stem not in keep:
                    path.unlink(missing_ok=True)
            for row in self.studies.values():
                if row["report_id"] not in keep:
                    row["report_id"] = None
            self._save()
        return self.snapshot()

    def retry_unknown(self, identifier, acknowledge_unknown=False):
        if acknowledge_unknown is not True:
            raise ValueError(
                "Inspect the server and explicitly acknowledge the uncertain outcome first"
            )
        with self.lock:
            if self.active or self.offline or not self.account or not self.can_upload:
                raise ValueError(
                    "Connect an authorized account and wait for the current operation"
                )
            row = self._selected([identifier])[0]
            unknown = [
                j
                for j in self.jobs
                if j["study_id"] == identifier and j["status"] == "unknown"
            ]
            if not unknown or any(j["endpoint"] != self.endpoint for j in unknown):
                raise ValueError("Retry must target the original server")
            if row["duplicate"] or not self.endpoint or not self.api_key:
                raise ValueError(
                    duplicate_message(identifier)
                    if row["duplicate"]
                    else "Connect an API key first"
                )
            # Preserve the historical unknown persistence rather than pretending it failed.
            for job in unknown:
                job.update(
                    status="reviewed",
                    message="User inspected the server and requested a new upload",
                )
            row["_blocked"] = False
            self.paused = False
            self._enqueue_one(row, "upload")
        return self.snapshot()
