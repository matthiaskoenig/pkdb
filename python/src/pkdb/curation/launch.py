"""Start the local workspace and open files using operating-system associations."""

import io
import os
import shlex
import subprocess
import sys
import tempfile
import threading
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import IO

from pkdb.curation.errors import STDERR_TAIL, ActionFailed


def windows_quoted(path: str) -> str:
    """A Windows path in double quotes, as programs and `cmd /c` read an argument.

    The quotes keep spaces and characters such as & in the argument. Backslashes before
    the closing quote are doubled, so that a folder such as C:\\ keeps its backslash; a
    Windows path holds no double quote.
    """
    trailing = len(path) - len(path.rstrip("\\"))
    return f'"{path}{"\\" * trailing}"'


#: How long the command that opens a file has to fail. A command that still runs then
#: counts as started: xdg-open, for example, may run as long as the program it started.
EARLY_FAILURE_SECONDS: float = 2

#: Hears that an open command failed after it counted as started, with the ActionFailed
#: that open_path raises for a command that fails in time.
LateFailure = Callable[[ActionFailed], None]


def _stderr_of(errors: IO[bytes]) -> bytes:
    """The end of what a command wrote to `errors`: as much as an error body keeps.

    A command may write megabytes; only the last STDERR_TAIL bytes are read.
    """
    size = errors.seek(0, io.SEEK_END)
    errors.seek(max(0, size - STDERR_TAIL))
    return errors.read()


def _open_failed(failed: str, error: BaseException) -> ActionFailed:
    """The ActionFailed of an open command that failed, early or late."""
    failure = ActionFailed(f"{failed}.", code="open_failed", cause=error)
    failure.__cause__ = error
    return failure


def _reap(
    process: subprocess.Popen[bytes],
    arguments: list[str] | str,
    errors: IO[bytes],
    failed: str,
    late_failure: LateFailure | None,
) -> None:
    """Wait for an open command that counted as started, so that no zombie remains.

    A later exit with a non-zero status goes to `late_failure`; without it, the failure is
    dropped, as for `pkdb tables open`, which has exited by then.
    """
    with errors:
        status = process.wait()
        if status == 0 or late_failure is None:
            return
        error = subprocess.CalledProcessError(
            status, arguments, stderr=_stderr_of(errors)
        )
    late_failure(_open_failed(failed, error))


def _start(
    arguments: list[str] | str, failed: str, late_failure: LateFailure | None
) -> None:
    """Start the open command detached, and wait EARLY_FAILURE_SECONDS for it to fail.

    The command gets no pipe: a program that it starts, such as LibreOffice started by
    xdg-open, inherits its streams and keeps them open until it quits, so reading a pipe
    to its end would wait for the program (#933). stdin and stdout are the null device,
    stderr is a temporary file. The command runs in a session of its own, so that the
    program outlives a Ctrl+C in the terminal of pkdb; Windows ignores start_new_session.

    CalledProcessError, with the end of stderr, says that the command failed in time. A
    command that still runs counts as started: a daemon thread waits for it (`_reap`).
    """
    errors = tempfile.TemporaryFile()
    try:
        process = subprocess.Popen(
            arguments,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=errors,
            close_fds=True,
            start_new_session=True,
        )
    except BaseException:
        errors.close()
        raise
    try:
        try:
            status = process.wait(timeout=EARLY_FAILURE_SECONDS)
        except subprocess.TimeoutExpired:
            try:
                threading.Thread(
                    target=_reap,
                    args=(process, arguments, errors, failed, late_failure),
                    name=f"pkdb-open-command-{process.pid}",
                    daemon=True,
                ).start()
            except BaseException:
                # Nothing will wait for the command: stop it, so that no zombie remains.
                process.kill()
                process.wait()
                raise
            return
        if status != 0:
            raise subprocess.CalledProcessError(
                status, arguments, stderr=_stderr_of(errors)
            )
    except BaseException:
        # The thread did not take over the file, or the command failed in time.
        errors.close()
        raise
    errors.close()


def open_path(
    path: Path,
    *,
    reveal: bool = False,
    subject: str | None = None,
    late_failure: LateFailure | None = None,
) -> None:
    """Open `path`, or its folder with `reveal`, with the program of the system.

    PKDB_OPEN_COMMAND replaces the program of the system. The command starts detached.
    ActionFailed says what could not be opened or shown in its folder, `subject`, by
    default the name of the file, when the command is missing or fails within
    EARLY_FAILURE_SECONDS; its cause holds the command, its exit status and its stderr. A
    command that still runs then counts as started; when it fails later, `late_failure`
    gets that ActionFailed. Windows without PKDB_OPEN_COMMAND opens the file with its
    file association, which returns at once.
    """
    path = Path(path).resolve(strict=True)
    # A folder has no folder to be shown in: it opens.
    shown = reveal and path.is_file()
    failed = (
        f"Could not show {subject or path.name} in its folder"
        if shown
        else f"Could not open {subject or path.name}"
    )
    if shown:
        path = path.parent
    command = os.environ.get("PKDB_OPEN_COMMAND")
    executable = "open" if sys.platform == "darwin" else "xdg-open"
    try:
        if command:
            if os.name == "nt":
                # Windows gets the command line as written, so a program path in double
                # quotes may hold spaces, and backslashes stay.
                arguments = f"{command} {windows_quoted(str(path))}"
            else:
                arguments = [*shlex.split(command), str(path)]
        elif sys.platform == "win32":
            os.startfile(str(path))
            return
        else:
            arguments = [executable, str(path)]
        _start(arguments, failed, late_failure)
    except subprocess.CalledProcessError as error:
        raise _open_failed(failed, error)
    except FileNotFoundError as error:
        if not command and sys.platform == "win32":
            raise _open_failed(failed, error)
        missing = (
            f"the command {command!r} of PKDB_OPEN_COMMAND" if command else executable
        )
        raise ActionFailed(
            f"{failed}: {missing} was not found. Set PKDB_OPEN_COMMAND "
            "to a command that opens files, such as 'gio open'.",
            code="open_command_missing",
            cause=error,
        ) from error
    except OSError as error:
        raise _open_failed(failed, error)


def unbuilt_app_message(assets: Path) -> str:
    """Why `pkdb curate` cannot start without the built app, and which pkdb runs.

    The folder of the app names the pkdb that runs, so that a user with a release and a
    source checkout of pkdb sees that the checkout runs, for example from an active
    virtual environment. The app lies in `python/src/pkdb/curation/static` of a checkout.
    """
    message = f"The curation app is not built: {assets} has no index.html."
    parents = assets.parents
    checkout = parents[4] if len(parents) > 4 else None
    if checkout is not None and (checkout / "frontend" / "package.json").is_file():
        return (
            f"{message}\nThis pkdb runs from the source checkout {checkout}. Run npm ci "
            f"and npm run build:curation in {checkout / 'frontend'}, or run an installed "
            "pkdb release, which contains the app."
        )
    return (
        f"{message}\nThis pkdb was installed from a source checkout without the app. "
        "Run npm ci and npm run build:curation in frontend/ of the checkout and install "
        "it again, or install a pkdb release, which contains the app."
    )


def run(
    path=None,
    *,
    endpoint=None,
    user=None,
    github_user=None,
    repository=None,
    offline=False,
    port=0,
    no_browser=False,
    state_dir=None,
):
    from pkdb.curation import server as transport
    from pkdb.curation.engine import CurationEngine

    if not 0 <= port <= 65535:
        raise ValueError("Port must be between 0 and 65535")
    if not (transport.ASSETS / "index.html").is_file():
        # A source checkout without `npm run build:curation`; release wheels ship the app.
        print(unbuilt_app_message(transport.ASSETS), file=sys.stderr)
        return 1
    engine = CurationEngine(
        path=path,
        endpoint=endpoint,
        user=user,
        github_user=github_user,
        repository=repository,
        offline=offline,
        state_dir=state_dir,
        api_key=os.environ.get("PKDB_API_KEY"),
    )
    try:
        server = transport.create_server(engine, port)
    except Exception:
        engine.close()
        raise
    print(f"PK-DB curation: {server.launch_url}\nPress Ctrl+C to stop.", flush=True)
    if not no_browser:
        try:
            webbrowser.open(server.launch_url)
        except webbrowser.Error:
            print("Open the URL above in your browser.", file=sys.stderr)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
