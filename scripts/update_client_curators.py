#!/usr/bin/env python3
"""Bundle public curator profiles and avatars for the local curation app.

Run from the repository: uv run --project backend python scripts/update_client_curators.py [--check]
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "backend/bootstrap/curator-roster.json"
AVATARS = ROOT / "frontend/public"
TARGET = ROOT / "python/src/pkdb/data/curators.json"
TARGET_AVATARS = ROOT / "python/src/pkdb/curation/static/avatars"


def build():
    """Return the bundled profile JSON and avatar files by name."""
    curators, files = [], {}
    for user in json.loads(ROSTER.read_text(encoding="utf-8"))["users"]:
        avatar = None
        if user.get("avatar"):
            source = AVATARS / user["avatar"]["url"].lstrip("/")
            avatar = source.name
            files[avatar] = source.read_bytes()
        curators.append(
            {
                "username": user["username"],
                "display_name": user.get("display_name") or user["username"],
                "title": user.get("title"),
                "affiliation": user.get("affiliation"),
                "avatar": avatar,
            }
        )
    curators.sort(key=lambda item: item["username"].lower())
    content = (
        json.dumps(
            {"schema_version": 1, "curators": curators}, indent=2, ensure_ascii=False
        )
        + "\n"
    )
    return content, files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content, files = build()
    existing = (
        {path.name: path.read_bytes() for path in TARGET_AVATARS.iterdir()}
        if TARGET_AVATARS.is_dir()
        else {}
    )
    if args.check:
        if (
            not TARGET.exists()
            or TARGET.read_text(encoding="utf-8") != content
            or existing != files
        ):
            parser.exit(
                1, "Bundled curators are stale; run this script without --check.\n"
            )
        return
    TARGET.write_text(content, encoding="utf-8")
    TARGET_AVATARS.mkdir(parents=True, exist_ok=True)
    for name in existing.keys() - files.keys():
        (TARGET_AVATARS / name).unlink()
    for name, data in files.items():
        (TARGET_AVATARS / name).write_bytes(data)


if __name__ == "__main__":
    main()
