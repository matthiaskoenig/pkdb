"""Persistent local workspace, settled file watching, and serialized scientific jobs."""

import hashlib
import json
import os
import threading
import time
from collections import Counter
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from pkdb.cache import (
    VocabularyCache,
    atomic_json,
    bundled_vocabulary,
    cache_directory,
    endpoint_root,
)
from pkdb.client import Client
from pkdb.curation.github import GitHubAssignments
from pkdb.domain.validation import PROCESSING_VERSION
from pkdb.domain.vocabulary import vocabulary_hash
from pkdb.errors import ClientError, CompatibilityError, SourceChangedError
from pkdb.preparation import prepare, source_hashes
from pkdb.schemas.validation import StudyValidationError
from pkdb.source_files import ignored_source


def now():
    return datetime.now(UTC).isoformat()


def fingerprint(hashes):
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


class CurationEngine:
    def __init__(
        self,
        path=None,
        endpoint=None,
        github_user=None,
        repository=None,
        offline=False,
        state_dir=None,
        api_key=None,
        start=True,
    ):
        self.lock = threading.RLock()
        self._connection_generation = 0
        self.stop = threading.Event()
        self.wakeup = threading.Event()
        self.state_dir = (
            Path(state_dir or cache_directory() / "curation").expanduser().resolve()
        )
        self.state_dir.mkdir(parents=True, exist_ok=True)
        try:
            saved = json.loads((self.state_dir / "state.json").read_text())
        except OSError, ValueError:
            saved = {}
        self.api_key = api_key or os.environ.get("PKDB_API_KEY")
        self.endpoint = (
            endpoint_root(str(endpoint or saved.get("endpoint")))
            if (endpoint or saved.get("endpoint"))
            else ""
        )
        self.offline = offline
        self.github_user = github_user or saved.get("github_user", "")
        self.repository = (
            repository or saved.get("repository") or "matthiaskoenig/pkdb_data"
        )
        self.github = GitHubAssignments(
            self.repository,
            os.environ.get("GH_TOKEN"),
            saved.get("github") if saved.get("repository") == self.repository else None,
        )
        self.account = None
        self.can_upload = False
        self.connection_error = None
        self.vocabulary = {"status": "offline" if offline else "not_checked"}
        self.cache = VocabularyCache(self.state_dir / "vocabulary")
        self.studies = {}
        self.jobs = saved.get("jobs", [])
        for job in self.jobs:
            if job.get("status") in {"queued", "running"}:
                job["status"] = (
                    "unknown"
                    if job.get("action") == "upload"
                    and job.get("stage") in {"transfer", "upload", "response", "commit"}
                    else "canceled"
                )
                if job["status"] == "unknown":
                    job["persistence"] = "unknown"
                job["message"] = (
                    "Interrupted by previous shutdown; inspect before retrying"
                )
        self.modes = saved.get("modes", {})
        self.mappings = saved.get("mappings", {})
        self.paused = False
        self.active = None
        self.queue = {}
        self.root = Path.cwd()
        self.threads = []
        default_workspace = next(
            (
                candidate
                for candidate in (Path.cwd(), *Path.cwd().parents)
                if (candidate / "studies").is_dir()
            ),
            Path.cwd(),
        )
        self.select_workspace(path or saved.get("workspace") or default_workspace)
        if start:
            for target in (self._watch, self._worker, self._connect):
                thread = threading.Thread(target=target, daemon=True)
                self.threads.append(thread)
                thread.start()

    def _save(self):
        atomic_json(
            self.state_dir / "state.json",
            {
                "workspace": str(self.root),
                "endpoint": self.endpoint,
                "github_user": self.github_user,
                "repository": self.repository,
                "github": self.github.data,
                "modes": self.modes,
                "mappings": self.mappings,
                "jobs": self.jobs,
            },
        )

    def _context(self):
        return f"{self.root}|{self.endpoint}|{self.account or ''}"

    def snapshot(self):
        with self.lock:
            issues = []
            for raw in self.github.data.get("issues", []):
                issue = dict(raw)
                mapped = self.mappings.get(f"{self.repository}#{raw['number']}")
                title = raw["title"].strip().replace("\\", "/")
                candidates = [
                    row["id"]
                    for row in self.studies.values()
                    if row["path"] == title
                    or row["path"] == f"studies/{title}"
                    or (row["_folder"].parent.name + "/" + row["_folder"].name) == title
                ]
                issue["study_ids"] = (
                    [
                        r["id"]
                        for r in self.studies.values()
                        if str(r["_folder"]) in mapped
                    ]
                    if mapped is not None
                    else candidates
                    if len(candidates) == 1
                    else []
                )
                issues.append(issue)
            return json.loads(
                json.dumps(
                    {
                        "workspace": str(self.root),
                        "endpoint": self.endpoint,
                        "account": self.account,
                        "can_upload": self.can_upload,
                        "connection_error": self.connection_error,
                        "offline": self.offline,
                        "paused": self.paused,
                        "vocabulary": self.vocabulary,
                        "github": {
                            **self.github.data,
                            "user": self.github_user,
                            "repository": self.repository,
                            "issues": issues,
                        },
                        "studies": [
                            {k: v for k, v in row.items() if not k.startswith("_")}
                            for row in self.studies.values()
                        ],
                        "jobs": self.jobs,
                    }
                )
            )

    def select_workspace(self, path):
        root = Path(path).expanduser().resolve(strict=True)
        if not root.is_dir():
            raise ValueError("Choose a directory")
        if self.state_dir.is_relative_to(root):
            raise ValueError(
                "Application state must be outside the selected source workspace"
            )
        with self.lock:
            if self.active:
                raise ValueError("Wait for the current job before changing workspace")
            self._cancel_pending()
            self.root = root
            self.studies = {}
        self.scan(initial=True)
        with self.lock:
            self._save()
        return self.snapshot()

    def _row(self, folder):
        identifier = hashlib.sha256(str(folder).encode()).hexdigest()[:20]
        path = folder.relative_to(self.root).as_posix()
        return {
            "id": identifier,
            "name": folder.name,
            "sid": None,
            "path": path,
            "substance": folder.parent.name,
            "mode": "validate",
            "status": "discovered",
            "stale": True,
            "files": [],
            "problems": [],
            "last_upload": None,
            "progress": None,
            "report_id": None,
            "attribution": {},
            "_folder": folder,
            "_fingerprint": None,
            "_signature": None,
            "_changed_at": time.monotonic(),
            "_pending": False,
            "_blocked": False,
        }

    def scan(self, initial=False):
        root = self.root
        folders = {
            p.parent
            for p in root.rglob("study.json")
            if not p.is_symlink() and not ignored_source(p.relative_to(root))
        }
        with self.lock:
            folders.update(row["_folder"] for row in self.studies.values())
        for folder in sorted(folders):
            try:
                if folder.is_symlink() or not folder.resolve().is_relative_to(root):
                    continue
                with self.lock:
                    row = self.studies.setdefault(
                        self._row(folder)["id"], self._row(folder)
                    )
                paths = sorted(
                    p
                    for p in folder.rglob("*")
                    if not ignored_source(p.relative_to(folder))
                )
                signature = [
                    (
                        p.relative_to(folder).as_posix(),
                        p.stat().st_size,
                        p.stat().st_mtime_ns,
                    )
                    for p in paths
                    if p.is_file()
                ]
                if signature == row["_signature"]:
                    continue
                hashes = source_hashes(folder)
                digest = fingerprint(hashes)
                try:
                    metadata = json.loads((folder / "study.json").read_text())
                    if not isinstance(metadata, dict):
                        metadata = {}
                except ValueError, OSError:
                    metadata = {}
                with self.lock:
                    old = row["_fingerprint"]
                    if row["sid"] and row["sid"] != metadata.get("sid"):
                        row["identity_changed"] = True
                        row["message"] = (
                            "Study identity changed; choose upload mode again after reviewing it"
                        )
                    row.update(
                        name=metadata.get("name") or folder.name,
                        sid=metadata.get("sid"),
                        files=[{"id": name, "path": name} for name in hashes],
                        attribution={
                            k: metadata.get(k) for k in ("creator", "curators")
                        },
                    )
                    row["_signature"] = signature
                    row["_fingerprint"] = digest
                    if old != digest:
                        row["_changed_at"] = time.monotonic()
                        row["stale"] = True
                        if not row["_blocked"]:
                            row["status"] = "changed" if old else "discovered"
                        # An initial scan validates locally, never uploads a backlog.
                        row["_pending"] = True
                        row["_initial"] = initial or old is None
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
                    row = self.studies.setdefault(
                        self._row(folder)["id"], self._row(folder)
                    )
                    row["status"] = "waiting"
                    row["stale"] = True
                    row["message"] = (
                        "Waiting for readable source files"
                        if isinstance(error, OSError)
                        else "Symlinked source files are not accepted"
                    )
        with self.lock:
            counts = Counter(r["sid"] for r in self.studies.values() if r["sid"])
            for row in self.studies.values():
                row["duplicate_sid"] = bool(row["sid"] and counts[row["sid"]] > 1)

    def _watch(self):
        while not self.stop.wait(1):
            try:
                self.scan()
                self.schedule_changes()
            except OSError, ValueError:
                continue

    def schedule_changes(self):
        with self.lock:
            if self.paused:
                return
            for row in self.studies.values():
                if not row["_pending"] or time.monotonic() - row["_changed_at"] < 1:
                    continue
                if row["_blocked"] or row["mode"] == "off" or row["duplicate_sid"]:
                    continue
                action = "validate" if row.get("_initial") else row["mode"]
                if action == "upload" and row.get("identity_changed"):
                    action = "validate"
                if action == "upload" and (
                    self.offline or not self.account or not self.can_upload
                ):
                    row["message"] = (
                        "Upload on save suspended: connect an authorized account"
                    )
                    continue
                if self.active == row["id"]:
                    continue
                row["_pending"] = False
                row["_initial"] = False
                self._enqueue_one(row, action, automatic=True)

    def _enqueue_one(self, row, action, automatic=False):
        if row["_blocked"]:
            raise ValueError("Reconcile the unknown upload before starting another job")
        if row["duplicate_sid"] and action == "upload":
            raise ValueError("Resolve duplicate study identifiers before uploading")
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
        self.jobs.append(job)
        protected = [
            j for j in self.jobs if j["status"] in {"queued", "running", "unknown"}
        ]
        finished = [j for j in self.jobs if j not in protected][-100:]
        self.jobs = sorted(protected + finished, key=lambda j: j["created_at"])
        self.queue[row["id"]] = job
        row["_pending"] = False
        row["_initial"] = False
        row["status"] = "queued"
        self._save()
        self.wakeup.set()
        return job

    def enqueue(self, ids, action):
        if action not in {"validate", "validate_remote", "upload"}:
            raise ValueError("Choose validate or upload")
        with self.lock:
            rows = self._selected(ids)
            if any(row["_blocked"] for row in rows):
                raise ValueError("Reconcile unknown uploads first")
            if action == "upload" and any(row["duplicate_sid"] for row in rows):
                raise ValueError("Resolve duplicate study identifiers before uploading")
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
        if any(
            not isinstance(identifier, str) or identifier not in self.studies
            for identifier in ids
        ):
            raise ValueError("Study is not in this workspace")
        return [self.studies[key] for key in dict.fromkeys(ids)]

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
                row["identity_changed"] = False
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
                    self.studies[identifier]["_pending"] = True
                self._cancel_pending()
            self._save()
        self.wakeup.set()
        return self.snapshot()

    def configure(
        self,
        endpoint=None,
        api_key=None,
        github_user=None,
        offline=None,
        repository=None,
    ):
        with self.lock:
            changed = endpoint is not None or api_key is not None or offline is not None
            if self.active and changed:
                raise ValueError("Wait for the running job before changing connection")
            if offline is not None and not isinstance(offline, bool):
                raise ValueError("Offline must be true or false")
            if api_key is not None and not isinstance(api_key, str):
                raise ValueError("API key must be text")
            resolved_endpoint = (
                self.endpoint
                if endpoint is None
                else (endpoint_root(endpoint) if endpoint else "")
            )
            github = self.github
            if repository is not None and repository != self.repository:
                github = GitHubAssignments(repository, os.environ.get("GH_TOKEN"))
            if (
                github_user is not None
                and github_user
                and github_user
                not in {u["login"] for u in github.data.get("users", [])}
            ):
                raise ValueError("Select a user from the available GitHub users")
            if changed:
                self._connection_generation += 1
                self._cancel_pending()
                self.account = None
                self.can_upload = False
                self.connection_error = None
                self.vocabulary = {"status": "not_checked"}
            self.endpoint = resolved_endpoint
            if api_key is not None:
                self.api_key = api_key or None
            if offline is not None:
                self.offline = offline
            if github_user is not None:
                self.github_user = github_user
            self.github = github
            self.repository = github.repository
            if changed:
                for row in self.studies.values():
                    row.update(mode="validate", stale=True)
                    row["_pending"] = False
            self._save()
        if changed:
            self.connect()
        return self.snapshot()

    def _connect(self):
        self.connect()
        if not self.offline and not self.stop.is_set():
            self.refresh_assignments()

    def connect(self):
        with self.lock:
            self._connection_generation += 1
            generation = self._connection_generation
            endpoint, api_key = self.endpoint, self.api_key
            if self.offline or not endpoint:
                self.vocabulary = {"status": "offline"}
                return
        account, can_upload, error = None, False, None
        try:
            with Client(endpoint, api_key=api_key, cache=self.cache) as client:
                self._vocabulary(client, generation=generation)
                with self.lock:
                    if generation != self._connection_generation:
                        return
                if api_key:
                    value = client._request("GET", "/api/v2/curation-context").json()
                    account = value["username"]
                    can_upload = bool(value["can_upload"])
        except ClientError, ValueError, KeyError, OSError:
            error = "Could not verify the server account or vocabulary. Check endpoint, key, and server version."
        with self.lock:
            if generation != self._connection_generation:
                return
            self.account, self.can_upload = account, can_upload
            self.connection_error = error
            for row in self.studies.values():
                row["mode"] = self.modes.get(self._context(), {}).get(
                    row["id"], "validate"
                )

    def _vocabulary(self, client, *, generation=None):
        capabilities = client.capabilities()
        if capabilities.processing_version != PROCESSING_VERSION:
            raise CompatibilityError(
                "Upgrade pkdb to match the server processing version"
            )
        try:
            vocabulary = self.cache.load(client.endpoint)
        except OSError, ValueError:
            vocabulary = None
        if (
            vocabulary is None
            or vocabulary_hash(vocabulary) != capabilities.vocabulary_hash
        ):
            vocabulary = client.vocabulary()
        digest = vocabulary_hash(vocabulary)
        if digest != capabilities.vocabulary_hash:
            raise CompatibilityError(
                "Server vocabulary changed while synchronizing; validate again"
            )
        with self.lock:
            if generation is not None and generation != self._connection_generation:
                return vocabulary
            if self.vocabulary.get("hash") != digest:
                for row in self.studies.values():
                    row["stale"] = True
            self.vocabulary = {
                "status": "current",
                "hash": digest,
                "processing_version": PROCESSING_VERSION,
            }
        return vocabulary

    def refresh_assignments(self):
        if self.offline:
            return {**self.github.data, "status": "offline"}
        result = self.github.refresh()
        with self.lock:
            self._save()
        return result

    def map_assignment(self, number, study_id):
        with self.lock:
            row = self._selected([study_id])[0]
            if number not in {
                issue["number"] for issue in self.github.data.get("issues", [])
            }:
                raise ValueError("Unknown GitHub issue")
            key = f"{self.repository}#{number}"
            self.mappings.setdefault(key, [])
            if str(row["_folder"]) not in self.mappings[key]:
                self.mappings[key].append(str(row["_folder"]))
            self._save()
        return self.snapshot()

    def resolve_file(self, study_id, file=None):
        with self.lock:
            row = self._selected([study_id])[0]
            folder = row["_folder"]
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

    def _server_validate(self, client, prepared):
        with prepared.source() as source, ExitStack() as stack:
            parts: list[tuple[str, tuple]] = [
                (name, (None, json.dumps(value)))
                for name, value in (
                    ("study", source.study),
                    ("reference", source.reference),
                )
            ]
            parts.extend(
                (
                    "files",
                    (
                        name,
                        stack.enter_context(path.open("rb")),
                        "application/octet-stream",
                    ),
                )
                for name, path in source.files.items()
            )
            headers = {
                **client._headers(required=True),
                "X-PKDB-Report-Version": "2",
                "X-PKDB-Vocabulary-Hash": prepared.vocabulary_hash,
                "X-PKDB-Processing-Version": PROCESSING_VERSION,
            }
            return client._request(
                "POST", "/api/v2/studies/validate", headers=headers, files=parts
            ).json()

    def run_job(self, job):
        row = self.studies[job["study_id"]]
        with self.lock:
            if row["_blocked"]:
                job.update(
                    status="canceled",
                    message="A previous upload has an unknown outcome; reconcile it first",
                )
                self._save()
                return
        expected = row["_fingerprint"]
        outcome = {"persistence": "not_attempted", "report": {"issues": []}}

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
            row["status"] = "validating"
            with Client(
                job["endpoint"] or "http://localhost",
                api_key=self.api_key,
                cache=self.cache,
                progress=progress,
            ) as client:
                if self.offline or not job["endpoint"]:
                    try:
                        vocabulary = (
                            self.cache.load(job["endpoint"])
                            if job["endpoint"]
                            else bundled_vocabulary()
                        )
                    except OSError, ValueError:
                        vocabulary = bundled_vocabulary()
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
                    }
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
            except OSError, StudyValidationError:
                current = False
            job.update(
                status="failed" if current else "canceled",
                message="Validation found problems"
                if current
                else "Source changed; diagnostics belong to a previous save",
            )
            row.update(status="invalid" if current else "changed", stale=not current)
            if not current:
                row["_pending"] = True
                row["_changed_at"] = time.monotonic()
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
                publication = client._request(
                    "GET", f"/api/v2/studies/{quote(job['sid'], safe='')}/publication"
                ).json()
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
                    self.studies[identifier]["_pending"] = False
                    self.studies[identifier]["status"] = "changed"
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
            if row["duplicate_sid"] or not self.endpoint or not self.api_key:
                raise ValueError(
                    "Resolve duplicate identifiers and connect an API key first"
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

    def close(self):
        self.stop.set()
        self.wakeup.set()
        with self.lock:
            self._cancel_pending()
            self._save()
        for thread in self.threads:
            thread.join(timeout=2)
