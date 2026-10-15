"""Curator profiles for the local curation interface.

Curator profiles and avatars come from the bundled public curator roster
(scripts/update_client_curators.py); unknown usernames keep their username.
"""

import json
from functools import cache
from importlib.resources import files


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


def roster() -> list[dict]:
    """The profiles of the bundled curator roster, ordered by username."""
    return [profile(item["username"]) for item in _curators().values()]
