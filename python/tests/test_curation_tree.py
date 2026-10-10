"""The listings that the scans of the curation app reuse while a folder shows no change."""

import os
import shutil
import sys
import time
from pathlib import Path

import pytest

from pkdb.curation import engine as module
from pkdb.curation import tree as tree_module
from pkdb.curation.tree import RECHECK, STABLE, SourceTree


class Clock:
    """The clock of the tree, which the tests move on."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@pytest.fixture
def workspace(tmp_path, tmp_path_factory, make_study, valid_files):
    folder = make_study(valid_files)  # tmp_path/caffeine/Example
    engine = module.CurationEngine(
        tmp_path, state_dir=tmp_path_factory.mktemp("state"), offline=True, start=False
    )
    clock = Clock()
    engine._tree = SourceTree(engine.root, clock)
    yield engine, folder, clock
    engine.close()


def settle(engine, clock):
    """Let the next scans reuse the listings, as a while after the last change.

    The folders get a modification time long ago, so that a change after the listings shows
    on any file system, whatever the resolution of its timestamps.
    """
    past = time.time_ns() - 3600 * 10**9
    for folder in [engine.root, *engine.root.rglob("*")]:
        if folder.is_dir() and not folder.is_symlink():
            os.utime(folder, ns=(past, past))
    engine.scan()
    clock.now += STABLE
    engine.scan()


@pytest.fixture
def listed(monkeypatch):
    """The folders that the scans list."""
    folders = []
    real = tree_module.scandir

    def scandir(path):
        folders.append(path)
        return real(path)

    monkeypatch.setattr(tree_module, "scandir", scandir)
    return folders


def write(path, text="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def files(engine, key="caffeine/Example"):
    return [entry["path"] for entry in engine.studies[key]["files"]]


def test_a_scan_after_the_folders_settled_lists_none(workspace, listed):
    engine, folder, clock = workspace
    settle(engine, clock)
    listed.clear()
    engine.scan()
    assert listed == []
    # A reused listing is read again after a while, to check the file system.
    clock.now += RECHECK
    engine.scan()
    assert str(folder) in listed
    assert engine._tree.reliable


def test_a_file_added_removed_or_renamed_between_two_scans(workspace):
    engine, folder, clock = workspace
    settle(engine, clock)
    (folder / "notes.txt").write_text("notes", encoding="utf-8", newline="")
    engine.scan()
    assert "notes.txt" in files(engine)
    (folder / "Example_Fig2.png").unlink()
    engine.scan()
    assert "Example_Fig2.png" not in files(engine)
    (folder / "notes.txt").rename(folder / "remarks.txt")
    engine.scan()
    assert "remarks.txt" in files(engine) and "notes.txt" not in files(engine)
    # A file in a new subfolder, hidden or not, is a source file too.
    (folder / ".drafts").mkdir()
    (folder / ".drafts" / "plan.txt").write_text("plan", encoding="utf-8", newline="")
    engine.scan()
    assert ".drafts/plan.txt" in files(engine)
    (folder / ".drafts" / "plan.txt").unlink()
    engine.scan()
    assert ".drafts/plan.txt" not in files(engine)


def test_a_file_edited_in_place_between_two_scans(workspace):
    engine, folder, clock = workspace
    settle(engine, clock)
    row = engine.studies["caffeine/Example"]
    row["_pending"], row["stale"] = False, False
    fingerprint = row["_fingerprint"]
    # Writing to a file leaves the modification time of its folder as it was.
    status = folder.stat()
    with (folder / "subjects.tsv").open("a", encoding="utf-8", newline="") as stream:
        stream.write("S3\tall\t1\tTabA\n")
    assert folder.stat().st_mtime_ns == status.st_mtime_ns
    engine.scan()
    assert row["_fingerprint"] != fingerprint
    assert row["status"] == "changed" and row["_pending"] and row["stale"]


def test_a_folder_renamed_between_two_scans(workspace):
    engine, folder, clock = workspace
    settle(engine, clock)
    folder.rename(folder.with_name("Renamed"))
    engine.scan()
    assert list(engine.studies) == ["caffeine/Renamed"]
    (engine.root / "caffeine").rename(engine.root / "theophylline")
    engine.scan()
    assert list(engine.studies) == ["theophylline/Renamed"]


def test_a_hidden_folder_created_between_two_scans(workspace):
    engine, folder, clock = workspace
    settle(engine, clock)
    # The build folder of an interrupted pkdb new holds no study; a visible copy does.
    shutil.copytree(folder, folder.parent / ".Copy.new" / "Copy")
    engine.scan()
    assert list(engine.studies) == ["caffeine/Example"]
    shutil.copytree(folder, folder.parent / "Copy")
    engine.scan()
    assert sorted(engine.studies) == ["caffeine/Copy", "caffeine/Example"]


def test_opening_the_workbook_between_two_scans(workspace):
    engine, folder, clock = workspace
    settle(engine, clock)
    lock = folder / ".~lock.Example.xlsx#"
    lock.write_text("curator", encoding="utf-8", newline="")
    engine.scan()
    assert engine.studies["caffeine/Example"]["_signature"][1] is True
    lock.unlink()
    engine.scan()
    assert engine.studies["caffeine/Example"]["_signature"][1] is False


def _frozen_status(monkeypatch):
    """A file system that leaves the status of a folder as it was when its entries change."""
    real = tree_module._status
    frozen = {}
    monkeypatch.setattr(
        tree_module, "_status", lambda path: frozen.setdefault(path, real(path))
    )


def test_a_listing_is_reused_only_after_its_folder_stayed_unchanged(
    workspace, monkeypatch
):
    engine, folder, clock = workspace
    # As with coarse timestamps: a change right after a listing keeps the status.
    _frozen_status(monkeypatch)
    engine.scan()
    (folder / "notes.txt").write_text("notes", encoding="utf-8", newline="")
    clock.now += STABLE - 1
    engine.scan()
    assert "notes.txt" in files(engine)


def test_a_file_system_that_keeps_the_folder_status_is_listed_on_each_scan(
    workspace, monkeypatch
):
    engine, folder, clock = workspace
    settle(engine, clock)
    _frozen_status(monkeypatch)
    engine.scan()
    (folder / "notes.txt").write_text("notes", encoding="utf-8", newline="")
    engine.scan()
    # The scans cannot tell the change until they read the listing again.
    assert "notes.txt" not in files(engine)
    clock.now += RECHECK
    engine.scan()
    assert "notes.txt" in files(engine)
    assert not engine._tree.reliable
    # From then on each scan reads every folder.
    (folder / "remarks.txt").write_text("remarks", encoding="utf-8", newline="")
    engine.scan()
    assert "remarks.txt" in files(engine)


def test_a_workspace_switch_starts_a_new_tree(workspace, tmp_path, tmp_path_factory):
    engine, folder, clock = workspace
    tree = engine._tree
    other = tmp_path_factory.mktemp("other")
    shutil.copytree(folder, other / "caffeine" / "Other")
    engine.select_workspace(other)
    assert engine._tree is not tree and engine._tree.root == other.resolve()
    assert list(engine.studies) == ["caffeine/Other"]


def test_the_stable_time_counts_from_when_a_scan_reached_the_folder(
    workspace, monkeypatch
):
    engine, folder, clock = workspace
    real = tree_module._status
    frozen = {}

    def status(path):
        if path == str(folder) and path not in frozen:
            # A long scan reaches the study folder shortly before the stable time is over.
            clock.now += STABLE - 1
        return frozen.setdefault(path, real(path))

    # As with coarse timestamps: a change right after a listing keeps the status.
    monkeypatch.setattr(tree_module, "_status", status)
    engine.scan()
    # The stable time after the start of the first scan, a second after the folder.
    clock.now += 1
    engine.scan()
    write(folder / "notes.txt")
    engine.scan()
    assert "notes.txt" in files(engine)


@pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0,
    reason="Windows ignores the folder mode, and root lists any folder",
)
def test_a_study_folder_that_can_be_entered_but_not_listed(workspace):
    engine, folder, clock = workspace
    locked = shutil.copytree(folder, folder.with_name("Locked"))
    locked.chmod(0o311)
    try:
        engine.scan()
        # As for Path.rglob: study.json counts, and the folder has no files to list.
        assert files(engine, "caffeine/Locked") == []
    finally:
        locked.chmod(0o755)


def test_a_lock_file_seen_between_two_listings_counts_only_once(workspace, monkeypatch):
    engine, folder, clock = workspace
    # The listings are read on each scan, with the same entries each time.
    engine.scan()
    with monkeypatch.context() as patch:
        # A lock file that exists only while the scan looks for it.
        patch.setattr(tree_module, "open_lock", lambda workbook: workbook)
        engine.scan()
    assert engine.studies["caffeine/Example"]["_signature"][1] is True
    engine.scan()
    assert engine.studies["caffeine/Example"]["_signature"][1] is False


def test_a_format_2_file_seen_between_two_listings_counts_only_once(
    workspace, monkeypatch
):
    engine, folder, clock = workspace
    legacy = folder.with_name("Legacy1990")
    write(legacy / "study.json", '{"sid": "Legacy1990", "name": "Legacy1990"}')
    engine.scan()
    assert "caffeine/Legacy1990" not in engine.studies
    real = os.path.lexists
    review = str(legacy / "review.json")
    with monkeypatch.context() as patch:
        # A review.json that exists only while the scan looks for it.
        patch.setattr(
            tree_module.os.path,
            "lexists",
            lambda path: str(path) == review or real(path),
        )
        engine.scan()
    assert "caffeine/Legacy1990" in engine.studies
    engine.scan()
    assert "caffeine/Legacy1990" not in engine.studies


@pytest.mark.skipif(
    sys.platform == "win32", reason="Windows reports the creation time as st_ctime"
)
def test_a_folder_whose_modification_time_was_set_back(workspace):
    engine, folder, clock = workspace
    settle(engine, clock)
    before = folder.stat()
    write(folder / "notes.txt")
    # As tar x and rsync -t leave a folder: its old modification time, a new status
    # change time, which changes within its resolution, a clock tick at most.
    os.utime(folder, ns=(before.st_atime_ns, before.st_mtime_ns))
    deadline = time.monotonic() + 5
    while folder.stat().st_ctime_ns == before.st_ctime_ns:
        assert time.monotonic() < deadline, "The status change time stayed"
        time.sleep(0.001)
        os.utime(folder, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert folder.stat().st_mtime_ns == before.st_mtime_ns
    engine.scan()
    assert "notes.txt" in files(engine)


class _Status:
    """The status of a folder with some fields of another one."""

    def __init__(self, status, **fields):
        self._status = status
        self.__dict__.update(fields)

    def __getattr__(self, name):
        return getattr(self._status, name)


@pytest.mark.parametrize("field", ["st_ino", "st_dev"])
def test_a_folder_replaced_by_one_with_the_same_times(workspace, monkeypatch, field):
    engine, folder, clock = workspace
    settle(engine, clock)
    before = os.stat(folder)
    replacement = shutil.copytree(folder, folder.with_name("Replacement"))
    write(replacement / "notes.txt")
    folder.rename(folder.with_name("Old"))
    replacement.rename(folder)
    real = tree_module.stat

    def stat(path):
        status = real(path)
        if path != str(folder):
            return status
        # The times of the old folder: only the inode, or the device, tells it apart.
        fields = {
            name: getattr(before, name)
            for name in ("st_mtime_ns", "st_ctime_ns", "st_ino", "st_dev")
        }
        fields[field] = status.st_ino if field == "st_ino" else before.st_dev + 1
        return _Status(status, **fields)

    monkeypatch.setattr(tree_module, "stat", stat)
    engine.scan()
    assert "notes.txt" in files(engine)


def test_a_study_json_created_in_a_listed_folder(workspace):
    engine, folder, clock = workspace
    draft = shutil.copytree(folder, folder.with_name("Draft"))
    (draft / "study.json").unlink()
    settle(engine, clock)
    assert "caffeine/Draft" not in engine.studies
    shutil.copy(folder / "study.json", draft / "study.json")
    engine.scan()
    assert "caffeine/Draft" in engine.studies


def test_a_symlinked_study_json_is_no_study(workspace):
    engine, folder, clock = workspace
    linked = shutil.copytree(folder, folder.with_name("Linked"))
    (linked / "study.json").unlink()
    try:
        os.symlink(folder / "study.json", linked / "study.json")
    except OSError:
        pytest.skip("Creating symbolic links needs a privilege on this system")
    settle(engine, clock)
    assert "caffeine/Linked" not in engine.studies


def test_a_folder_named_study_json_makes_a_study_folder(workspace):
    engine, folder, clock = workspace
    odd = shutil.copytree(folder, folder.with_name("Odd"))
    (odd / "study.json").unlink()
    (odd / "study.json").mkdir()
    settle(engine, clock)
    # As for Path.rglob("study.json"): the name counts, not the kind of entry.
    assert "caffeine/Odd" in engine.studies


def test_the_listings_of_removed_folders_are_forgotten(workspace):
    engine, folder, clock = workspace
    copy = shutil.copytree(folder, folder.with_name("Copy"))
    write(copy / "figures" / "Fig1.png")
    settle(engine, clock)
    tree = engine._tree
    assert {str(copy), str(copy / "figures")} <= set(tree._seen)
    shutil.rmtree(copy)
    engine.scan()
    engine.scan()
    remembered = {*tree._seen, *tree._listings}
    assert not {str(copy), str(copy / "figures")} & remembered
    assert str(folder) in remembered


def test_git_folders_are_never_listed(workspace, listed):
    engine, folder, clock = workspace
    write(engine.root / ".git" / "objects" / "ab" / "cdef")
    write(folder / ".git" / "config")
    write(folder / "sub" / ".git" / "HEAD")
    settle(engine, clock)
    assert listed
    assert not [path for path in listed if ".git" in Path(path).parts]
    assert not [name for name in files(engine) if ".git" in name]


def test_a_study_behind_a_junction_counts_only_inside_the_workspace(
    workspace, tmp_path_factory
):
    winapi = pytest.importorskip("_winapi", reason="Junctions exist on Windows only")
    engine, folder, clock = workspace
    outside = tmp_path_factory.mktemp("outside")
    shutil.copytree(folder, outside / "Outside")
    winapi.CreateJunction(str(outside), str(engine.root / "elsewhere"))
    winapi.CreateJunction(str(folder.parent), str(engine.root / "again"))
    settle(engine, clock)
    # The scan resolves a folder behind a junction, as before: a study outside the
    # workspace does not count.
    assert sorted(engine.studies) == ["again/Example", "caffeine/Example"]
