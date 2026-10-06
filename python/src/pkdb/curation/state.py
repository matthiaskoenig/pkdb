"""Typed view of the engine attributes and methods that the engine mixins share.

The attributes are only annotated here; `CurationEngine.__init__` initializes all of them. The
methods are declared for type checking only and are provided by `CurationEngine` and the mixins.
"""

import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pkdb.cache import VocabularyCache
from pkdb.curation.github import GitHubAssignments


class EngineState:
    lock: threading.RLock
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
    github: GitHubAssignments
    account: Any
    can_upload: bool
    connection_error: Any
    connection_problem: Any
    connecting: bool
    checked_at: Any
    server_version: Any
    vocabulary: dict
    cache: VocabularyCache
    studies: dict
    format1_folders: int
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
        def _cancel_pending(self) -> Any: ...
        def refresh_assignments(self) -> Any: ...
        def _issue_for(self, number: Any) -> dict | None: ...
        def _local_vocabulary(self) -> Any: ...
        def _sync_state(self, folder: Path) -> dict: ...
        def _sync_later(self, row: dict) -> None: ...
