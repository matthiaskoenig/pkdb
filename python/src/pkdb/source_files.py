"""Source files of a study folder: editor files to ignore, attachments and digest."""

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

CHUNK = 1024 * 1024


def ignored_source(path: Path) -> bool:
    name = path.name
    return (
        ".git" in path.parts
        or name in {".DS_Store", "Thumbs.db", "desktop.ini"}
        or name.startswith("~$")
        or (name.startswith(".~lock.") and name.endswith("#"))
        or (name.startswith(".") and name.endswith((".swp", ".swo")))
    )


def attachments_and_digest(
    study: object, reference: object, files: Mapping[str, Path]
) -> tuple[list[dict], str]:
    """Attachments (name, size, sha256) of the files and the digest of the source.

    The digest covers the parsed study and reference JSON and every file by
    name and content, in name order, so equal sources have equal digests.
    """
    digest = hashlib.sha256(
        json.dumps(
            {"study": study, "reference": reference}, sort_keys=True, allow_nan=False
        ).encode()
    )
    attachments = []
    for name, file in sorted(files.items()):
        content = hashlib.sha256()
        with file.open("rb") as stream:
            for chunk in iter(lambda: stream.read(CHUNK), b""):
                content.update(chunk)
        attachments.append(
            {"name": name, "size": file.stat().st_size, "sha256": content.hexdigest()}
        )
        digest.update(name.encode())
        digest.update(content.digest())
    return attachments, digest.hexdigest()
