import re

import pytest

from pkdb.studyformat.revision import (
    ABSENT,
    RevisionConflict,
    folder_lock,
    read_revision,
    revision_of,
    write_checked,
)
from pkdb.studyformat.ulid import new_ulid

ULID = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def test_revision_of_missing_and_present(tmp_path):
    path = tmp_path / "study.json"
    assert read_revision(path) == (None, ABSENT)
    path.write_bytes(b"{}\n")
    assert read_revision(path) == (b"{}\n", revision_of(b"{}\n"))


def test_write_checked_refuses_a_stale_revision(tmp_path):
    path = tmp_path / "review.json"
    path.write_text("old\n", encoding="utf-8", newline="")
    stale = revision_of(b"older\n")
    with folder_lock(tmp_path), pytest.raises(RevisionConflict) as error:
        write_checked(path, "new\n", stale)
    assert error.value.content == "old\n"
    assert path.read_text(encoding="utf-8") == "old\n"
    with folder_lock(tmp_path):
        assert write_checked(path, "new\n", revision_of(b"old\n")) == revision_of(
            b"new\n"
        )


def test_ulids_are_valid_and_increase():
    ids = [new_ulid(now_ms=1_700_000_000_000) for _ in range(1000)]
    assert all(ULID.fullmatch(value) for value in ids)
    assert ids == sorted(ids) and len(set(ids)) == len(ids)
    assert new_ulid(now_ms=1) > ids[-1]  # a clock going back keeps the order
