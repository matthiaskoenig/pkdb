"""Server connection state and checks for the curation engine.

Reads and writes engine attributes: lock, endpoint, api_key, user, account, can_upload,
connection_error, connection_problem, user_mismatch, connecting, checked_at, server_version, vocabulary, cache,
offline, github, github_user, repository, stop, wakeup, _connection_generation. Uses engine
methods _save, snapshot and scan.
"""

import os

from pkdb.cache import (
    endpoint_root,
)
from pkdb.client import Client
from pkdb.curation.github import GitHubAssignments
from pkdb.curation.jobs import now
from pkdb.curation.state import THEMES, EngineState
from pkdb.domain.validation import PROCESSING_VERSION
from pkdb.domain.vocabulary import vocabulary_hash
from pkdb.errors import ClientError, CompatibilityError
from pkdb.identity import Author, UserMismatch, resolve_author

HEARTBEAT_SECONDS = 30
INCOMPATIBLE = {"processing_version_mismatch", "unsupported_protocol"}
CONNECTION_FAILED = "Could not verify the server account or vocabulary. Check endpoint, key, and server version."


def _connection_problem(error, endpoint):
    """Classify a failed server check and explain it in actionable terms."""
    if error.code == "user_mismatch":
        return "unauthorized", str(error)
    if error.code in INCOMPATIBLE:
        return (
            "incompatible",
            f"{error}. Run `pkdb update` and restart the curation service.",
        )
    if error.status_code in {401, 403}:
        return (
            "unauthorized",
            "The server rejected the API key. Check the key in Connection settings.",
        )
    if isinstance(error, CompatibilityError):
        return "error", f"{error}."
    if error.code == "unreachable":
        return (
            "error",
            f"Cannot reach {endpoint}. Check the server address and your network.",
        )
    if error.status_code is not None and error.status_code >= 500:
        return (
            "error",
            f"The PK-DB server or its database is unavailable (HTTP {error.status_code}).",
        )
    return "error", CONNECTION_FAILED


class ConnectionMixin(EngineState):
    def _connection_status(self):
        if self.offline:
            return "offline"
        if not self.endpoint:
            return "not_configured"
        if self.connection_error:
            return self.connection_problem or "error"
        if self.connecting or self.checked_at is None:
            return "connecting"
        return "connected"

    def _context(self):
        return f"{self.root}|{self.endpoint}|{self.account or ''}"

    def author(self, agent: str | None = None) -> Author:
        """Who writes study files from the app (spec 7.4), resolved as the CLI resolves it.

        The authenticated account when an API key is configured and the last connection check
        succeeded, otherwise the configured user. UserMismatch when the last check found that
        the key belongs to another account; IdentityError without a usable user.
        """
        with self.lock:
            checked = (
                self.api_key
                and self.account
                and self.checked_at is not None
                and not self.connection_error
            )
            account = self.account if checked else None
            mismatch = self.user_mismatch
            user, endpoint, api_key = self.user, self.endpoint, self.api_key
            offline = self.offline

        def last_check(*_):
            # The heartbeat checks the key; a write never waits for the server.
            if mismatch:
                raise UserMismatch(mismatch)
            return account

        return resolve_author(
            user,
            agent,
            endpoint=endpoint,
            api_key=api_key,
            offline=offline,
            environ={},
            check=last_check,
            hint="set it in Connection settings",
        )

    def configure(
        self,
        endpoint=None,
        api_key=None,
        user=None,
        github_user=None,
        offline=None,
        repository=None,
        theme=None,
    ):
        with self.lock:
            changed = (
                endpoint is not None
                or api_key is not None
                or offline is not None
                or (user is not None and user != self.user)
            )
            if self.active and changed:
                raise ValueError("Wait for the running job before changing connection")
            if offline is not None and not isinstance(offline, bool):
                raise ValueError("Offline must be true or false")
            if api_key is not None and not isinstance(api_key, str):
                raise ValueError("API key must be text")
            if user is not None and not isinstance(user, str):
                raise ValueError("PK-DB user must be text")
            if theme is not None and theme not in THEMES:
                raise ValueError("Theme must be light, dark or system")
            resolved_endpoint = (
                self.endpoint
                if endpoint is None
                else (endpoint_root(endpoint) if endpoint else "")
            )
            github = self.github
            if repository is not None and repository != self.repository:
                github = GitHubAssignments(repository, os.environ.get("GH_TOKEN"))
            if (
                github_user is not None
                and github_user
                and github_user
                not in {u["login"] for u in github.data.get("users", [])}
            ):
                raise ValueError("Select a user from the available GitHub users")
            if changed:
                self._connection_generation += 1
                self._cancel_pending("Canceled when the connection settings changed")
                self.account = None
                self.can_upload = False
                self.connection_error = None
                self.connection_problem = None
                self.user_mismatch = None
                self.checked_at = None
                self.server_version = None
                self.vocabulary = {"status": "not_checked"}
            self.endpoint = resolved_endpoint
            if user is not None:
                self.user = user.strip()
            if api_key is not None:
                self.api_key = api_key or None
            if offline is not None:
                self.offline = offline
            if github_user is not None:
                self.github_user = github_user
            if theme is not None:
                self.theme = theme
            self.github = github
            self.repository = github.repository
            if changed:
                for row in self.studies.values():
                    row.update(mode="validate", stale=True)
                    row["_pending"] = False
            self._save()
        if changed:
            self.connect()
        return self.snapshot()

    def _connect(self):
        self.connect()
        if not self.offline and not self.stop.is_set():
            self.refresh_assignments()
        # Keep the displayed server and database state current while the service runs.
        while not self.stop.wait(HEARTBEAT_SECONDS):
            with self.lock:
                idle = not self.connecting
            if idle:
                self.connect()

    def connect(self):
        with self.lock:
            self._connection_generation += 1
            generation = self._connection_generation
            endpoint, api_key, user = self.endpoint, self.api_key, self.user
            if self.offline or not endpoint:
                self.vocabulary = {"status": "offline"}
                self.connecting = False
                return
            self.connecting = True
        account, can_upload, problem, mismatch = None, False, None, None
        try:
            with Client(
                endpoint, api_key=api_key, user=user, cache=self.cache
            ) as client:
                self._vocabulary(client, generation=generation)
                with self.lock:
                    if generation != self._connection_generation:
                        return
                if api_key:
                    identity = client.identity()
                    account, can_upload = identity.username, identity.can_upload
        except ClientError as failure:
            problem = _connection_problem(failure, endpoint)
            if failure.code == UserMismatch.code:
                mismatch = str(failure)
        except ValueError, KeyError, OSError:
            problem = ("error", CONNECTION_FAILED)
        finally:
            with self.lock:
                if generation == self._connection_generation:
                    self.connecting = False
        with self.lock:
            if generation != self._connection_generation:
                return
            self.account, self.can_upload = account, can_upload
            self.connection_problem, self.connection_error = problem or (None, None)
            self.user_mismatch = mismatch
            self.checked_at = now()
            for row in self.studies.values():
                row["mode"] = self.modes.get(self._context(), {}).get(
                    row["id"], "validate"
                )

    def _vocabulary(self, client, *, generation=None):
        capabilities = client.capabilities()
        with self.lock:
            if generation is None or generation == self._connection_generation:
                self.server_version = capabilities.server_version
        if capabilities.processing_version != PROCESSING_VERSION:
            raise CompatibilityError(
                "Upgrade pkdb to match the server processing version",
                code="processing_version_mismatch",
            )
        try:
            vocabulary = self.cache.load(client.endpoint)
        except OSError, ValueError:
            vocabulary = None
        if (
            vocabulary is None
            or vocabulary_hash(vocabulary) != capabilities.vocabulary_hash
        ):
            vocabulary = client.vocabulary()
        digest = vocabulary_hash(vocabulary)
        if digest != capabilities.vocabulary_hash:
            raise CompatibilityError(
                "Server vocabulary changed while synchronizing; validate again"
            )
        with self.lock:
            if generation is not None and generation != self._connection_generation:
                return vocabulary
            if self.vocabulary.get("hash") != digest:
                for row in self.studies.values():
                    row["stale"] = True
            self.vocabulary = {
                "status": "current",
                "hash": digest,
                "processing_version": PROCESSING_VERSION,
            }
        return vocabulary
