"""Start the local workspace and open files using operating-system associations."""

import os
import shlex
import subprocess
import sys
import webbrowser
from pathlib import Path

from pkdb.curation.errors import ActionFailed


def windows_quoted(path: str) -> str:
    """A Windows path in double quotes, as programs and `cmd /c` read an argument.

    The quotes keep spaces and characters such as & in the argument. Backslashes before
    the closing quote are doubled, so that a folder such as C:\\ keeps its backslash; a
    Windows path holds no double quote.
    """
    trailing = len(path) - len(path.rstrip("\\"))
    return f'"{path}{"\\" * trailing}"'


#: How long the command that opens a file may run; it should start a program and return.
OPEN_TIMEOUT = 15


def open_path(path: Path, *, reveal=False, subject: str | None = None):
    """Open `path`, or its folder with `reveal`, with the program of the system.

    PKDB_OPEN_COMMAND replaces the program of the system. ActionFailed says what could not
    be opened or shown in its folder, `subject`, by default the name of the file, and what
    to do when the command is missing or does not return; its cause holds the command, its
    exit status and its stderr.
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
            subprocess.run(
                arguments, check=True, timeout=OPEN_TIMEOUT, capture_output=True
            )
        elif sys.platform == "win32":
            os.startfile(str(path))
        else:
            subprocess.run(
                [executable, str(path)],
                check=True,
                timeout=OPEN_TIMEOUT,
                capture_output=True,
            )
    except subprocess.CalledProcessError as error:
        raise ActionFailed(f"{failed}.", code="open_failed", cause=error) from error
    except subprocess.TimeoutExpired as error:
        raise ActionFailed(
            f"{failed}: the command did not return within "
            f"{OPEN_TIMEOUT} seconds. Use a command that starts the program and returns.",
            code="open_timeout",
            cause=error,
        ) from error
    except FileNotFoundError as error:
        if not command and sys.platform == "win32":
            raise ActionFailed(f"{failed}.", code="open_failed", cause=error) from error
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
        raise ActionFailed(f"{failed}.", code="open_failed", cause=error) from error


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
