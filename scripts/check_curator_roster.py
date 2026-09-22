"""Validate the public curator/profile mapping without accessing private contacts.

Run from any directory: python3 scripts/check_curator_roster.py
This command is read-only and never creates accounts or assigns permissions.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "backend/bootstrap/curator-roster.json"
EXPECTED_REVIEWERS = {"MariiaMysh", "mii-halina", "shubhankarpalwankar"}


def validate() -> dict[str, int]:
    manifest = json.loads(MANIFEST.read_text())
    if manifest["schema_version"] != 1:
        raise ValueError("Unsupported curator roster version")
    users = manifest["users"]
    usernames = [user["username"] for user in users]
    if len(set(usernames)) != len(usernames):
        raise ValueError("Duplicate usernames in curator roster")
    administrators = {user["username"] for user in users if user["role"] == "admin"}
    reviewers = {user["username"] for user in users if user["role"] == "reviewer"}
    if administrators != {"mkoenig"} or reviewers != EXPECTED_REVIEWERS:
        raise ValueError(
            "Roster differs from the explicitly authorized privileged roles"
        )
    forbidden = {
        "email",
        "primary_email",
        "secondary_email",
        "password",
        "password_hash",
        "api_key",
        "token",
    }

    def reject_private_fields(value: object) -> None:
        if isinstance(value, dict):
            if forbidden.intersection(value):
                raise ValueError("Private contact or credential field in public roster")
            for child in value.values():
                reject_private_fields(child)
        elif isinstance(value, list):
            for child in value:
                reject_private_fields(child)

    reject_private_fields(manifest)
    counts = {
        "accounts": len(users),
        "site_avatars": 0,
        "legacy_avatars": 0,
        "fallbacks": 0,
    }
    for user in users:
        username = user["username"]
        if user["role"] not in {"user", "curator", "reviewer", "admin"}:
            raise ValueError(f"Unknown role for {username}")
        expected_policy = (
            "administrator_bootstrap"
            if username == "mkoenig"
            else "exclude_test_account"
            if username == "reviewer"
            else "reviewed_invitation"
        )
        if user["import_policy"] != expected_policy:
            raise ValueError(f"Unsafe import policy for {username}")
        if username == "reviewer" and user["role"] != "user":
            raise ValueError("Historical test account must not receive privileges")
        avatar = user["avatar"]
        if avatar is None:
            counts["fallbacks"] += 1
            continue
        url = avatar["url"]
        if not url.startswith("/assets/images/avatars/"):
            raise ValueError(f"Nonlocal avatar for {username}")
        avatar_root = (ROOT / "frontend/public/assets/images/avatars").resolve()
        path = (ROOT / "frontend/public" / url.lstrip("/")).resolve()
        if not path.is_relative_to(avatar_root):
            raise ValueError(f"Avatar escapes its directory for {username}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != avatar["sha256"]:
            raise ValueError(f"Avatar checksum mismatch for {username}")
        counts[
            "site_avatars" if "source_person_id" in avatar else "legacy_avatars"
        ] += 1
    return counts


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
