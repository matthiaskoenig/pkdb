"""PK-DB command-line entry point."""

import argparse
import json
import os
from contextlib import nullcontext
from pathlib import Path

import httpx

from pkdb.commands.upload import api_root, send_folder, study_folders


def main(argv=None, *, client=None):
    parser = argparse.ArgumentParser(prog="pkdb")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("upload", "validate"):
        command = commands.add_parser(name)
        command.add_argument("path", type=Path)
        command.add_argument("--api-url", required=True)
    commands.add_parser("bootstrap").add_argument("path", type=Path)
    commands.add_parser("cleanup")
    args = parser.parse_args(argv)
    if args.command in {"bootstrap", "cleanup"}:
        return local_command(args)

    token = os.environ.get("PKDB_API_TOKEN")
    if not token:
        print(
            json.dumps({"ok": False, "error": "Set PKDB_API_TOKEN in the environment"})
        )
        return 1
    try:
        url = api_root(args.api_url)
        folders = study_folders(args.path)
    except (ValueError, OSError) as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 1
    failed = False
    with (
        nullcontext(client)
        if client is not None
        else httpx.Client(
            timeout=httpx.Timeout(600, connect=10), follow_redirects=False
        ) as transport
    ):
        for folder in folders:
            result = send_folder(
                folder,
                client=transport,
                api_url=url,
                token=token,
                validate=args.command == "validate",
            )
            print(
                json.dumps(result, ensure_ascii=False).replace(token, "[redacted]"),
                flush=True,
            )
            failed |= not result["ok"]
    return int(failed)


def local_command(args):
    from sqlalchemy.exc import SQLAlchemyError

    from pkdb.commands.bootstrap import bootstrap
    from pkdb.commands.cleanup import cleanup
    from pkdb.config import Settings
    from pkdb.db.session import make_session_factory
    from pkdb.files.store import FileStore

    factory = None
    try:
        settings = Settings()
        factory = make_session_factory(settings.database_url)
        if args.command == "bootstrap":
            report = bootstrap(args.path, factory)
            result = {"ok": not report.errors, **report.model_dump(mode="json")}
        else:
            store = FileStore(settings.file_root, factory, settings.upload_max_bytes)
            result = {"ok": True, **cleanup(factory, store)}
        print(json.dumps(result))
        return int(not result["ok"])
    except (ValueError, OSError, SQLAlchemyError):
        # Connection/configuration exceptions can contain database credentials.
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "Local administration failed; check database, schema, file storage and input configuration",
                }
            )
        )
        return 1
    finally:
        if factory is not None:
            factory.kw["bind"].dispose()


if __name__ == "__main__":
    raise SystemExit(main())
