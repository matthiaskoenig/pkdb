"""Typed view of the engine attributes and methods that the engine mixins share.

The attributes are only annotated here; `CurationEngine.__init__` initializes all of them. The
methods are declared for type checking only and are provided by `CurationEngine` and the mixins.
"""

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

from pkdb.cache import VocabularyCache
from pkdb.curation.errors import ErrorLog
from pkdb.curation.github import GitHubAssignments
from pkdb.curation.tree import SourceTree

#: The color themes of the app: the system theme, or one that the curator chose.
THEMES = ("light", "dark", "system")

#: Row fields that only the study page serves: with them, every poll of the state would carry
#: the problems of all studies.
DETAIL_ONLY = frozenset({"problems"})


def state_row(row: dict) -> dict:
    """The fields of a study row in the state of the app: those without a leading
    underscore, except the ones that only the study page serves."""
    return {
        key: value
        for key, value in row.items()
        if not key.startswith("_") and key not in DETAIL_ONLY
    }


class StateLock:
    """The reentrant lock of the state of an engine, which counts the changes of the state.

    `with lock:` is a section that may change the state: when the outermost section of the
    thread that holds the lock ends after one, `revision` grows by one, also after an error.
    `with lock.reading():` only reads and keeps the revision, unless it calls `changed()` or
    enters `with lock:` inside. The local server answers a poll of the state from the revision
    without building the state.

    So a change that no section counts stays hidden behind `304` until an unrelated change.
    Every change of what `CurationEngine.snapshot` returns, by any thread, happens in a
    section that counts it, or is followed by one on every path, also when it fails, as
    `run_job` ends in one after the outcome it writes outside the lock. A reading section
    calls `changed()` only when a value really changes, so that an idle engine keeps its
    revision. What `snapshot` reads from outside the engine is a function of fields that
    only such sections change (`author`, `connection`, `update_required`), fixed for the
    engine (`client_version`, `log_file`), or part of `state_version` (whether each recent
    workspace exists).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # Only the thread that holds the lock changes these; `held` reads the owner.
        self._depth = 0
        self._changed = False
        self._owner: int | None = None
        self.revision = 0

    def __enter__(self) -> StateLock:
        self._acquire()
        self._changed = True
        return self

    def __exit__(self, *_: object) -> None:
        self._release()

    @contextmanager
    def reading(self) -> Iterator[StateLock]:
        self._acquire()
        try:
            yield self
        finally:
            self._release()

    def changed(self) -> None:
        """Count a change of the state in a reading section; called with the lock held."""
        self._changed = True

    def held(self) -> bool:
        """Whether the current thread holds the lock."""
        return self._owner == threading.get_ident()

    def _acquire(self) -> None:
        self._lock.acquire()
        self._depth += 1
        self._owner = threading.get_ident()

    def _release(self) -> None:
        self._depth -= 1
        if self._depth == 0:
            self._owner = None
            if self._changed:
                self._changed = False
                self.revision += 1
        self._lock.release()


class StateVersion(NamedTuple):
    """A version of the state of an engine (`CurationEngine.state_version`)."""

    #: The ETag of the state: the epoch of the engine, the revision of its state, and which
    #: recent workspaces exist.
    tag: str
    #: The recent workspaces with whether each exists, as `tag` has them.
    recent: list[dict]


class JobRunning(Exception):
    """A job of the study runs: it compares the source with the one it started on, so a
    write that the watcher takes as seen would still stop it."""


class EngineState:
    lock: StateLock
    # Tells the versions of the state of this engine from those of an engine before it.
    epoch: str
    scan_lock: threading.Lock
    stop: threading.Event
    wakeup: threading.Event
    state_dir: Path
    root: Path
    api_key: str | None
    user: str
    endpoint: str
    offline: bool
    github_user: str
    repository: str
    # The color theme of the app; the server keeps it, as the browser origin changes with the port.
    theme: str
    github: GitHubAssignments
    account: Any
    can_upload: bool
    connection_error: Any
    connection_problem: Any
    user_mismatch: str | None
    connecting: bool
    checked_at: Any
    server_version: Any
    vocabulary: dict
    cache: VocabularyCache
    studies: dict
    format1_folders: int
    _formats: dict
    _tree: SourceTree | None
    _saved_substances: dict | None
    reference_previews: dict
    jobs: list
    modes: dict
    recent_workspaces: list
    paused: bool
    active: Any
    queue: dict
    threads: list
    _connection_generation: int
    # The log file of failures, and the tokens of the local server that it redacts.
    log: ErrorLog
    protected: list[str]
    # The last failure of the file watcher.
    watcher_error: dict | None

    if TYPE_CHECKING:

        def secrets(self) -> list[str]: ...
        def _save(self) -> None: ...
        def snapshot(self, recent: list[dict] | None = None) -> dict: ...
        def state_version(self) -> StateVersion: ...
        def scan(self, initial: bool = False) -> Any: ...
        def connect(self) -> Any: ...
        def _context(self) -> str: ...
        def _connection_status(self) -> str: ...
        def _vocabulary(self, client: Any, *, generation: Any = None) -> Any: ...
        def _selected(self, ids: Any) -> Any: ...
        def _row_of(self, identifier: Any) -> Any: ...
        def _enqueue_one(
            self, row: Any, action: Any, automatic: bool = False
        ) -> Any: ...
        def _cancel_pending(self, message: str) -> Any: ...
        def refresh_assignments(self) -> Any: ...
        def _issue_for(self, number: Any) -> dict | None: ...
        def _local_vocabulary(self, folder: Path | None = None) -> Any: ...
        def author(self, agent: str | None = None) -> Any: ...
        def _sync_state(self, folder: Path) -> dict: ...
        def _wait(self, row: dict, error: Exception) -> None: ...
        def _sync_later(self, row: dict) -> None: ...
        def _unwatched_write[T](
            self, folder: Path, file: str, write: Callable[[], T]
        ) -> T: ...
        def _record_write(
            self,
            identity: str,
            message: str,
            status: str = "succeeded",
            item: str | None = None,
            error: dict | None = None,
        ) -> str: ...
