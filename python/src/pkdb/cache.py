"""Explicit, content-addressed offline vocabulary snapshots."""

import hashlib
import json
import os
import sys
from importlib.resources import files
from pathlib import Path
from tempfile import NamedTemporaryFile
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


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, allow_nan=False, indent=2)
            handle.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


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
