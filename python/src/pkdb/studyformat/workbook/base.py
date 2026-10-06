"""Location of the workbook, its sync state file and the lock files of open workbooks."""

from pathlib import Path

# Excel limits sheet names to 31 characters.
SHEET_NAME_LIMIT = 31


def workbook_path(folder: Path) -> Path:
    """The workbook of a study folder, named after the study: Smith2020/Smith2020.xlsx."""
    return folder / f"{folder.name}.xlsx"


def state_path(workbook: Path) -> Path:
    """The hidden sync state file next to the workbook: .Smith2020.xlsx.pkdb-base."""
    return workbook.with_name(f".{workbook.name}.pkdb-base")


def open_lock(workbook: Path) -> Path | None:
    """The lock file that shows the workbook is open in a spreadsheet program, or None.

    LibreOffice creates `.~lock.<file>#` and Excel creates `~$<file>`; Office
    replaces the first two characters of the file name of long names, so the
    name without them is checked as well. Only regular files count; a folder or a
    symbolic link with such a name is no lock.
    """
    name = workbook.name
    for lock in (f".~lock.{name}#", f"~${name}", f"~${name[2:]}"):
        path = workbook.with_name(lock)
        if path.is_file() and not path.is_symlink():
            return path
    return None
