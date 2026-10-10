"""Keep the installed pkdb client in sync with PyPI and the PK-DB server.

The client and server share one release version. A server newer than the
client, or a newer release on PyPI, upgrades the installed client with the
installer that owns it before the command runs. Development checkouts and
system-managed interpreters are never modified.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from importlib import metadata
from importlib.util import find_spec
from pathlib import Path

from pkdb import __version__

PYPI_URL = "https://pypi.org/pypi/pkdb/json"
CHECK_INTERVAL = 6 * 3600
DISABLE_VARIABLE = "PKDB_NO_UPDATE"
_RELEASE = re.compile(r"\d+(?:\.\d+)*")


def release(value) -> tuple[int, ...] | None:
    """Return the numeric release tuple of a final version, otherwise ``None``."""
    if not isinstance(value, str) or not _RELEASE.fullmatch(value):
        return None
    parts = [int(part) for part in value.split(".")]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def newer(candidate, current=__version__) -> bool:
    candidate, current = release(candidate), release(current)
    return candidate is not None and current is not None and candidate > current


@dataclass(frozen=True)
class Installation:
    kind: str
    command: tuple[str, ...] | None

    @property
    def manual(self) -> str:
        if self.command:
            return " ".join(self.command)
        if self.kind == "development":
            return "update the development checkout"
        return "pip install --upgrade pkdb"


def _direct_url() -> dict:
    try:
        text = metadata.distribution("pkdb").read_text("direct_url.json")
        return json.loads(text) if text else {}
    except metadata.PackageNotFoundError, ValueError:
        return {}


def installation(prefix=None) -> Installation:
    """Describe the installer that owns this interpreter's pkdb distribution."""
    prefix = Path(prefix or sys.prefix)
    direct = _direct_url()
    # Source checkouts (editable or not) and VCS installs are managed by hand.
    if "dir_info" in direct or "vcs_info" in direct:
        return Installation("development", None)
    if (prefix / "uv-receipt.toml").is_file() and shutil.which("uv"):
        return Installation("uv tool", ("uv", "tool", "upgrade", "pkdb"))
    if (prefix / "pipx_metadata.json").is_file() and shutil.which("pipx"):
        return Installation("pipx", ("pipx", "upgrade", "pkdb"))
    if sys.prefix != sys.base_prefix:
        if find_spec("pip") is not None:
            return Installation(
                "virtual environment",
                (sys.executable, "-m", "pip", "install", "--upgrade", "pkdb"),
            )
        if shutil.which("uv"):
            return Installation(
                "virtual environment",
                ("uv", "pip", "install", "--python", sys.executable, "-U", "pkdb"),
            )
    return Installation("unmanaged", None)


class UpdateState:
    """Throttled release checks and the newest server version seen by this client."""

    def __init__(self, path=None):
        from pkdb.cache import cache_directory

        self.path = Path(path or cache_directory() / "update.json")

    def load(self) -> dict:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except OSError, ValueError:
            return {}
        return value if isinstance(value, dict) else {}

    def save(self, value: dict):
        from pkdb.cache import atomic_json

        try:
            atomic_json(self.path, value)
        except OSError:
            pass

    def note_server_version(self, version):
        """Remember a server release newer than this client for the next start."""
        if not newer(version):
            return
        value = self.load()
        if newer(version, value.get("server_version") or "0"):
            self.save(
                {**value, "server_version": version, "server_seen_at": time.time()}
            )

    def due(self, now=None) -> bool:
        value = self.load()
        checked = value.get("checked_at")
        if not isinstance(checked, int | float):
            return True
        seen = value.get("server_seen_at")
        # A newer server release triggers one immediate check, not one per command.
        if newer(value.get("server_version")) and isinstance(seen, int | float):
            if seen > checked:
                return True
        now = time.time() if now is None else now
        return now - checked >= CHECK_INTERVAL

    def latest(self, *, transport=None, now=None) -> str | None:
        """Query PyPI for the newest final release, falling back to the last answer."""
        import httpx2

        value = self.load()
        now = time.time() if now is None else now
        owns = transport is None
        client = transport or httpx2.Client(
            timeout=httpx2.Timeout(5, connect=3), follow_redirects=True
        )
        try:
            response = client.get(
                PYPI_URL, headers={"User-Agent": f"pkdb/{__version__}"}
            )
            response.raise_for_status()
            latest = response.json()["info"]["version"]
            if release(latest) is None:
                raise ValueError("Not a final release")
        except httpx2.HTTPError, ValueError, KeyError, TypeError:
            # Offline starts retry after the regular interval, not on every command.
            self.save({**value, "checked_at": now})
            return value.get("latest")
        finally:
            if owns:
                client.close()
        self.save(
            {
                **value,
                "checked_at": now,
                "latest": latest,
            }
        )
        return latest


def installed_version() -> str | None:
    """Read the version a fresh interpreter would import after an upgrade."""
    try:
        result = subprocess.run(
            [sys.executable, "-P", "-c", "import pkdb; print(pkdb.__version__)"],
            check=True,
            capture_output=True,
            encoding="utf-8",
            timeout=60,
        )
    except OSError, subprocess.SubprocessError:
        return None
    return result.stdout.strip() or None


def upgrade(target, *, install=None, log=print) -> bool:
    """Upgrade to at least ``target``; return whether a newer release is installed."""
    install = install or installation()
    if not install.command:
        log(
            f"pkdb {target} is available (installed {__version__}, {install.kind}). "
            f"To update, {install.manual}."
        )
        return False
    log(f"Updating pkdb {__version__} to {target}: {install.manual}")
    try:
        subprocess.run(install.command, check=True, timeout=600, capture_output=True)
    except OSError, subprocess.SubprocessError:
        log(f"Automatic update failed. Run `{install.manual}` manually.")
        return False
    version = installed_version()
    if not newer(version):
        log(f"pkdb is still {__version__} after updating. Run `{install.manual}`.")
        return False
    if newer(target, version):
        log(f"pkdb {version} installed; {target} is not yet available to installers.")
    else:
        log(f"Updated pkdb to {version}.")
    return True


def target_version(state, *, force=False, transport=None) -> str | None:
    """The newest release this client should run, or ``None`` when it is current."""
    if not force and not state.due():
        return None
    latest = state.latest(transport=transport)
    return latest if newer(latest) else None


def automatic_update(argv, *, state=None, transport=None) -> int | None:
    """Upgrade before running a command and rerun it with the new release.

    Returns the exit code of the rerun command, or ``None`` when the current
    process should continue with the installed release.
    """
    if os.environ.get(DISABLE_VARIABLE) or "--no-update" in argv:
        return None
    if not argv or argv[0] == "update" or {"-h", "--help", "--version"} & set(argv):
        return None
    install = installation()
    if install.kind == "development":
        return None
    state = state or UpdateState()
    target = target_version(state, transport=transport)
    if target is None:
        return None

    def log(message):
        print(message, file=sys.stderr, flush=True)

    if not upgrade(target, install=install, log=log):
        return None
    return subprocess.run(
        [sys.executable, "-m", "pkdb", *argv],
        env={**os.environ, DISABLE_VARIABLE: "1"},
    ).returncode
