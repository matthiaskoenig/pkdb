"""Persistent local workspace, settled file watching, and serialized scientific jobs."""

import json
import os
import re
import threading
from pathlib import Path
from secrets import token_hex

from pkdb import __version__
from pkdb.cache import (
    VocabularyCache,
    atomic_json,
    cache_directory,
    endpoint_root,
)
from pkdb.curation.connection import ConnectionMixin
from pkdb.curation.errors import ErrorLog
from pkdb.curation.github import GitHubAssignments
from pkdb.curation.issues import IssuesMixin
from pkdb.curation.jobs import (
    CANCELED_BEFORE_START,
    JobsMixin,
    fingerprint,
    maybe_sent,
    now,
)
from pkdb.curation.plot_scales import saved_plot_scales
from pkdb.curation.state import THEMES, StateLock, StateVersion, state_row
from pkdb.curation.studies import StudiesMixin
from pkdb.curation.workspace import (
    RECENT_LIMIT,
    WorkspaceError,
    WorkspaceMixin,
    folder_kind,
)
from pkdb.identity import IdentityError
from pkdb.issues.github import token_from
from pkdb.studyformat.substances import folder_index, folder_substances
from pkdb.update import newer

__all__ = ["CurationEngine", "WorkspaceError", "fingerprint", "folder_kind", "now"]

# How write jobs saved before they recorded `item` name their review item in the message,
# "Added review item <id>" (`_item_reference` in studies.py).
SAVED_ITEM = re.compile(r"review item (\S+)")


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
        self.lock = StateLock()
        # Tells the versions of the state of this engine from those of an engine before it.
        self.epoch = token_hex(4)
        self.scan_lock = threading.Lock()
        self._connection_generation = 0
        self.stop = threading.Event()
        self.wakeup = threading.Event()
        self.state_dir = (
            Path(state_dir or cache_directory() / "curation").expanduser().resolve()
        )
        self.state_dir.mkdir(parents=True, exist_ok=True)
        try:
            saved = json.loads(
                (self.state_dir / "state.json").read_text(encoding="utf-8")
            )
        except OSError, ValueError:
            saved = {}
        self.api_key = api_key or os.environ.get("PKDB_API_KEY")
        # The tokens of the local server, which error bodies, reports and the log never show.
        self.protected: list[str] = []
        self.log = ErrorLog(self.state_dir / "logs" / "curation.log", self.secrets)
        # The last failure of the file watcher, which the File watching menu shows.
        self.watcher_error = None
        self.user = user or os.environ.get("PKDB_USER") or saved.get("user") or ""
        configured_endpoint = (
            endpoint or os.environ.get("PKDB_ENDPOINT") or saved.get("endpoint")
        )
        self.endpoint = (
            endpoint_root(str(configured_endpoint)) if configured_endpoint else ""
        )
        self.offline = offline
        self.github_user = github_user or saved.get("github_user", "")
        theme = saved.get("theme")
        self.theme = theme if isinstance(theme, str) and theme in THEMES else "system"
        self.plot_scales = saved_plot_scales(saved.get("plot_scales"))
        self.repository = (
            repository or saved.get("repository") or "matthiaskoenig/pkdb_data"
        )
        self.github = GitHubAssignments(
            self.repository,
            token_from(),
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
        # The listings of the folders of the workspace, which scans reuse while unchanged.
        self._tree = None
        # The substances that the watcher last saved in the state directory; None until its
        # first save, which also drops the entries of studies that are gone.
        self._saved_substances = None
        self.reference_previews = {}
        self.jobs = saved.get("jobs", [])
        for job in self.jobs:
            if job.get("status") in {"queued", "running"}:
                if maybe_sent(job):
                    # The server may have saved the study: the curator inspects it first.
                    job.update(
                        status="unknown",
                        persistence="unknown",
                        message="Interrupted by previous shutdown; inspect before retrying",
                    )
                else:
                    job.update(
                        status="canceled", message="Canceled when pkdb curate stopped"
                    )
            elif (
                job.get("status") == "failed"
                and job.get("message") == "Validation found problems"
            ):
                # Saved before problems found had a status of their own.
                job["status"] = "invalid"
            elif job.get("status") == "canceled" and job.get("message") in {
                # Earlier versions kept the message of a queued job when canceling it, and
                # named a job that the curator canceled in other words.
                "Queued",
                "Canceled before starting",
            }:
                job["message"] = CANCELED_BEFORE_START
            if (
                job.get("action") == "write"
                and "item" not in job
                and "error" not in job
                and job.get("status") == "succeeded"
            ):
                # Saved before writes recorded the review item that their message names;
                # a failure names none, whatever its message says.
                if found := SAVED_ITEM.search(job.get("message", "")):
                    job["item"] = found.group(1)
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
            "theme": self.theme,
            "plot_scales": self.plot_scales,
            "github": self.github.data,
            "modes": self.modes,
            "recent_workspaces": self.recent_workspaces,
            "jobs": self.jobs,
        }
        # The released format 1 app shares the default state directory: keep what it
        # saved and this version does not know, such as its issue mappings.
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
        except OSError, ValueError:
            saved = {}
        if isinstance(saved, dict):
            state = {**saved, **state}
        atomic_json(path, state)

    def secrets(self) -> list[str]:
        """What error bodies, reports and the log replace with [redacted]: the API key, the
        GitHub tokens of the environment and the tokens that the local server protects."""
        values = [
            self.api_key,
            os.environ.get("GH_TOKEN"),
            os.environ.get("GITHUB_TOKEN"),
            *self.protected,
        ]
        return [value for value in values if value]

    def protect(self, *values: str) -> None:
        """Add tokens, such as the session token of the local server, to the secrets."""
        self.protected.extend(value for value in values if value)

    def snapshot(self, recent: list[dict] | None = None):
        """The state of the app. `recent` is the recent workspaces with whether each exists,
        as a `StateVersion` has them; without it, they are checked now."""
        if recent is None:
            recent = self._recent()[1]
        try:
            author = {"user": self.author().user, "reason": None}
        except IdentityError as error:
            author = {"user": None, "reason": str(error)}
        with self.lock.reading():
            # The substance folders of the workspace, by which a study is also found.
            folders = folder_index(row["substance"] for row in self.studies.values())
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
                        "theme": self.theme,
                        "plot_scales": {
                            figure: dict(scales)
                            for figure, scales in self.plot_scales.items()
                        },
                        "vocabulary": self.vocabulary,
                        "github": {
                            **self.github.data,
                            "user": self.github_user,
                            "repository": self.repository,
                        },
                        "studies": [
                            {
                                **state_row(row),
                                # The folder substance, then the other substance folders
                                # that the tables name, as the watcher last read them.
                                "substances": folder_substances(
                                    row["substance"], row["_named_substances"], folders
                                ),
                                "issue": self._issue_for(
                                    (row.get("summary") or {}).get("issue")
                                ),
                            }
                            for row in self.studies.values()
                        ],
                        "format1_folders": self.format1_folders,
                        "jobs": self.jobs,
                        # What Clear finished history would remove.
                        "clearable_jobs": len(self._clearable()),
                        "recent_workspaces": recent,
                        # Where the traceback of a failure is, for the Details of the app.
                        "log_file": str(self.log.path),
                        "watcher_error": self.watcher_error,
                    }
                )
            )

    def _recent(self) -> tuple[int, list[dict]]:
        """The revision of the state, and the recent workspaces with whether each exists."""
        with self.lock.reading():
            revision, recent = self.lock.revision, list(self.recent_workspaces)
        # Existence checks may touch slow mounts, so they run outside the lock.
        return revision, [
            {"path": path, "exists": Path(path).is_dir()} for path in recent
        ]

    def state_version(self) -> StateVersion:
        """A version of `snapshot`, cheap enough for every poll: the epoch of the engine, the
        revision of its state, and which recent workspaces exist, which no section of the lock
        sees change. Read before building the state, so the state is at least as new; the
        state built with `snapshot(version.recent)` has the recent workspaces as the version
        has them, also when a mount comes and goes meanwhile."""
        revision, recent = self._recent()
        exists = "".join("1" if item["exists"] else "0" for item in recent)
        return StateVersion(f"{self.epoch}-{revision}-{exists}", recent)

    def close(self):
        self.stop.set()
        self.wakeup.set()
        with self.lock:
            self._cancel_pending("Canceled when pkdb curate stopped")
            self._save()
        for thread in self.threads:
            thread.join(timeout=2)
        self.log.close()
