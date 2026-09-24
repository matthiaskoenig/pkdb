"""Known non-source files created by editors and operating systems."""

from pathlib import Path


def ignored_source(path: Path) -> bool:
    name = path.name
    return (
        ".git" in path.parts
        or name in {".DS_Store", "Thumbs.db", "desktop.ini"}
        or name.startswith("~$")
        or (name.startswith(".~lock.") and name.endswith("#"))
        or (name.startswith(".") and name.endswith((".swp", ".swo")))
    )
