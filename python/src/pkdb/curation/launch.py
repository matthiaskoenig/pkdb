"""Start the local workspace and open files using operating-system associations."""

import os
import shlex
import subprocess
import sys
import webbrowser
from pathlib import Path


def windows_quoted(path: str) -> str:
    """A Windows path in double quotes, as programs and `cmd /c` read an argument.

    The quotes keep spaces and characters such as & in the argument. Backslashes before
    the closing quote are doubled, so that a folder such as C:\\ keeps its backslash; a
    Windows path holds no double quote.
    """
    trailing = len(path) - len(path.rstrip("\\"))
    return f'"{path}{"\\" * trailing}"'


def open_path(path: Path, *, reveal=False):
    path = Path(path).resolve(strict=True)
    if reveal and path.is_file():
        path = path.parent
    if command := os.environ.get("PKDB_OPEN_COMMAND"):
        if os.name == "nt":
            # Windows gets the command line as written, so a program path in double
            # quotes may hold spaces, and backslashes stay.
            arguments = f"{command} {windows_quoted(str(path))}"
        else:
            arguments = [*shlex.split(command), str(path)]
        subprocess.run(arguments, check=True, timeout=15, capture_output=True)
    elif sys.platform == "win32":
        os.startfile(str(path))
    else:
        executable = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.run(
            [executable, str(path)], check=True, timeout=15, capture_output=True
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
        print(
            "The curation app is not built. "
            "Run npm ci and npm run build:curation in frontend/.",
            file=sys.stderr,
        )
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
