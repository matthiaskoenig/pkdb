"""Start the local workspace and open files using operating-system associations."""

import os
import subprocess
import sys
import webbrowser
from pathlib import Path


def open_path(path: Path, *, reveal=False):
    path = Path(path).resolve(strict=True)
    if reveal and path.is_file():
        path = path.parent
    if sys.platform == "win32":
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
    github_user=None,
    repository=None,
    offline=False,
    port=0,
    no_browser=False,
    state_dir=None,
):
    from pkdb.curation.engine import CurationEngine
    from pkdb.curation.server import create_server

    if not 0 <= port <= 65535:
        raise ValueError("Port must be between 0 and 65535")
    engine = CurationEngine(
        path=path,
        endpoint=endpoint,
        github_user=github_user,
        repository=repository,
        offline=offline,
        state_dir=state_dir,
        api_key=os.environ.get("PKDB_API_KEY"),
    )
    try:
        server = create_server(engine, port)
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
