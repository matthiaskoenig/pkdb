"""Source files of a study folder: editor files to ignore, attachments and digest."""

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path

CHUNK = 1024 * 1024
# The temporary files of pkdb.cache.atomic_bytes, next to the files they replace.
TEMPORARY_FILE = re.compile(r"\.tmp[0-9a-f]{16}")


def below_hidden_folder(path: Path) -> bool:
    """Whether a relative file path lies below a folder whose name starts with a dot."""
    return any(part.startswith(".") for part in path.parts[:-1])


def ignored_source(path: Path) -> bool:
    return ".git" in path.parts or ignored_name(path.name)


def ignored_name(name: str) -> bool:
    """Whether a source file or folder name is one that sources ignore, by the name alone.

    Everything below a `.git` folder is ignored as well; `ignored_source` checks the whole path.
    """
    if name in {".DS_Store", "Thumbs.db", "desktop.ini"} or name.startswith("~$"):
        return True
    # The other names start with a dot; scans of large workspaces check every name.
    return name.startswith(".") and (
        name == ".git"
        or (name.startswith(".~lock.") and name.endswith("#"))
        or name.endswith((".swp", ".swo"))
        or TEMPORARY_FILE.fullmatch(name) is not None
        # The state files of the workbook sync, such as .Example.xlsx.pkdb-base.
        or name.endswith(".pkdb-base")
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
