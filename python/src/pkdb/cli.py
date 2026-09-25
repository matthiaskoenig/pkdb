"""Prepare, validate, and upload existing PK-DB study folders."""

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

from pkdb import __version__
from pkdb.cache import VocabularyCache, atomic_json, bundled_vocabulary
from pkdb.client import Client
from pkdb.domain.vocabulary import Vocabulary
from pkdb.errors import ClientError, CompatibilityError
from pkdb.preparation import prepare, study_folders
from pkdb.schemas.validation import StudyValidationError
from pkdb.terminal import Terminal, safe_text


def _redact(value, token):
    if isinstance(value, str) and token:
        return value.replace(token, "[redacted]")
    if isinstance(value, dict):
        return {key: _redact(item, token) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item, token) for item in value]
    return value


def main(argv=None, *, client=None) -> int:
    parser = argparse.ArgumentParser(prog="pkdb", description=__doc__)
    parser.add_argument("--version", action="version", version=f"pkdb {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "validate", "upload"):
        command = commands.add_parser(name)
        command.add_argument(
            "folder", type=Path, help="Existing study folder or parent directory"
        )
        command.add_argument(
            "--endpoint", "--api-url", default=os.environ.get("PKDB_ENDPOINT")
        )
        command.add_argument(
            "--vocabulary", type=Path, help="Pinned vocabulary snapshot JSON"
        )
        command.add_argument("--cache-dir", type=Path)
        command.add_argument("--format", choices=("human", "json"))
        command.add_argument("--verbose", action="store_true")
        command.add_argument("--report", type=Path)
        command.add_argument("--overwrite-report", action="store_true")
        command.add_argument("--fail-fast", action="store_true")
        command.add_argument(
            "--offline",
            action="store_true",
            help="Never contact the server (prepare/validate only)",
        )
        command.add_argument(
            "--output",
            type=Path,
            help="JSON output file outside the study folder (one study only)",
        )
    vocabulary = commands.add_parser("vocabulary")
    actions = vocabulary.add_subparsers(dest="action", required=True)
    sync = actions.add_parser(
        "sync", help="Explicitly retrieve and cache the endpoint's validation rules"
    )
    sync.add_argument("--endpoint", default=os.environ.get("PKDB_ENDPOINT"))
    sync.add_argument("--cache-dir", type=Path)
    sync.add_argument(
        "--output", type=Path, help="Portable project vocabulary lock file"
    )
    curation = commands.add_parser(
        "curation", help="Open the local study curation interface"
    )
    curation.add_argument("path", nargs="?", type=Path)
    curation.add_argument("--endpoint", default=os.environ.get("PKDB_ENDPOINT"))
    curation.add_argument("--github-user")
    curation.add_argument("--repository")
    curation.add_argument("--offline", action="store_true")
    curation.add_argument("--port", type=int, default=0)
    curation.add_argument("--no-browser", action="store_true")
    curation.add_argument("--state-dir", type=Path)
    args = parser.parse_args(argv)
    if args.command == "curation":
        from pkdb.curation.launch import run

        try:
            return run(
                **{key: value for key, value in vars(args).items() if key != "command"}
            )
        except ValueError, OSError:
            print(
                "Unable to start curation. Check the workspace, state directory, and port.",
                file=sys.stderr,
            )
            return 1
    if args.command == "upload" and args.offline:
        parser.error("upload requires network access; use validate --offline")
    token = os.environ.get("PKDB_API_KEY")
    human = getattr(args, "format", None) == "human" or (
        getattr(args, "format", None) is None and sys.stdout.isatty()
    )
    terminal = Terminal(human, getattr(args, "verbose", False))
    cache = VocabularyCache(args.cache_dir)
    try:
        if args.command == "vocabulary":
            with Client(
                args.endpoint, api_key=token, transport=client, cache=cache
            ) as api:
                snapshot = api.vocabulary()
                if args.output:
                    snapshot.save(args.output)
                from pkdb.domain.vocabulary import vocabulary_hash

                print(
                    json.dumps(
                        {
                            "ok": True,
                            "vocabulary_version": snapshot.version,
                            "vocabulary_hash": vocabulary_hash(snapshot),
                        }
                    )
                )
            return 0
        folders = study_folders(args.folder)
        if args.report:
            if args.output and args.report.resolve() == args.output.resolve():
                raise ValueError("Use different paths for --output and --report")
            if any(
                args.report.resolve().is_relative_to(folder.resolve())
                for folder in folders
            ):
                raise ValueError("Write --report outside all study folders")
            if args.report.exists() and not args.overwrite_report:
                raise ValueError(
                    "Report already exists; choose another path or use --overwrite-report"
                )
        if args.output:
            if len(folders) != 1:
                raise ValueError("--output requires a single study folder")
            if args.output.resolve().is_relative_to(folders[0].resolve()):
                raise ValueError(
                    "Write --output outside the study folder to keep source files unchanged"
                )
        if args.vocabulary:
            snapshot = Vocabulary.load(args.vocabulary)
        elif args.endpoint:
            try:
                snapshot = cache.load(args.endpoint)
            except FileNotFoundError:
                snapshot = bundled_vocabulary()
        else:
            snapshot = bundled_vocabulary()
        if args.command == "upload" and (not args.endpoint or not token):
            raise ValueError("Upload requires an endpoint and PKDB_API_KEY")
    except (ValueError, OSError, ClientError) as error:
        if human:
            terminal.result(_redact({"ok": False, "error": str(error)}, token))
        else:
            print(
                json.dumps(_redact({"ok": False, "error": str(error)}, token)),
                file=sys.stderr,
            )
        return 1
    failed = False
    interrupted = False
    results = []
    batch = {
        "report_version": 2,
        "command": args.command,
        "endpoint": args.endpoint,
        "source": str(args.folder.resolve()),
        "started_at": datetime.now(UTC).isoformat(),
        "client_version": __version__,
        "vocabulary_hash": None,
        "results": results,
    }
    terminal.begin(args.command, args.endpoint, str(args.folder), len(folders))

    def summary():
        return {
            "discovered": len(folders),
            "attempted": len(results),
            "created": sum(r.get("persistence") == "created" for r in results),
            "replaced": sum(r.get("persistence") == "replaced" for r in results),
            "validated": sum(
                r.get("ok", False) and r.get("persistence") == "not_attempted"
                for r in results
            ),
            "failed": sum(
                not r.get("ok")
                and r.get("persistence") not in {"unknown", "created", "replaced"}
                for r in results
            ),
            "unknown": sum(r.get("persistence") == "unknown" for r in results),
            "unattempted": len(folders) - len(results),
            "saved_with_errors": sum(
                not r.get("ok") and r.get("persistence") in {"created", "replaced"}
                for r in results
            ),
            "warnings": sum(
                len(r.get("warnings", []))
                + sum(
                    i.get("severity") == "warning"
                    for i in (r.get("report") or {}).get("issues", [])
                )
                for r in results
            ),
        }

    source_root = args.folder.resolve()
    if (source_root / "study.json").is_file():
        source_root = source_root.parent

    for index, folder in enumerate(folders, 1):
        started = time.monotonic()
        stop = False
        relative_path = folder.resolve().relative_to(source_root).as_posix()
        terminal.start(relative_path, index, len(folders))
        result = {
            "path": str(folder),
            "relative_path": relative_path,
            "name": folder.name,
            "ok": False,
            "persistence": "not_attempted",
        }
        try:
            prepared = prepare(folder, vocabulary=snapshot, progress=terminal.progress)
            batch["vocabulary_hash"] = prepared.vocabulary_hash
            batch["processing_version"] = prepared.prepared.processing_version
            result.update(sid=prepared.study.sid)
            if args.command == "upload":
                with Client(
                    args.endpoint,
                    api_key=token,
                    transport=client,
                    cache=cache,
                    progress=terminal.progress,
                ) as api:
                    result.update(api.upload(prepared).model_dump(mode="json"))
                    result["persistence"] = (
                        "created" if result["created"] else "replaced"
                    )
                    result["url"] = (
                        f"{api.endpoint}/api/v1/studies/{quote(str(result['sid']), safe='')}/"
                    )
                    if api.last_upload_report:
                        result["server_report"] = api.last_upload_report
                        result["request_id"] = api.last_upload_report.get("request_id")
            elif args.command == "prepare":
                result.update(prepared.model_dump())
            else:
                result.update(
                    report=prepared.report.model_dump(mode="json"),
                    vocabulary_version=prepared.prepared.vocabulary_version,
                    vocabulary_hash=prepared.vocabulary_hash,
                    processing_version=prepared.prepared.processing_version,
                )
            result["ok"] = True
        except StudyValidationError as error:
            result.update(
                error="Study validation failed",
                report=error.report.model_dump(mode="json"),
            )
        except ClientError as error:
            result.update(
                error=str(error),
                status_code=error.status_code,
                code=error.code,
                retry_after=error.retry_after,
                persistence=error.persistence,
                request_id=error.request_id,
                stage=error.stage,
            )
            if error.envelope:
                result["server_report"] = error.envelope
            stop = (
                isinstance(error, CompatibilityError)
                or error.status_code in {401, 429}
                or (error.status_code is not None and error.status_code >= 500)
                or error.persistence == "unknown"
            )
            if error.report:
                result["report"] = error.report.model_dump(mode="json")
        except (ValueError, OSError) as error:
            result["error"] = str(error)
        except KeyboardInterrupt:
            interrupted = True
            stop = True
            result.update(
                error="Interrupted",
                persistence="unknown"
                if terminal.stage in {"transfer", "server_validation", "complete"}
                else "not_attempted",
            )
        result.setdefault("stage", terminal.stage or "read")
        result["status"] = (
            "unknown"
            if result["persistence"] == "unknown"
            else "succeeded"
            if result["ok"]
            else "failed"
        )
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        result = _redact(result, token)
        if args.output:
            try:
                atomic_json(args.output, result)
            except OSError as error:
                result.update(
                    ok=False, status="failed", error=_redact(str(error), token)
                )
        results.append(result)
        batch["summary"] = summary()
        batch["updated_at"] = datetime.now(UTC).isoformat()
        batch["unattempted"] = [str(folder) for folder in folders[len(results) :]]
        if args.report:
            try:
                atomic_json(args.report, _redact(batch, token))
            except OSError as error:
                failed = True
                stop = True
                result["report_error"] = _redact(str(error), token)
                terminal.console.print(
                    "Could not save batch report: "
                    + safe_text(_redact(str(error), token)),
                    markup=False,
                ) if human else print(
                    json.dumps({"ok": False, "error": result["report_error"]}),
                    file=sys.stderr,
                )
        terminal.result(result)
        if not human:
            print(json.dumps(result, ensure_ascii=False, allow_nan=False), flush=True)
        failed |= not result["ok"]
        if stop or (args.fail_fast and not result["ok"]):
            break
    terminal.finish(
        summary(), str(args.report) if args.report and args.report.exists() else None
    )
    return 130 if interrupted else int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
