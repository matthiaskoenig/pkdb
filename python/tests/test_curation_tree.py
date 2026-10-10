"""The listings that the scans of the curation app reuse while a folder shows no change."""

import os
import shutil
import time

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
    real = os.scandir

    def scandir(path):
        folders.append(path)
        return real(path)

    monkeypatch.setattr(tree_module.os, "scandir", scandir)
    return folders


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
