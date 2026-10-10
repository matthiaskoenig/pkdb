"""The study folders of a workspace and their source files, read for the scan each second.

The curation app scans its workspace each second. Listing every folder and making a path object
for every file on each scan kept a processor core half busy for a workspace of the size of
pkdb_data, so the tree keeps the listing of each folder and reuses it while the status of the
folder shows that its entries are the same.

The cache relies on a rule that file systems keep on Linux, macOS and Windows: the modification
time of a folder changes when an entry is added to it, removed from it or renamed in it. Writing
to a file does not change the modification time of its folder, so each scan still reads the
status of every source file of a study. The tree closes the gaps of the rule:

- Timestamps are coarse (2 s on FAT, 1 s on HFS+, a clock tick on Linux), and network file
  systems cache the status and the listing of a folder for some seconds, so a change right after
  a listing can leave the status as it was. A listing is reused only if the status of its folder
  was the same for `STABLE` seconds before it was read. The seconds are counted on the clock of
  the app, so the clock of a file server does not matter.
- Tools such as `cp -p`, `rsync -t` and `tar x` set the modification time back. The status change
  time, which they cannot set, tells this on Linux and macOS; the inode and the device tell a
  folder that was replaced.
- Some file systems may not keep the rule at all, such as FAT drives and some network and FUSE
  mounts, and on Windows the status change time is the creation time. A reused listing is read
  again after `RECHECK` seconds; if its entries changed while the status of its folder did not,
  the tree reads every folder on each scan from then on, as the scan did before the cache,
  until the workspace changes or the app restarts.

Only scans use a tree, one at a time, so it needs no lock.
"""

import os
import time
from collections.abc import Callable

# The tests change what the tree reads through these names, not in the os module.
from os import scandir, stat
from pathlib import Path
from stat import S_ISLNK, S_ISREG
from typing import NamedTuple

from pkdb.source_files import ignored_name
from pkdb.studyformat.tables import STUDY_JSON
from pkdb.studyformat.validation import _FORMAT_2_FILES as FORMAT_2_FILES
from pkdb.studyformat.workbook.base import open_lock, workbook_path

#: Seconds that the status of a folder must stay the same before a listing of it is reused.
STABLE = 30.0
#: Seconds after which a reused listing is read again to check the file system.
RECHECK = 30.0

# The kinds of entries, as `os.DirEntry` tells them without following symbolic links. A
# junction is a folder too, on Windows only.
_FILE, _FOLDER, _JUNCTION, _LINK, _OTHER = range(5)


class StudyFolder(NamedTuple):
    """A folder with a study.json that is no symbolic link, outside hidden folders."""

    #: The path relative to the workspace with forward slashes, "." for the workspace itself.
    key: str
    #: Whether a junction or a mount point of Windows lies on the way from the workspace, so
    #: that the folder may resolve to a path outside it.
    junction: bool
    #: Whether study.json is a regular file.
    study_file: bool


class _Listing:
    """The entries of a folder as one `os.scandir` read them, and the status of the folder."""

    __slots__ = (
        "entries",
        "files",
        "folder",
        "folders",
        "format_2_file",
        "key",
        "listed",
        "since",
        "study",
        "study_file",
        "trusted",
        "visible",
        "workbook_open",
    )

    def __init__(self, key: tuple, since: float, listed: float):
        self.key = key
        # When the scans first saw the status, and when the entries were read.
        self.since = since
        self.listed = listed
        # Whether the status was the same for STABLE seconds before the entries were read.
        self.trusted = False
        # The name and the kind of each entry by name, None for a folder that cannot be read.
        self.entries: list[tuple[str, int]] | None = None
        # (name, path) of the entries that are no folders and that sources do not ignore, made
        # when a scan first asks for the files of the folder.
        self.files: list[tuple[str, str]] | None = None
        # (name, path, junction) of the folders except .git, and of those that are not hidden.
        self.folders: list[tuple[str, str, bool]] = []
        self.visible: list[tuple[str, str, bool]] = []
        # Whether a study.json that is no symbolic link exists, and whether it is a file.
        self.study = False
        self.study_file = False
        # Decided when a scan first asks for them in this listing.
        self.format_2_file: bool | None = None
        self.workbook_open: bool | None = None
        # The path object of a study folder, kept to compare and hash it cheaply.
        self.folder: Path | None = None


def _status(path: str) -> tuple | None:
    """What changes when an entry of the folder is added, removed or renamed, or None."""
    try:
        status = stat(path)
    except OSError, ValueError:
        return None
    return (status.st_mtime_ns, status.st_ctime_ns, status.st_ino, status.st_dev)


def _find_study(listing: _Listing, path: str) -> None:
    """Whether the folder has a study.json that is no symbolic link, as `os.path.lexists` tells."""
    try:
        status = os.lstat(os.path.join(path, STUDY_JSON))
    except OSError, ValueError:
        return
    listing.study = not S_ISLNK(status.st_mode)
    listing.study_file = S_ISREG(status.st_mode)


def _kind(entry: os.DirEntry) -> int:
    """The kind of an entry; as for `Path.rglob`, one that cannot be told is no folder."""
    try:
        if entry.is_file(follow_symlinks=False):
            return _FILE
        if entry.is_dir(follow_symlinks=False):
            return _JUNCTION if entry.is_junction() else _FOLDER
        if entry.is_symlink():
            return _LINK
    except OSError:
        pass
    return _OTHER


class SourceTree:
    """The study folders below a workspace and their source files, with the listings reused."""

    def __init__(self, root: Path, clock: Callable[[], float] = time.monotonic):
        self.root = root
        self.clock = clock
        # False once a listing changed while the status of its folder did not.
        self.reliable = True
        # The listings of the last scan, and those that this scan used so far.
        self._listings: dict[str, _Listing] = {}
        self._seen: dict[str, _Listing] = {}
        # The folders that the last scan sorted, which it keeps alive, and their order.
        self._identities: set[int] = set()
        self._order: list[Path] = []

    def study_folders(self) -> dict[Path, StudyFolder]:
        """Start a scan and find the folders with a study.json, as `Path.rglob` finds them.

        A study.json that is a symbolic link or that lies below a hidden folder does not count,
        and the walk does not follow symbolic links of folders. A listing that this scan does not
        use is forgotten.
        """
        self._listings, self._seen = self._seen, {}
        found: dict[Path, StudyFolder] = {}
        stack = [(str(self.root), ".", False)]
        while stack:
            path, key, junction = stack.pop()
            listing = self._listing(path)
            if listing is None:
                continue
            if listing.study:
                if listing.folder is None:
                    listing.folder = Path(path)
                found.setdefault(
                    listing.folder, StudyFolder(key, junction, listing.study_file)
                )
            if listing.visible:
                stack.extend(
                    (child, name if key == "." else f"{key}/{name}", junction or link)
                    for name, child, link in reversed(listing.visible)
                )
        return found

    def files(self, folder: Path) -> list[tuple[str, int, int]]:
        """The relative path, size and modification time of each source file of a folder.

        These are the files that `folder.rglob("*")` finds and that sources do not ignore, with
        the status that `Path.stat` reads; only regular files count, also through a symbolic
        link. The status of each file is read on each call, as a file can change in place.
        """
        files = []
        stack = [(str(folder), "")]
        while stack:
            path, prefix = stack.pop()
            listing = self._listing(path)
            if listing is None:
                continue
            if listing.files is None:
                listing.files = [
                    (name, os.path.join(path, name))
                    for name, kind in listing.entries or ()
                    if kind != _FOLDER and kind != _JUNCTION and not ignored_name(name)
                ]
            for name, file in listing.files:
                try:
                    status = stat(file)
                except OSError, ValueError:
                    continue
                if S_ISREG(status.st_mode):
                    files.append((prefix + name, status.st_size, status.st_mtime_ns))
            if listing.folders:
                stack.extend(
                    (child, f"{prefix}{name}/")
                    for name, child, _ in reversed(listing.folders)
                )
        return files

    def has_format_2_file(self, folder: Path) -> bool:
        """Whether a file that only format 2 has exists in the folder, maybe as a symbolic link."""
        listing = self._listing(str(folder))
        if listing is None:
            return any(os.path.lexists(folder / name) for name in FORMAT_2_FILES)
        if listing.format_2_file is None:
            listing.format_2_file = any(
                os.path.lexists(folder / name) for name in FORMAT_2_FILES
            )
        return listing.format_2_file

    def workbook_open(self, folder: Path) -> bool:
        """Whether the lock file of a spreadsheet program shows the workbook of the folder open."""
        listing = self._listing(str(folder))
        if listing is None:
            return open_lock(workbook_path(folder)) is not None
        if listing.workbook_open is None:
            listing.workbook_open = open_lock(workbook_path(folder)) is not None
        return listing.workbook_open

    def ordered(self, folders: set[Path]) -> list[Path]:
        """`sorted(folders)`, remembered while the scans pass the same path objects."""
        identities = {id(folder) for folder in folders}
        if identities != self._identities:
            self._identities, self._order = identities, sorted(folders)
        return self._order

    def _listing(self, path: str) -> _Listing | None:
        """The listing of a folder, read again unless its status shows the same entries.

        None for a folder whose status cannot be read.
        """
        listing = self._seen.get(path)
        if listing is not None:
            return listing
        key = _status(path)
        if key is None:
            return None
        # The time of this status, not of the start of the scan, which can be long ago.
        now = self.clock()
        old = self._listings.get(path)
        if old is not None and old.key == key:
            if self.reliable and old.trusted and now - old.listed < RECHECK:
                self._seen[path] = old
                return old
            since = old.since
        else:
            since = now
        listing = self._read(path, key, since, now, old)
        if (
            old is not None
            and old.trusted
            and old.key == key
            and listing.entries is not None
            and listing.entries != old.entries
            and _status(path) == key
        ):
            # The entries changed while the status did not: this file system does not keep
            # the rule that the cache relies on.
            self.reliable = False
        self._seen[path] = listing
        return listing

    def _read(
        self, path: str, key: tuple, since: float, now: float, old: _Listing | None
    ) -> _Listing:
        listing = _Listing(key, since, now)
        if old is not None:
            listing.folder = old.folder
        try:
            with scandir(path) as iterator:
                listing.entries = sorted(
                    (entry.name, _kind(entry)) for entry in iterator
                )
        except OSError:
            # As for Path.rglob, a folder that cannot be listed has no entries, but its
            # study.json counts when the folder can be entered. The next scan reads it again.
            _find_study(listing, path)
            return listing
        listing.trusted = now - since >= STABLE
        for name, kind in listing.entries:
            if (kind == _FOLDER or kind == _JUNCTION) and name != ".git":
                folder = (name, os.path.join(path, name), kind == _JUNCTION)
                listing.folders.append(folder)
                if not name.startswith("."):
                    listing.visible.append(folder)
        if old is not None and old.key == key and old.entries == listing.entries:
            # The same entries: what the listing told of them holds still. The format 2
            # files and the lock files are looked up again, as they were looked up after
            # the old listing was read and may have changed in between.
            listing.study, listing.study_file = old.study, old.study_file
            listing.files = old.files
        else:
            _find_study(listing, path)
        return listing
