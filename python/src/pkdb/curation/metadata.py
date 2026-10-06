"""Key study and reference metadata for the local curation interface.

Curator profiles and avatars come from the bundled public curator roster
(scripts/update_client_curators.py); unknown usernames keep their username.
"""

import json
from functools import cache
from importlib.resources import files
from pathlib import Path


@cache
def _curators() -> dict[str, dict]:
    data = json.loads(
        files("pkdb").joinpath("data/curators.json").read_text(encoding="utf-8")
    )
    return {item["username"].lower(): item for item in data["curators"]}


def profile(username: str) -> dict:
    known = _curators().get(username.lower(), {})
    avatar = known.get("avatar")
    return {
        "username": known.get("username", username),
        "display_name": known.get("display_name", username),
        "title": known.get("title"),
        "affiliation": known.get("affiliation"),
        "avatar_url": f"/avatars/{avatar}" if avatar else None,
    }


def _text(value) -> str | None:
    if isinstance(value, bool) or not isinstance(value, str | int | float):
        return None
    return str(value)


def _author(value) -> str | None:
    if not isinstance(value, dict):
        return None
    name = " ".join(
        part
        for part in (value.get("first_name"), value.get("last_name"))
        if isinstance(part, str) and part.strip()
    )
    organization = value.get("organization")
    return name or (organization if isinstance(organization, str) else None) or None


def reference_summary(folder: Path) -> dict | None:
    path = Path(folder) / "reference.json"
    if not path.is_file() or path.is_symlink():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError, OSError:
        return {"error": "reference.json is not valid JSON"}
    if not isinstance(data, dict):
        return {"error": "reference.json is not valid JSON"}
    authors = data.get("authors")
    return {
        **{
            key: _text(data.get(key))
            for key in ("sid", "pmid", "doi", "title", "journal", "abstract")
        },
        "publication_date": _text(data.get("publication_date") or data.get("date")),
        "authors": [
            name
            for name in map(_author, authors if isinstance(authors, list) else [])
            if name
        ],
    }
