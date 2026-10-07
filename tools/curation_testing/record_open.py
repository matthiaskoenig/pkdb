"""Stand in for the opener of the operating system: append the opened path to PKDB_OPEN_LOG.

`pkdb curate` runs the command in PKDB_OPEN_COMMAND with the path as its last argument, so the
end-to-end tests set it to this script and read the log instead of opening a program.
"""

import os
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: record_open.py <path>")
    with Path(os.environ["PKDB_OPEN_LOG"]).open("a", encoding="utf-8") as log:
        log.write(sys.argv[1] + "\n")


if __name__ == "__main__":
    main()
