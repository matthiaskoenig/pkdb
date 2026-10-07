"""Persistent local workspace, settled file watching, and serialized scientific jobs."""

import json
import os
import threading
from pathlib import Path

from pkdb import __version__
from pkdb.cache import (
    VocabularyCache,
    atomic_json,
    cache_directory,
    endpoint_root,
)
from pkdb.curation.connection import ConnectionMixin
from pkdb.curation.github import GitHubAssignments
from pkdb.curation.issues import IssuesMixin
from pkdb.curation.jobs import JobsMixin, fingerprint, now
from pkdb.curation.studies import StudiesMixin
from pkdb.curation.workspace import (
    RECENT_LIMIT,
    WorkspaceError,
    WorkspaceMixin,
    folder_kind,
)
from pkdb.identity import IdentityError
from pkdb.update import newer

__all__ = ["CurationEngine", "WorkspaceError", "fingerprint", "folder_kind", "now"]


class CurationEngine(
    WorkspaceMixin, JobsMixin, ConnectionMixin, IssuesMixin, StudiesMixin
):
    def __init__(
        self,
        path=None,
        endpoint=None,
        github_user=None,
        repository=None,
        offline=False,
        state_dir=None,
        api_key=None,
        user=None,
        start=True,
    ):
        self.lock = threading.RLock()
        self.scan_lock = threading.Lock()
        self._connection_generation = 0
        self.stop = threading.Event()
        self.wakeup = threading.Event()
        self.state_dir = (
            Path(state_dir or cache_directory() / "curation").expanduser().resolve()
        )
        self.state_dir.mkdir(parents=True, exist_ok=True)
        try:
            saved = json.loads((self.state_dir / "state.json").read_text())
        except OSError, ValueError:
            saved = {}
        self.api_key = api_key or os.environ.get("PKDB_API_KEY")
        self.user = user or os.environ.get("PKDB_USER") or saved.get("user") or ""
        configured_endpoint = (
            endpoint or os.environ.get("PKDB_ENDPOINT") or saved.get("endpoint")
        )
        self.endpoint = (
            endpoint_root(str(configured_endpoint)) if configured_endpoint else ""
        )
        self.offline = offline
        self.github_user = github_user or saved.get("github_user", "")
        self.repository = (
            repository or saved.get("repository") or "matthiaskoenig/pkdb_data"
        )
        self.github = GitHubAssignments(
            self.repository,
            os.environ.get("GH_TOKEN"),
            saved.get("github") if saved.get("repository") == self.repository else None,
        )
        self.account = None
        self.can_upload = False
        self.connection_error = None
        self.connection_problem = None
        # The refusal of the last connection check when the key is of another account.
        self.user_mismatch = None
        self.connecting = False
        self.checked_at = None
        self.server_version = None
        self.vocabulary = {"status": "offline" if offline else "not_checked"}
        self.cache = VocabularyCache(self.state_dir / "vocabulary")
        self.studies = {}
        self.format1_folders = 0
        # The format of each study folder, by its study.json and its format 2 files.
        self._formats = {}
        self.reference_previews = {}
        self.jobs = saved.get("jobs", [])
        for job in self.jobs:
            if job.get("status") in {"queued", "running"}:
                job["status"] = (
                    "unknown"
                    if job.get("action") == "upload"
                    and job.get("stage") in {"transfer", "upload", "response", "commit"}
                    else "canceled"
                )
                if job["status"] == "unknown":
                    job["persistence"] = "unknown"
                job["message"] = (
                    "Interrupted by previous shutdown; inspect before retrying"
                )
        self.modes = saved.get("modes", {})
        self.recent_workspaces = [
            item for item in saved.get("recent_workspaces", []) if isinstance(item, str)
        ][:RECENT_LIMIT]
        self.paused = False
        self.active = None
        self.queue = {}
        self.root = Path.cwd()
        self.threads = []
        default_workspace = next(
            (
                candidate
                for candidate in (Path.cwd(), *Path.cwd().parents)
                if (candidate / "studies").is_dir()
            ),
            Path.cwd(),
        )
        remembered = saved.get("workspace")
        if path is None and remembered and not Path(remembered).is_dir():
            # A removed or unmounted workspace must not prevent startup.
            remembered = None
        self.select_workspace(path or remembered or default_workspace)
        if start:
            for target in (self._watch, self._worker, self._connect):
                thread = threading.Thread(target=target, daemon=True)
                self.threads.append(thread)
                thread.start()

    def _save(self):
        path = self.state_dir / "state.json"
        state = {
            "workspace": str(self.root),
            "endpoint": self.endpoint,
            "user": self.user,
            "github_user": self.github_user,
            "repository": self.repository,
            "github": self.github.data,
            "modes": self.modes,
            "recent_workspaces": self.recent_workspaces,
            "jobs": self.jobs,
        }
        # The released format 1 app shares the default state directory: keep what it
        # saved and this version does not know, such as its issue mappings.
        try:
            saved = json.loads(path.read_text())
        except OSError, ValueError:
            saved = {}
        if isinstance(saved, dict):
            state = {**saved, **state}
        atomic_json(path, state)

    def snapshot(self):
        with self.lock:
            recent = list(self.recent_workspaces)
        try:
            author = {"user": self.author().user, "reason": None}
        except IdentityError as error:
            author = {"user": None, "reason": str(error)}
        # Existence checks may touch slow mounts, so they run outside the lock.
        recent = [{"path": path, "exists": Path(path).is_dir()} for path in recent]
        with self.lock:
            return json.loads(
                json.dumps(
                    {
                        "workspace": str(self.root),
                        "endpoint": self.endpoint,
                        "user": self.user,
                        # Who writes study files, or why writes are refused.
                        "author": author,
                        "authenticated": bool(self.api_key),
                        "account": self.account,
                        "can_upload": self.can_upload,
                        "connection": self._connection_status(),
                        "connection_error": self.connection_error,
                        "checked_at": self.checked_at,
                        "client_version": __version__,
                        "server_version": self.server_version,
                        "update_required": newer(self.server_version),
                        "offline": self.offline,
                        "paused": self.paused,
                        "vocabulary": self.vocabulary,
                        "github": {
                            **self.github.data,
                            "user": self.github_user,
                            "repository": self.repository,
                        },
                        "studies": [
                            {
                                **{
                                    k: v
                                    for k, v in row.items()
                                    if not k.startswith("_")
                                },
                                "issue": self._issue_for(
                                    (row.get("summary") or {}).get("issue")
                                ),
                            }
                            for row in self.studies.values()
                        ],
                        "format1_folders": self.format1_folders,
                        "jobs": self.jobs,
                        "recent_workspaces": recent,
                    }
                )
            )

    def close(self):
        self.stop.set()
        self.wakeup.set()
        with self.lock:
            self._cancel_pending()
            self._save()
        for thread in self.threads:
            thread.join(timeout=2)
