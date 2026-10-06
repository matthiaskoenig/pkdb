"""Revisions of study files and the lock that serializes writes to a study folder.

A revision is the SHA-256 of a file's bytes. A writer passes the revision it
read; the write is refused when the file changed since. The lock serializes
writers in one process; a writer in another process is caught by the revision
check, except in the instant between check and replace.
"""

import hashlib
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pkdb.cache import atomic_text

ABSENT = "absent"
_locks: dict[Path, threading.Lock] = {}
_guard = threading.Lock()


class RevisionConflict(Exception):
    """A file changed on disk since the caller read it; `content` is its current text."""

    def __init__(self, file: str, expected: str, current: str, content: str | None):
        super().__init__(f"{file} changed on disk since it was read")
        self.file, self.expected, self.current, self.content = (
            file,
            expected,
            current,
            content,
        )


def revision_of(data: bytes | None) -> str:
    return ABSENT if data is None else hashlib.sha256(data).hexdigest()


def read_revision(path: Path) -> tuple[bytes | None, str]:
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        data = None
    return data, revision_of(data)


@contextmanager
def folder_lock(folder: Path) -> Iterator[None]:
    key = Path(folder).resolve()
    with _guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:
        yield


def write_checked(path: Path, text: str, expected: str | None) -> str:
    """Replace a file atomically when its revision is still `expected`; the new revision."""
    data, current = read_revision(path)
    if expected is not None and expected != current:
        content = None if data is None else data.decode("utf-8", "replace")
        raise RevisionConflict(path.name, expected, current, content)
    atomic_text(path, text)
    return revision_of(text.encode("utf-8"))
