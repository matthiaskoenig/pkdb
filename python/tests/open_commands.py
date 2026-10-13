"""Open commands for the tests: real programs that stand in for xdg-open.

`pkdb curate` runs PKDB_OPEN_COMMAND with the path as its last argument. These commands are
Python programs, so they run on every platform, and none opens a file.
"""

import os
import shlex
import signal
import subprocess
import sys
from pathlib import Path


def command_line(arguments: list[str]) -> str:
    """`arguments` as PKDB_OPEN_COMMAND: quoted as the shell of the platform quotes them."""
    join = subprocess.list2cmdline if os.name == "nt" else shlex.join
    return join(arguments)


def python_program(code: str) -> list[str]:
    """The arguments that run the Python `code`; the path to open comes after them."""
    return [sys.executable, "-c", code]


#: An opener that fails at once, as xdg-open without a program for the file.
FAILING_OPENER = python_program(
    "import sys; sys.stderr.write('no method available for opening'); sys.exit(4)"
)


def holding_opener(pid_file: Path) -> list[str]:
    """An opener that starts a program and exits at once, as xdg-open starts LibreOffice.

    The program keeps the stdout and the stderr of the opener open for 30 seconds. Its
    process id is in `pid_file` once the opener has exited, for `stop_program`.
    """
    program = "import time; time.sleep(30)"
    return python_program(
        "import pathlib, subprocess, sys; "
        f"child = subprocess.Popen([sys.executable, '-c', {program!r}], "
        "stdout=sys.stdout, stderr=sys.stderr); "
        f"pathlib.Path({str(pid_file)!r}).write_text(str(child.pid))"
    )


def stop_program(pid_file: Path) -> None:
    """Stop the program of a holding opener; nothing when it did not start or has ended."""
    if not pid_file.exists():
        return
    try:
        os.kill(int(pid_file.read_text()), signal.SIGTERM)
    except OSError:
        # The program has ended already.
        pass
