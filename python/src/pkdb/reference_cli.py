"""Lightweight command registration; lookup dependencies load after parsing."""

import json
import sys
from pathlib import Path


def register(commands):
    command = commands.add_parser(
        "reference", help="Resolve and review literature metadata"
    )
    actions = command.add_subparsers(dest="action", required=True)
    resolve = actions.add_parser("resolve", help="Preview or save a study reference")
    resolve.add_argument("folder", type=Path)
    resolve.add_argument("--input", type=Path, help="Minimal reference input JSON")
    resolve.add_argument("--pmid")
    resolve.add_argument("--doi")
    resolve.add_argument("--title")
    resolve.add_argument(
        "--author", action="append", help="Author display name (repeatable)"
    )
    resolve.add_argument("--organization", action="append")
    resolve.add_argument("--publication-date", help="YYYY, YYYY-MM, or YYYY-MM-DD")
    resolve.add_argument(
        "--write",
        action="store_true",
        help="Save the resolved reference.json; default is preview only",
    )
    resolve.add_argument(
        "--reset-overrides",
        action="store_true",
        help="Use provider metadata instead of saved curator corrections",
    )
    search = actions.add_parser(
        "search", help="Find candidates without selecting or saving a publication"
    )
    search.add_argument("citation")
    for action in (resolve, search):
        action.add_argument("--cache-dir", type=Path)
        action.add_argument("--offline", action="store_true")
        action.add_argument("--refresh", action="store_true")


def run(args, *, client=None):
    from pkdb.references import ReferenceResolver, preview_reference, save_reference

    try:
        resolver = ReferenceResolver(
            args.cache_dir, client=client, offline=args.offline, refresh=args.refresh
        )
        if args.action == "search":
            result = {"candidates": resolver.search(args.citation)}
        else:
            seed = json.loads(args.input.read_text()) if args.input else {}
            if not isinstance(seed, dict):
                raise ValueError("Reference input must be a JSON object")
            for key in ("pmid", "doi", "title", "publication_date"):
                if getattr(args, key) is not None:
                    seed[key] = getattr(args, key)
            if args.author or args.organization:
                seed["authors"] = [
                    {"last_name": name} for name in args.author or []
                ] + [{"organization": name} for name in args.organization or []]
            result = preview_reference(
                args.folder, seed, resolver, reset_overrides=args.reset_overrides
            )
            if args.write:
                save_reference(args.folder, result)
            result["saved"] = args.write
        print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as error:
        print(json.dumps({"ok": False, "error": str(error)}), file=sys.stderr)
        return 1
