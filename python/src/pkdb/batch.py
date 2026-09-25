"""Bounded study uploads with parent-owned checkpoints and explicit write outcomes."""

import json
import multiprocessing
import os
import queue
import signal
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict
from urllib.parse import quote

from pkdb.cache import atomic_json, endpoint_root
from pkdb.client import Client
from pkdb.domain.validation import PROCESSING_VERSION
from pkdb.domain.vocabulary import Vocabulary, vocabulary_hash
from pkdb.errors import ClientError, CompatibilityError
from pkdb.preparation import source_hashes
from pkdb.schemas.validation import StudyValidationError


class StudyResult(TypedDict, total=False):
    index: int
    path: str
    sid: str | None
    status: str
    persistence: str
    ok: bool
    source_digest: str
    file_hashes: dict[str, str]
    timings: dict[str, float]
    error: str
    server_report: dict[str, Any]


@dataclass(frozen=True)
class BatchOptions:
    jobs: int = 1
    fail_fast: bool = False
    report: Path | None = None
    resume: Path | None = None
    drain_seconds: float = 10

    def __post_init__(self):
        if self.jobs < 1:
            raise ValueError("jobs must be positive")
        if self.drain_seconds < 0:
            raise ValueError("drain_seconds must be nonnegative")


@dataclass(frozen=True)
class BatchEvent:
    index: int
    path: str
    stage: str
    completed: int | None = None
    total: int | None = None


def redact(value, token):
    if isinstance(value, str) and token:
        return value.replace(token, "[redacted]")
    if isinstance(value, dict):
        return {key: redact(item, token) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item, token) for item in value]
    return value


def _worker(slot, tasks, events, endpoint, token, vocabulary, capabilities, transport):
    if multiprocessing.current_process().name != "MainProcess":
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    # Spawned processes never inherit an HTTP connection pool.
    with Client(endpoint, api_key=token, transport=transport) as api:
        while (task := tasks.get()) is not None:
            if task == "cancel":
                return
            index, path, expected_sid = task
            started = time.monotonic()
            stage = "read"
            submitting = False
            timings = {}
            stage_started = started

            def progress(event):
                nonlocal stage, stage_started
                now = time.monotonic()
                if event.stage != stage:
                    timings[stage] = timings.get(stage, 0) + now - stage_started
                    stage_started = now
                    stage = event.stage
                    events.put((slot, index, "progress", event))
                elif event.total is not None and event.completed == event.total:
                    events.put((slot, index, "progress", event))

            def submit(prepared, hashes):
                nonlocal submitting
                if prepared.study.sid != expected_sid:
                    raise ValueError("Study SID changed after batch discovery")
                events.put(
                    (
                        slot,
                        index,
                        "submitting",
                        {
                            "sid": prepared.study.sid,
                            "source_digest": prepared.study.source_digest,
                            "file_hashes": hashes,
                        },
                    )
                )
                if tasks.get() != "submit":
                    raise ValueError("Submission stopped by batch coordinator")
                submitting = True

            api.progress = progress
            result = {"ok": False, "persistence": "not_attempted", "stop": False}
            try:
                uploaded = api._upload_folder(path, vocabulary, capabilities, submit)
                result.update(
                    uploaded.model_dump(mode="json"),
                    ok=True,
                    persistence="created" if uploaded.created else "replaced",
                    url=f"{endpoint}/api/v1/studies/{quote(uploaded.sid, safe='')}/",
                )
                if api.last_upload_report:
                    result.update(
                        server_report=api.last_upload_report,
                        request_id=api.last_upload_report.get("request_id"),
                    )
            except StudyValidationError as error:
                result.update(
                    error="Study validation failed",
                    report=error.report.model_dump(mode="json"),
                )
            except ClientError as error:
                result.update(
                    error=str(error),
                    status_code=error.status_code,
                    persistence=error.persistence,
                    code=error.code,
                    request_id=error.request_id,
                    retry_after=error.retry_after,
                    server_report=error.envelope,
                )
                result["stop"] = (
                    isinstance(error, CompatibilityError)
                    or error.status_code in {401, 429}
                    or (error.status_code is not None and error.status_code >= 500)
                    or error.persistence == "unknown"
                )
                if error.report:
                    result["report"] = error.report.model_dump(mode="json")
            except Exception as error:
                result.update(
                    error=str(error),
                    persistence="unknown" if submitting else "not_attempted",
                    stop=submitting,
                )
            timings[stage] = timings.get(stage, 0) + time.monotonic() - stage_started
            result.update(
                stage=stage, timings=timings, elapsed_seconds=time.monotonic() - started
            )
            events.put((slot, index, "result", redact(result, token)))


def upload_many(
    folders: list[Path],
    *,
    endpoint: str,
    api_key: str,
    vocabulary: Vocabulary,
    options: BatchOptions | None = None,
    progress: Callable[[BatchEvent], None] | None = None,
    on_result: Callable[[StudyResult], None] | None = None,
    transport=None,
) -> dict:
    """Upload in bounded workers; never retry an ambiguous write automatically.

    Results are ordered by input index. Callbacks and report writes run exclusively
    in the calling thread. A supplied transport is supported only with one job.
    """
    options = options or BatchOptions()
    if transport is not None and options.jobs != 1:
        raise ValueError("Custom transports require jobs=1")
    endpoint = endpoint_root(endpoint)
    paths = [str(Path(folder).resolve()) for folder in folders]
    if not paths:
        raise ValueError("No study folders supplied")
    if len(paths) != len(set(paths)):
        raise ValueError("Duplicate study folders")
    for report_path in (options.report, options.resume):
        if report_path and any(
            report_path.resolve().is_relative_to(Path(p)) for p in paths
        ):
            raise ValueError("Write reports outside all study folders")
    source_root = (
        Path(os.path.commonpath(paths)).parent
        if len(paths) == 1
        else Path(os.path.commonpath(paths))
    )
    rows: list[dict[str, Any]] = []
    sids = set()
    references = set()
    for index, path in enumerate(paths):
        try:
            data = json.loads((Path(path) / "study.json").read_text())
            sid = str(data["sid"])
        except ValueError, OSError, KeyError, TypeError:
            # The runner produces the full source validation diagnostic.
            data, sid = {}, None
        if sid is not None and sid in sids:
            raise ValueError(f"Duplicate study SID: {sid}")
        sids.add(sid)
        reference = data.get("reference")
        if reference is not None:
            key = str(reference)
            if key in references:
                raise ValueError(f"Multiple studies claim reference {key}")
            references.add(key)
        rows.append(
            dict(
                index=index,
                path=path,
                name=Path(path).name,
                relative_path=Path(path).relative_to(source_root).as_posix(),
                sid=sid,
                status="queued",
                persistence="not_attempted",
                ok=False,
            )
        )
    batch: dict[str, Any] = dict(
        report_version=3,
        command="upload",
        started_at=datetime.now(UTC).isoformat(),
        endpoint=endpoint,
        paths=paths,
        vocabulary_hash=vocabulary_hash(vocabulary),
        vocabulary_version=vocabulary.version,
        processing_version=PROCESSING_VERSION,
        results=rows,
    )
    target = options.report or options.resume
    with Client(endpoint, api_key=api_key, transport=transport) as api:
        capabilities = api.capabilities()
        if (
            capabilities.processing_version != PROCESSING_VERSION
            or capabilities.vocabulary_hash != batch["vocabulary_hash"]
        ):
            raise CompatibilityError(
                "Server rules differ; synchronize vocabulary and client"
            )
        if options.resume:
            previous = json.loads(options.resume.read_text())
            for key in (
                "report_version",
                "endpoint",
                "paths",
                "vocabulary_hash",
                "processing_version",
            ):
                if previous.get(key) != batch[key]:
                    raise ValueError(f"Resume report does not match {key}")
            for row, old in zip(rows, previous["results"], strict=True):
                if old.get("status") not in {"confirmed", "submitting", "unknown"}:
                    continue
                if source_hashes(Path(row["path"])) != old.get("file_hashes"):
                    raise ValueError(
                        f"Source changed since previous upload: {row['path']}"
                    )
                try:
                    publication = api.publication(row["sid"])
                except ClientError as error:
                    if error.status_code != 404 or old["status"] != "confirmed":
                        raise
                    continue
                if (
                    publication.digest == old.get("source_digest")
                    and publication.processing_version == batch["processing_version"]
                    and publication.vocabulary_version == batch["vocabulary_version"]
                ):
                    row.update(
                        old,
                        status="confirmed",
                        ok=True,
                        skipped=True,
                        persistence=old["persistence"]
                        if old["status"] == "confirmed"
                        else "reconciled",
                    )
                elif old["status"] != "confirmed":
                    raise ValueError(
                        f"Unknown upload requires explicit resolution: {row['sid']}"
                    )

    def checkpoint():
        batch["updated_at"] = datetime.now(UTC).isoformat()
        batch["summary"] = {
            "discovered": len(rows),
            "attempted": sum(r["status"] != "queued" for r in rows),
            "reconciled": sum(r["persistence"] == "reconciled" for r in rows),
            "created": sum(r["persistence"] == "created" for r in rows),
            "replaced": sum(r["persistence"] == "replaced" for r in rows),
            "failed": sum(r["status"] == "failed" for r in rows),
            "unknown": sum(r["status"] == "unknown" for r in rows),
            "unattempted": sum(r["status"] == "queued" for r in rows),
        }
        batch["unattempted"] = [r["path"] for r in rows if r["status"] == "queued"]
        if target:
            atomic_json(target, redact(batch, api_key))

    checkpoint()
    if on_result:
        for row in rows:
            if row.get("skipped"):
                on_result(redact(dict(row), api_key))
    pending = iter(r for r in rows if r["status"] == "queued")
    ctx = multiprocessing.get_context("spawn")
    events = ctx.Queue() if options.jobs > 1 else queue.Queue()
    workers = []
    active = {}
    stopped = False
    deadline = None
    report_error = None

    def save():
        nonlocal stopped, report_error
        try:
            checkpoint()
        except OSError as error:
            stopped = True
            report_error = redact(str(error), api_key)

    def schedule(slot):
        if stopped:
            return
        row = next(pending, None)
        if row is None:
            return
        row["status"] = "preparing"
        active[slot] = row["index"]
        save()
        if not stopped:
            workers[slot][1].put((row["index"], row["path"], row["sid"]))
        else:
            row["status"] = "queued"
            del active[slot]

    try:
        for slot in range(min(options.jobs, len(rows))):
            tasks = ctx.Queue() if options.jobs > 1 else queue.Queue()
            args = (
                slot,
                tasks,
                events,
                endpoint,
                api_key,
                vocabulary,
                capabilities,
                transport,
            )
            worker = (
                ctx.Process(target=_worker, args=args)
                if options.jobs > 1
                else threading.Thread(target=_worker, args=args, daemon=True)
            )
            worker.start()
            workers.append((worker, tasks))
            schedule(slot)
        while active:
            try:
                if deadline is not None and time.monotonic() >= deadline:
                    break
                try:
                    slot, index, kind, payload = events.get(timeout=0.1)
                except queue.Empty:
                    for slot, index in list(active.items()):
                        if not workers[slot][0].is_alive():
                            row = rows[index]
                            row.update(
                                ok=False,
                                error="Upload worker exited",
                                persistence="unknown"
                                if row["status"] == "submitting"
                                else "not_attempted",
                                status="unknown"
                                if row["status"] == "submitting"
                                else "failed",
                            )
                            del active[slot]
                            stopped = True
                            save()
                    continue
                row = rows[index]
                if kind == "progress":
                    row["stage"] = payload.stage
                    if progress:
                        progress(
                            BatchEvent(
                                index,
                                row["path"],
                                payload.stage,
                                payload.completed,
                                payload.total,
                            )
                        )
                elif kind == "submitting":
                    row.update(payload, status="submitting")
                    save()
                    workers[slot][1].put("cancel" if stopped else "submit")
                else:
                    stop = payload.pop("stop")
                    row.update(payload)
                    row["status"] = (
                        "confirmed"
                        if row["ok"]
                        else "unknown"
                        if row["persistence"] == "unknown"
                        else "failed"
                    )
                    del active[slot]
                    stopped |= stop or (options.fail_fast and not row["ok"])
                    save()
                    if on_result:
                        on_result(redact(dict(row), api_key))
                    schedule(slot)
            except KeyboardInterrupt:
                stopped = True
                batch["interrupted"] = True
                deadline = time.monotonic() + options.drain_seconds
    finally:
        for slot, index in active.items():
            row = rows[index]
            unknown = row["status"] == "submitting"
            row.update(
                status="unknown" if unknown else "failed",
                ok=False,
                persistence="unknown" if unknown else "not_attempted",
                error="Interrupted before confirmation",
            )
        for slot, (worker, tasks) in enumerate(workers):
            if slot in active and rows[active[slot]].get("stage") not in {
                "transfer",
                "server_validation",
                "complete",
            }:
                tasks.put("cancel")
            tasks.put(None)
            if (
                not isinstance(worker, threading.Thread)
                and active
                and worker.is_alive()
            ):
                worker.terminate()
            worker.join(timeout=1)
        save()
    if report_error:
        batch["report_error"] = report_error
    return redact(batch, api_key)
