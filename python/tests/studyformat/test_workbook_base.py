import base64
import hashlib
import json
import os
import random
import zlib
from datetime import UTC, datetime

import pytest

from pkdb.studyformat.workbook.base import (
    BASE_CHUNK,
    BASE_SHEET,
    LISTS_SHEET,
    SHEET_NAME_LIMIT,
    WORKBOOK_FORMAT,
    BaseError,
    WorkbookBase,
    base_rows,
    open_lock,
    parse_base,
    read_state,
    remove_state,
    state_path,
    workbook_path,
    write_state,
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


# The `_base` encoding and the sync state file.

GENERATION = "0123456789abcdef0123456789abcdef"
CREATED = datetime(2026, 10, 6, 8, 30, tzinfo=UTC)


def base_of(files):
    return WorkbookBase(GENERATION, CREATED, files)


def test_base_constants():
    assert (LISTS_SHEET, BASE_SHEET, WORKBOOK_FORMAT, BASE_CHUNK) == (
        "_lists",
        "_base",
        1,
        32000,
    )


def test_base_rows_start_with_the_marker_and_round_trip():
    files = {"subjects.tsv": "study\tname\nExample\tall\n", "outputs_Tab1.tsv": ""}
    rows = base_rows(base_of(files))
    assert rows[0] == ("pkdb workbook", 1, GENERATION, CREATED.isoformat())
    text = files["subjects.tsv"]
    assert (
        "subjects.tsv",
        hashlib.sha256(text.encode()).hexdigest(),
        0,
        base64.b64encode(zlib.compress(text.encode())).decode(),
    ) in rows
    assert parse_base(rows) == base_of(files)


def test_a_long_text_needs_two_chunks_and_round_trips():
    # Hexadecimal digits of random bytes hardly compress.
    text = random.Random(0).randbytes(30000).hex()
    rows = base_rows(base_of({"outputs_Tab1.tsv": text}))
    assert [row[2] for row in rows[1:]] == [0, 1]
    assert len(str(rows[1][3])) == BASE_CHUNK
    assert parse_base(rows).files == {"outputs_Tab1.tsv": text}


def test_parse_base_ignores_trailing_empty_cells_and_rows():
    rows = [(*row, None) for row in base_rows(base_of({"subjects.tsv": "a\tb\n"}))] + [
        (None, None, None, None, None)
    ]
    assert parse_base(rows).files == {"subjects.tsv": "a\tb\n"}


def tampered(rows, index, value):
    row = list(rows[1])
    row[index] = value
    return [rows[0], tuple(row), *rows[2:]]


@pytest.mark.parametrize(
    "change",
    [
        lambda rows: [("other", *rows[0][1:]), *rows[1:]],
        lambda rows: [],
        lambda rows: [rows[0][:2], *rows[1:]],
        lambda rows: [(*rows[0][:3], "yesterday"), *rows[1:]],
        lambda rows: [(*rows[0][:3], "2026-10-06T08:30:00"), *rows[1:]],
        lambda rows: [(rows[0][0], "1", *rows[0][2:]), *rows[1:]],
        lambda rows: tampered(rows, 3, rows[1][3][:-6] + "AAAAAA"),
        lambda rows: tampered(rows, 3, "not base64!"),
        lambda rows: tampered(rows, 1, "0" * 64),
        lambda rows: tampered(rows, 2, 1),
        lambda rows: tampered(rows, 2, None),
        lambda rows: [*rows, rows[1]],
    ],
)
def test_parse_base_rejects_invalid_content(change):
    rows = base_rows(base_of({"subjects.tsv": "study\tname\nExample\tall\n"}))
    with pytest.raises(BaseError) as error:
        parse_base(change(rows))
    assert error.value.code == "workbook_base_invalid"
    assert error.value.message


def test_parse_base_reports_a_newer_format():
    rows = base_rows(base_of({"subjects.tsv": "a\n"}))
    with pytest.raises(BaseError) as error:
        parse_base([(rows[0][0], 2, *rows[0][2:]), *rows[1:]])
    assert error.value.code == "workbook_newer"


def test_sync_state_round_trips_for_its_generation(tmp_path):
    workbook = tmp_path / "Example.xlsx"
    files = {"subjects.tsv": "study\tname\n", "outputs_Tab1.tsv": None}
    write_state(workbook, GENERATION, files)
    assert json.loads(state_path(workbook).read_text(encoding="utf-8")) == {
        "format": 1,
        "generation": GENERATION,
        "files": files,
    }
    assert read_state(workbook, GENERATION) == files
    assert read_state(workbook, "f" * 32) == {}


@pytest.mark.parametrize(
    "content",
    [
        b"{not json",
        b"\xff\xfe",
        b"[]",
        b'{"format": 2, "generation": "%s", "files": {}}' % GENERATION.encode(),
        b'{"format": 1, "generation": "%s", "files": []}' % GENERATION.encode(),
        b'{"format": 1, "generation": "%s", "files": {"a.tsv": 1}}'
        % GENERATION.encode(),
    ],
)
def test_a_corrupt_sync_state_is_ignored(tmp_path, content):
    workbook = tmp_path / "Example.xlsx"
    state_path(workbook).write_bytes(content)
    assert read_state(workbook, GENERATION) == {}


def test_remove_state(tmp_path):
    workbook = tmp_path / "Example.xlsx"
    assert read_state(workbook, GENERATION) == {}
    remove_state(workbook)
    write_state(workbook, GENERATION, {"subjects.tsv": "study\n"})
    remove_state(workbook)
    assert not state_path(workbook).exists()
