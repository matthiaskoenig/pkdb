from pathlib import Path

import pytest

from pkdb.source_files import ignored_name, ignored_source


@pytest.mark.parametrize(
    "name",
    [
        ".DS_Store",
        "Thumbs.db",
        "desktop.ini",
        "~$Example.xlsx",
        ".~lock.Example.xlsx#",
        ".table.tsv.swp",
        ".tmp0123456789abcdef",
        ".Example.xlsx.pkdb-base",
        ".git",
    ],
)
def test_ignored_source_files(name):
    assert ignored_source(Path(name))
    assert ignored_source(Path("sub") / name)
    assert ignored_name(name)


@pytest.mark.parametrize(
    "name",
    [
        ".tmp",
        "tmp0123456789abcdef",
        ".tmp0123456789abcde",
        ".tmp0123456789abcdef0",
        ".tmp0123456789ABCDEF",
        ".tmp0123456789abcdeg",
        "Example.xlsx.pkdb-base",
        ".Example.xlsx.pkdb-base.bak",
        "Example.xlsx",
        "subjects.tsv",
    ],
)
def test_other_files_are_not_ignored(name):
    assert not ignored_source(Path(name))
    assert not ignored_name(name)
