"""PK-DB command-line entry point."""

import argparse
import json
import os
import sys
from contextlib import nullcontext
from getpass import getpass
from pathlib import Path

import httpx2

from pkdb_server.commands.upload import api_root, send_folder, study_folders


def main(argv=None, *, client=None):
    parser = argparse.ArgumentParser(prog="pkdb-server")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("upload", "validate"):
        command = commands.add_parser(name)
        command.add_argument("path", type=Path)
        command.add_argument("--api-url", required=True)
    commands.add_parser("bootstrap").add_argument("path", type=Path)
    commands.add_parser("bootstrap-study").add_argument("path", type=Path)
    commands.add_parser("cleanup")
    admin = commands.add_parser("create-admin")
    admin.add_argument("username")
    admin.add_argument("--email", required=True)
    admin.add_argument("--password-stdin", action="store_true")
    admin.add_argument("--adopt-user-id", type=int)
    user = commands.add_parser("create-user")
    user.add_argument("username")
    user.add_argument("--email")
    user.add_argument("--role", choices=["user", "curator", "reviewer"], default="user")
    user.add_argument("--password-stdin", action="store_true")
    roster = commands.add_parser("import-users")
    roster.add_argument("path", type=Path)
    roster.add_argument("--contacts", type=Path)
    mode = roster.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    roster.add_argument("--update-existing", action="store_true")
    roster.add_argument("--avatar-root", type=Path, default=Path("frontend/public"))
    args = parser.parse_args(argv)
    if args.command in {
        "bootstrap",
        "bootstrap-study",
        "cleanup",
        "create-admin",
        "import-users",
        "create-user",
    }:
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
        else httpx2.Client(
            timeout=httpx2.Timeout(600, connect=10), follow_redirects=False
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
                json.dumps(redact_values(result, token), ensure_ascii=False),
                flush=True,
            )
            failed |= not result["ok"]
    return int(failed)


def redact_values(value, token):
    """Redact before JSON escaping without changing field names or scalar types."""
    if isinstance(value, str):
        return value.replace(token, "[redacted]")
    if isinstance(value, list):
        return [redact_values(item, token) for item in value]
    if isinstance(value, dict):
        return {key: redact_values(item, token) for key, item in value.items()}
    return value


def local_command(args):
    from sqlalchemy.exc import SQLAlchemyError

    from pkdb_server.commands.admin import AdminProvisioningError, create_admin
    from pkdb_server.commands.bootstrap import bootstrap, bootstrap_study
    from pkdb_server.commands.cleanup import cleanup
    from pkdb_server.commands.user_import import import_roster
    from pkdb_server.config import Settings
    from pkdb_server.db.session import make_session_factory
    from pkdb_server.files.store import FileStore

    factory = None
    try:
        settings = Settings()
        factory = make_session_factory(settings.database_url)
        if args.command == "create-admin":
            if args.adopt_user_id is not None:
                if args.password_stdin:
                    raise AdminProvisioningError(
                        "Adoption preserves credentials; omit --password-stdin"
                    )
                password = None
            elif args.password_stdin:
                password = sys.stdin.readline(1026).rstrip("\r\n")
            elif sys.stdin.isatty():
                password = getpass("Administrator password: ")
            else:
                raise AdminProvisioningError(
                    "Use an interactive terminal or --password-stdin"
                )
            create_admin(
                factory,
                args.username,
                args.email,
                password,
                adopt_user_id=args.adopt_user_id,
            )
            result = {"ok": True, "username": args.username}
        elif args.command == "create-user":
            from pkdb_server.commands.users import create_user

            if args.password_stdin:
                password = sys.stdin.readline(1026).rstrip("\r\n")
            elif sys.stdin.isatty():
                password = getpass("User password: ")
            else:
                raise ValueError("Use an interactive terminal or --password-stdin")
            user_id = create_user(
                factory, args.username, password, email=args.email, role=args.role
            )
            result = {"ok": True, "username": args.username, "user_id": user_id}
        elif args.command == "import-users":
            result = import_roster(
                args.path,
                factory,
                contacts=args.contacts,
                apply=args.apply,
                update_existing=args.update_existing,
                file_root=settings.file_root,
                avatar_root=args.avatar_root,
            )
        elif args.command in {"bootstrap", "bootstrap-study"}:
            operation = bootstrap if args.command == "bootstrap" else bootstrap_study
            report = operation(args.path, factory)
            result = {"ok": not report.errors, **report.model_dump(mode="json")}
        else:
            store = FileStore(settings.file_root, factory, settings.upload_max_bytes)
            result = {"ok": True, **cleanup(factory, store)}
        print(json.dumps(result))
        return int(not result["ok"])
    except AdminProvisioningError as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 1
    except ValueError, OSError, SQLAlchemyError:
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
