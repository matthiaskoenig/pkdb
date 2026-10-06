"""Explicit, content-addressed offline vocabulary snapshots."""

import hashlib
import json
import os
import secrets
import stat
import sys
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from pkdb.domain.vocabulary import Vocabulary, vocabulary_hash


def endpoint_root(value: str) -> str:
    url = urlsplit(value)
    if (
        url.scheme not in {"http", "https"}
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise ValueError(
            "Endpoint must be an HTTP(S) URL without credentials, query, or fragment"
        )
    # Reject invalid ports here, before any request is attempted.
    _ = url.port
    path = url.path.rstrip("/")
    if path.endswith(("/api/v1", "/api/v2")):
        path = path[:-7]
    return urlunsplit((url.scheme.lower(), url.netloc.lower(), path, "", ""))


def vocabulary_envelope(vocabulary: Vocabulary) -> dict:
    return {
        "schema_version": 1,
        "vocabulary": vocabulary.model_dump(mode="json"),
        "vocabulary_hash": vocabulary_hash(vocabulary),
    }


def parse_vocabulary(value: dict) -> Vocabulary:
    if value.get("schema_version") != 1:
        raise ValueError("Unsupported vocabulary snapshot schema")
    vocabulary = Vocabulary.model_validate(value.get("vocabulary"))
    if value.get("vocabulary_hash") != vocabulary_hash(vocabulary):
        raise ValueError("Vocabulary snapshot hash does not match its contents")
    return vocabulary


def _create_temporary(folder: Path) -> tuple[int, Path]:
    """Create a new file next to the target.

    Unlike NamedTemporaryFile, which creates files with mode 0600, the mode 0666
    lets the process umask decide the permissions, as for any new file.
    """
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    for _ in range(100):
        temporary = folder / f".tmp{secrets.token_hex(8)}"
        try:
            return os.open(temporary, flags, 0o666), temporary
        except FileExistsError:
            continue
    raise FileExistsError(f"Cannot create a temporary file in {folder}")


def atomic_bytes(path: Path, data: bytes) -> None:
    """Replace a file atomically; the primitive of all atomic writes.

    The data is written and fsynced to a temporary file next to the target, which
    takes the permissions of the file it replaces and then replaces it. The
    directory is fsynced on POSIX. On failure the target keeps its old content
    and the temporary file is removed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        descriptor, temporary = _create_temporary(path.parent)
        with open(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            # Keep the permissions of the file that is replaced.
            temporary.chmod(stat.S_IMODE(path.stat().st_mode))
        temporary.replace(path)
        if os.name == "posix":
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def atomic_text(path: Path, text: str) -> None:
    """Replace a file atomically with UTF-8 text; newlines are written as given, never translated."""
    atomic_bytes(path, text.encode("utf-8"))


def atomic_json(path: Path, value: dict) -> None:
    atomic_text(
        path, json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    )


def load_vocabulary(path: str | Path) -> Vocabulary:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected a vocabulary snapshot object")
    return parse_vocabulary(value)


def bundled_vocabulary() -> Vocabulary:
    return parse_vocabulary(
        json.loads(
            files("pkdb").joinpath("data/vocabulary.json").read_text(encoding="utf-8")
        )
    )


def cache_directory() -> Path:
    if value := os.environ.get("PKDB_CACHE_DIR"):
        return Path(value)
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
    elif sys.platform == "darwin":
        root = Path.home() / "Library/Caches"
    else:
        root = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    return root / "pkdb"


class VocabularyCache:
    def __init__(self, directory: str | Path | None = None):
        self.directory = Path(directory) if directory is not None else cache_directory()

    def _pointer(self, endpoint: str) -> Path:
        key = hashlib.sha256(endpoint_root(endpoint).encode()).hexdigest()
        return self.directory / "endpoints" / f"{key}.json"

    def store(self, endpoint: str, vocabulary: Vocabulary) -> Path:
        digest = vocabulary_hash(vocabulary)
        path = self.directory / "snapshots" / f"{digest}.json"
        atomic_json(path, vocabulary_envelope(vocabulary))
        atomic_json(self._pointer(endpoint), {"vocabulary_hash": digest})
        return path

    def load(self, endpoint: str) -> Vocabulary:
        value = json.loads(self._pointer(endpoint).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Invalid vocabulary cache index")
        digest = value.get("vocabulary_hash")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
        ):
            raise ValueError("Invalid vocabulary cache index")
        try:
            vocabulary = load_vocabulary(
                self.directory / "snapshots" / f"{digest}.json"
            )
        except FileNotFoundError:
            raise ValueError(
                "Cached vocabulary snapshot is missing; synchronize again"
            ) from None
        if vocabulary_hash(vocabulary) != digest:
            raise ValueError("Vocabulary cache index does not match snapshot")
        return vocabulary


def select_vocabulary(
    path: str | Path | None, endpoint: str | None, cache: VocabularyCache
) -> Vocabulary:
    """The vocabulary that validates studies, without contacting a server.

    A pinned snapshot file comes first, then the cached vocabulary of the
    endpoint, and otherwise the vocabulary bundled with the client.
    """
    if path:
        return load_vocabulary(path)
    if endpoint:
        try:
            return cache.load(endpoint)
        except FileNotFoundError:
            pass
    return bundled_vocabulary()
