"""Persist retrieval times and apply PK-DB's public metadata cache policy."""

from __future__ import annotations

import json
import socket
import time
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from functools import cache as memoize
from json import JSONEncoder
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pymetadata
from pymetadata.core import annotation
from pymetadata.webservices import chebi, ols, registry, unichem
from pymetadata.webservices.webservice import WebserviceError, get_json

import info_nodes

TERM_HOURS = 60 * 24
REGISTRY_HOURS = 24
DAILY_FILES = {"identifiers_registry.json", "unichem_sources.json"}


class MetadataCache:
    """Cache JSON with retrieval timestamps independent of filesystem mtimes."""

    def __init__(
        self,
        root: Path,
        *,
        offline: bool = False,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.root = root
        self.offline = offline
        self.clock = clock
        self.manifest = root / "manifest.json"
        data = json.loads(self.manifest.read_text()) if self.manifest.exists() else {}
        self.entries: dict[str, dict[str, float]] = data.get("entries", {})
        self.failures: dict[str, str] = data.get("failures", {})
        self.misses: set[str] = set()
        self.requests = 0

    def age(self, cache_path: Path) -> float | None:
        """Return elapsed hours since retrieval, never since checkout."""
        if not cache_path.is_file():
            return None
        if self.offline:
            return 0
        entry = self.entries.get(cache_path.relative_to(self.root).as_posix())
        if entry is None:
            return None
        age = (self.clock() - entry["fetched_at"]) / 3600
        return age if age >= 0 else None

    def read(self, cache_path: Path, max_age: float | None = None) -> Any:
        """Read offline data, or require the applicable online cache lifetime."""
        age = self.age(cache_path)
        lifetime = REGISTRY_HOURS if cache_path.name in DAILY_FILES else TERM_HOURS
        if age is None or (not self.offline and age >= lifetime):
            raise OSError(f"Metadata cache missing or expired: {cache_path}")
        return json.loads(cache_path.read_text())

    def invalidate_expired(self) -> None:
        """Remove stale staged responses so offline replay cannot resurrect them."""
        if self.offline:
            return
        for path in self.root.rglob("*.json"):
            if path == self.manifest:
                continue
            age = self.age(path)
            lifetime = REGISTRY_HOURS if path.name in DAILY_FILES else TERM_HOURS
            if age is None or age >= lifetime:
                path.unlink()
                self.entries.pop(path.relative_to(self.root).as_posix(), None)

    def fallback(self, cache_path: Path, reason: str) -> Any:
        """Never conceal refresh failures by accepting expired online data."""
        try:
            return self.read(cache_path)
        except OSError, ValueError:
            return None

    def write(
        self,
        data: Any,
        cache_path: Path,
        json_encoder: type[JSONEncoder] | None = None,
    ) -> None:
        """Write a fetched response and remember its retrieval time."""
        if self.offline:
            raise OSError("Cannot write metadata while offline")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data, indent=2, cls=json_encoder) + "\n")
        key = cache_path.relative_to(self.root).as_posix()
        self.entries[key] = {"fetched_at": self.clock()}

    def fetch(self, url: str, **kwargs: Any) -> Any:
        """Fetch fresh public data, or report a deterministic offline miss."""
        if self.offline:
            self.misses.add(url)
            raise WebserviceError(
                self.failures.get(url, "No cached metadata; refresh the source cache")
            )
        self.requests += 1
        try:
            result = get_json(url, **kwargs)
        except WebserviceError as error:
            self.misses.add(url)
            self.failures[url] = str(error)
            raise
        self.failures.pop(url, None)
        return result

    def save(self) -> None:
        """Persist timestamps and lookup failures for reproducible offline builds."""
        if self.offline:
            return
        self.root.mkdir(parents=True, exist_ok=True)
        self.manifest.write_text(
            json.dumps(
                {"version": 1, "entries": self.entries, "failures": self.failures},
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )


@contextmanager
def use_metadata_cache(root: Path, *, offline: bool) -> Iterator[MetadataCache]:
    """Scope pymetadata's service hooks and singleton state to one compilation."""
    from info_nodes import node

    cache = MetadataCache(root, offline=offline)
    cache.invalidate_expired()

    def forbid_network(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Network forbidden during offline vocabulary generation")

    def registry_age(path: Path) -> float | None:
        age = cache.age(path)
        return 0 if age is not None and age < REGISTRY_HOURS else None

    with ExitStack() as stack:
        for module in (pymetadata, info_nodes):
            stack.enter_context(patch.object(module, "CACHE_PATH", root))
        stack.enter_context(patch.object(node, "CACHE_PATH", root))
        stack.enter_context(
            patch.object(
                node, "resolve_annotation", memoize(node.resolve_annotation.__wrapped__)
            )
        )
        stack.enter_context(patch.object(registry, "_REGISTRY", None))
        # FMA now publishes canonical sig/ont IRIs, rather than the old OBO IRIs.
        ontologies = [
            ols.OLSOntology("fma", "http://purl.org/sig/ont/fma/fma{$Id}")
            if item.name == "fma"
            else item
            for item in ols.ONTOLOGIES
        ]
        stack.enter_context(
            patch.object(annotation, "_OLS_QUERY", ols.OLSQuery(ontologies, root))
        )
        stack.enter_context(patch.object(unichem.UnichemQuery, "sources", {}))
        for module in (registry, chebi, unichem, ols):
            for name, function in (
                ("read_json_cache", cache.read),
                ("write_json_cache", cache.write),
                ("read_json_cache_fallback", cache.fallback),
                ("get_json", cache.fetch),
            ):
                stack.enter_context(patch.object(module, name, function))
            if hasattr(module, "cache_age"):
                # Registry refreshes when age > 24; treat the exact boundary as a miss.
                stack.enter_context(patch.object(module, "cache_age", registry_age))
        if offline:
            stack.enter_context(patch.object(socket.socket, "connect", forbid_network))
            stack.enter_context(
                patch.object(socket.socket, "connect_ex", forbid_network)
            )
        try:
            yield cache
        finally:
            cache.save()
