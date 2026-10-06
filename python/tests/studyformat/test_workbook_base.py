import os

import pytest

from pkdb.studyformat.workbook.base import (
    SHEET_NAME_LIMIT,
    open_lock,
    state_path,
    workbook_path,
)


def test_sheet_name_limit():
    assert SHEET_NAME_LIMIT == 31


def test_workbook_and_state_paths(tmp_path):
    folder = tmp_path / "caffeine" / "Example"
    assert workbook_path(folder) == folder / "Example.xlsx"
    assert state_path(folder / "Example.xlsx") == folder / ".Example.xlsx.pkdb-base"


@pytest.mark.parametrize(
    "lock", [".~lock.Example.xlsx#", "~$Example.xlsx", "~$ample.xlsx"]
)
def test_open_lock_finds_the_lock_files_of_the_office_programs(tmp_path, lock):
    workbook = tmp_path / "Example.xlsx"
    workbook.write_bytes(b"wb")
    (tmp_path / lock).write_bytes(b"lock")
    assert open_lock(workbook) == tmp_path / lock


def test_open_lock_is_none_without_a_lock(tmp_path):
    workbook = tmp_path / "Example.xlsx"
    workbook.write_bytes(b"wb")
    (tmp_path / "~$Other.xlsx").write_bytes(b"lock")
    (tmp_path / ".~lock.Other.xlsx#").write_bytes(b"lock")
    assert open_lock(workbook) is None


def test_open_lock_is_none_even_without_a_workbook(tmp_path):
    assert open_lock(tmp_path / "Example.xlsx") is None


@pytest.mark.parametrize(
    "lock", [".~lock.Example.xlsx#", "~$Example.xlsx", "~$ample.xlsx"]
)
def test_open_lock_ignores_directories(tmp_path, lock):
    (tmp_path / lock).mkdir()
    assert open_lock(tmp_path / "Example.xlsx") is None


@pytest.mark.skipif(os.name != "posix", reason="symbolic links")
@pytest.mark.parametrize(
    "lock", [".~lock.Example.xlsx#", "~$Example.xlsx", "~$ample.xlsx"]
)
def test_open_lock_ignores_symbolic_links(tmp_path, lock):
    target = tmp_path / "elsewhere"
    target.write_bytes(b"lock")
    (tmp_path / lock).symlink_to(target)
    assert open_lock(tmp_path / "Example.xlsx") is None
