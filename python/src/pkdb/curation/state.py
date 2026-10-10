"""Typed view of the engine attributes and methods that the engine mixins share.

The attributes are only annotated here; `CurationEngine.__init__` initializes all of them. The
methods are declared for type checking only and are provided by `CurationEngine` and the mixins.
"""

import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pkdb.cache import VocabularyCache
from pkdb.curation.github import GitHubAssignments
from pkdb.curation.tree import SourceTree

#: The color themes of the app: the system theme, or one that the curator chose.
THEMES = ("light", "dark", "system")


class EngineState:
    lock: threading.RLock
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
    reference_previews: dict
    jobs: list
    modes: dict
    recent_workspaces: list
    paused: bool
    active: Any
    queue: dict
    threads: list
    _connection_generation: int

    if TYPE_CHECKING:

        def _save(self) -> None: ...
        def snapshot(self) -> dict: ...
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
        def _record_write(
            self,
            identity: str,
            message: str,
            status: str = "succeeded",
            item: str | None = None,
        ) -> None: ...
