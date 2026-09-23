"""Prepare, validate, and upload existing PK-DB study folders."""

import argparse
import json
import os
import sys
from pathlib import Path

from pkdb import __version__
from pkdb.cache import VocabularyCache, atomic_json, bundled_vocabulary
from pkdb.client import Client
from pkdb.domain.vocabulary import Vocabulary
from pkdb.errors import ClientError
from pkdb.preparation import prepare, study_folders
from pkdb.schemas.validation import StudyValidationError


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
    args = parser.parse_args(argv)
    if args.command == "upload" and args.offline:
        parser.error("upload requires network access; use validate --offline")
    token = os.environ.get("PKDB_API_KEY")
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
        print(
            json.dumps(_redact({"ok": False, "error": str(error)}, token)),
            file=sys.stderr,
        )
        return 1
    failed = False
    for folder in folders:
        result = {"path": str(folder), "ok": False}
        try:
            prepared = prepare(folder, vocabulary=snapshot)
            result.update(sid=prepared.study.sid)
            if args.command == "upload":
                with Client(
                    args.endpoint, api_key=token, transport=client, cache=cache
                ) as api:
                    result.update(api.upload(prepared).model_dump(mode="json"))
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
            result.update(error=str(error), status_code=error.status_code)
            if error.report:
                result["report"] = error.report.model_dump(mode="json")
        except (ValueError, OSError) as error:
            result["error"] = str(error)
        result = _redact(result, token)
        if args.output:
            try:
                atomic_json(args.output, result)
            except OSError as error:
                result.update(ok=False, error=str(error))
        print(json.dumps(result, ensure_ascii=False, allow_nan=False), flush=True)
        failed |= not result["ok"]
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
