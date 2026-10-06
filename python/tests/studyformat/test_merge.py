"""Three-way line merge with diff3 semantics, as in git merge-file."""

import os
import random
import shutil
import subprocess
import time
from typing import Any

import pytest

from pkdb.studyformat.merge import Conflict, MergeResult, merge_lines

# Characters that str.splitlines() treats as line breaks but TSV cells may hold.
SEPARATORS = (chr(0x85), chr(0x2028), chr(0x2029))
GIT = shutil.which("git")


def lines(text: str) -> tuple[str, ...]:
    """One line per character, so that cases read as short strings."""
    return tuple(text)


def split(text: str) -> list[str]:
    """Canonical TSV text as lines, the way the sync engine splits it."""
    return text.removesuffix("\n").split("\n") if text else []


def joined(content) -> str:
    return "".join(f"{line}\n" for line in content)


def merge(base: str, ours: str, theirs: str, **options) -> MergeResult:
    return merge_lines(lines(base), lines(ours), lines(theirs), **options)


@pytest.mark.parametrize(
    ("base", "changed"),
    [
        ("abc", "abc"),
        ("abc", "aXc"),
        ("abc", ""),
        ("", "abc"),
        ("abc", "abcd"),
        ("abc", "dabc"),
        ("aab", "abab"),
        ("abab", "ba"),
    ],
)
def test_identities(base, changed):
    expected = MergeResult(lines(changed), ())
    assert merge(base, changed, base) == expected
    assert merge(base, base, changed) == expected
    assert merge(base, changed, changed) == expected


CLEAN = [
    pytest.param("abcde", "aXbcde", "abcdYe", "aXbcdYe", id="insertions"),
    pytest.param("abc", "Xabc", "abcY", "XabcY", id="insertions-at-the-ends"),
    pytest.param("abcde", "bcde", "abce", "bce", id="deletions"),
    pytest.param("abcdef", "abXdef", "abcde", "abXde", id="edit-and-distant-delete"),
    pytest.param("abcde", "aXcde", "abcYe", "aXcYe", id="one-unchanged-line-between"),
    pytest.param("abcde", "aXcde", "aXcdY", "aXcdY", id="same-change-and-other"),
    pytest.param("abcde", "acde", "acd", "acd", id="same-delete-and-other"),
    pytest.param("ab", "abX", "abX", "abX", id="same-append"),
    pytest.param("", "ab", "ab", "ab", id="empty-base-same-content"),
]


@pytest.mark.parametrize(("base", "ours", "theirs", "expected"), CLEAN)
def test_clean_merge(base, ours, theirs, expected):
    assert merge(base, ours, theirs) == MergeResult(lines(expected), ())
    assert merge(base, theirs, ours) == MergeResult(lines(expected), ())


CONFLICTS = [
    pytest.param(
        "abcde",
        "abXde",
        "abYde",
        (Conflict(("c",), ("X",), ("Y",), 2, 2, 2),),
        id="same-line-edited",
    ),
    pytest.param(
        "abcdef",
        "PQabcdXf",
        "abdYf",
        (Conflict(("e",), ("X",), ("Y",), 4, 6, 3),),
        id="starts-differ",
    ),
    pytest.param(
        "abcde",
        "abXde",
        "abcYe",
        (Conflict(("c", "d"), ("X", "d"), ("c", "Y"), 2, 2, 2),),
        id="adjacent-edits",
    ),
    pytest.param(
        "abcd",
        "abXcd",
        "abYd",
        (Conflict(("c",), ("X", "c"), ("Y",), 2, 2, 2),),
        id="insertion-next-to-edit",
    ),
    pytest.param(
        "ab",
        "aXb",
        "aYb",
        (Conflict((), ("X",), ("Y",), 1, 1, 1),),
        id="insertions-at-one-place",
    ),
    pytest.param(
        "abc",
        "aXc",
        "ac",
        (Conflict(("b",), ("X",), (), 1, 1, 1),),
        id="edit-and-delete",
    ),
    pytest.param(
        "abc",
        "",
        "aXc",
        (Conflict(("a", "b", "c"), (), ("a", "X", "c"), 0, 0, 0),),
        id="delete-all-and-edit",
    ),
    pytest.param(
        "ab",
        "abX",
        "abY",
        (Conflict((), ("X",), ("Y",), 2, 2, 2),),
        id="different-appends",
    ),
    pytest.param(
        "",
        "ab",
        "cd",
        (Conflict((), ("a", "b"), ("c", "d"), 0, 0, 0),),
        id="empty-base",
    ),
    pytest.param(
        "abcde",
        "XbcdY",
        "ZbcdW",
        (
            Conflict(("a",), ("X",), ("Z",), 0, 0, 0),
            Conflict(("e",), ("Y",), ("W",), 4, 4, 4),
        ),
        id="two-conflicts",
    ),
]


@pytest.mark.parametrize(("base", "ours", "theirs", "conflicts"), CONFLICTS)
def test_conflict(base, ours, theirs, conflicts):
    assert merge(base, ours, theirs) == MergeResult(None, conflicts)


@pytest.mark.parametrize(
    ("base", "ours", "theirs", "keep_ours", "keep_theirs"),
    [
        ("abcdefg", "abXdEfg", "abYdefG", "abXdEfG", "abYdEfG"),
        ("abcdef", "PQabcdXf", "abdYf", "PQabdXf", "PQabdYf"),
        ("abcde", "XbcdY", "ZbcdW", "XbcdY", "ZbcdW"),
        ("abc", "", "aXc", "", "aXc"),
        ("abcde", "aXcde", "abcYe", "aXcYe", "aXcYe"),
    ],
)
def test_prefer_resolves_only_the_conflicting_regions(
    base, ours, theirs, keep_ours, keep_theirs
):
    conflicts = merge(base, ours, theirs).conflicts
    assert merge(base, ours, theirs, prefer="ours") == MergeResult(
        lines(keep_ours), conflicts
    )
    assert merge(base, ours, theirs, prefer="theirs") == MergeResult(
        lines(keep_theirs), conflicts
    )


def test_lines_keep_unicode_line_separators():
    note = "x".join(SEPARATORS)
    base = f"name\tcomment\nA\t{note}\nB\tb\nC\tc\nD\td\nE\te\n"
    assert len(base.splitlines()) > len(split(base))
    ours = base.replace("A\t", "A\tnew ").replace("C\tc", "C\tours")
    theirs = base.replace("E\te", f"E\te{SEPARATORS[1]}")

    result = merge_lines(split(base), split(ours), split(theirs))
    assert result.conflicts == ()
    assert joined(result.lines) == (
        f"name\tcomment\nA\tnew {note}\nB\tb\nC\tours\nD\td\nE\te{SEPARATORS[1]}\n"
    )

    theirs = theirs.replace("C\tc", "C\ttheirs")
    conflict = Conflict(("C\tc",), ("C\tours",), ("C\ttheirs",), 3, 3, 3)
    assert merge_lines(split(base), split(ours), split(theirs)) == MergeResult(
        None, (conflict,)
    )


def test_a_string_is_not_a_sequence_of_lines():
    with pytest.raises(TypeError, match="ours"):
        merge_lines(["a"], "a\n", ["a"])


def test_an_unknown_preference_is_rejected():
    prefer: Any = "workbook"
    with pytest.raises(ValueError, match="workbook"):
        merge_lines(["a"], ["b"], ["c"], prefer=prefer)


def edited(rng: random.Random, content: list[str], count: int) -> list[str]:
    """Content after count random insertions, deletions and replacements."""
    content = list(content)
    for _ in range(count):
        kind = rng.choice(("insert", "delete", "replace"))
        new = f"n{rng.randrange(4)}"
        if kind == "insert" or not content:
            content.insert(rng.randint(0, len(content)), new)
        elif kind == "delete":
            del content[rng.randrange(len(content))]
        else:
            content[rng.randrange(len(content))] = new
    return content


def random_case(seed: int) -> tuple[list[str], list[str], list[str]]:
    """20 unique base lines and two sides with up to 4 edits each.

    New lines never equal a base line, so every diff of the base against a side is unambiguous and git aligns it the same way. Some cases start both sides from shared edits, so identical changes occur.
    """
    rng = random.Random(seed)
    base = [f"b{index}{(*SEPARATORS, '')[index % 4]}" for index in range(20)]
    shared = rng.randint(0, 2) if rng.random() < 0.3 else 0
    common = edited(rng, base, shared)
    ours = edited(rng, common, rng.randint(0, 4 - shared))
    theirs = edited(rng, common, rng.randint(0, 4 - shared))
    return base, ours, theirs


GIT_ENV = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}


def git_merge(folder, base, ours, theirs, *options) -> tuple[bool, str]:
    """Whether `git merge-file -p` merges cleanly, and its output."""
    paths = []
    for name, content in (("ours", ours), ("base", base), ("theirs", theirs)):
        path = folder / name
        path.write_bytes(joined(content).encode())
        paths.append(str(path))
    assert GIT is not None
    completed = subprocess.run(
        [GIT, "merge-file", "-p", *options, *paths],
        capture_output=True,
        cwd=folder,
        env=GIT_ENV,
        check=False,
    )
    assert 0 <= completed.returncode < 128, completed.stderr
    return completed.returncode == 0, completed.stdout.decode()


def test_random_merges_keep_both_sides_changes(tmp_path):
    outcomes = {"clean": 0, "conflict": 0}
    for seed in range(500):
        base, ours, theirs = random_case(seed)
        result = merge_lines(base, ours, theirs)
        assert result == merge_lines(base, ours, theirs), seed
        if result.lines is None:
            outcomes["conflict"] += 1
        else:
            outcomes["clean"] += 1
            kept = [line for line in base if line in ours and line in theirs]
            assert [line for line in result.lines if line in base] == kept, seed
            added = (set(ours) | set(theirs)) - set(base)
            assert set(result.lines) - set(base) == added, seed
        if GIT is not None:
            clean, text = git_merge(tmp_path, base, ours, theirs)
            assert clean == (result.lines is not None), seed
            if clean:
                assert text == joined(result.lines), seed
            for side in ("ours", "theirs"):
                preferred = merge_lines(base, ours, theirs, prefer=side)
                assert preferred.conflicts == result.conflicts, seed
                if result.conflicts:
                    _, text = git_merge(tmp_path, base, ours, theirs, f"--{side}")
                    assert text == joined(preferred.lines), (seed, side)
                else:
                    assert preferred == result, (seed, side)
    assert min(outcomes.values()) > 100, outcomes


@pytest.mark.parametrize("seed", range(200))
def test_conflicts_locate_their_lines_in_every_input(seed):
    rng = random.Random(seed)
    base = [rng.choice("abc") for _ in range(rng.randint(0, 12))]
    ours = edited(rng, base, rng.randint(0, 4))
    theirs = edited(rng, base, rng.randint(0, 4))
    result = merge_lines(base, ours, theirs)
    for conflict in result.conflicts:
        for content, start, region in (
            (base, conflict.base_start, conflict.base),
            (ours, conflict.ours_start, conflict.ours),
            (theirs, conflict.theirs_start, conflict.theirs),
        ):
            assert tuple(content[start : start + len(region)]) == region
    # An unchanged line separates consecutive conflicts in every input.
    for earlier, later in zip(result.conflicts, result.conflicts[1:]):
        assert later.base_start > earlier.base_start + len(earlier.base)
        assert later.ours_start > earlier.ours_start + len(earlier.ours)
        assert later.theirs_start > earlier.theirs_start + len(earlier.theirs)
    assert (result.lines is None) == bool(result.conflicts)
    for side in ("ours", "theirs"):
        preferred = merge_lines(base, ours, theirs, prefer=side)
        assert preferred.conflicts == result.conflicts
        assert preferred.lines is not None
        if not result.conflicts:
            assert preferred.lines == result.lines


def test_large_tables_merge_quickly():
    rng = random.Random(7)
    base = [
        f"row {index}\tdrug\tplasma\t{index * 0.25}\tmg/l" for index in range(20_000)
    ]
    positions = rng.sample(range(0, 20_000, 4), 400)
    ours, theirs = list(base), list(base)
    for side, position in zip((ours, theirs) * 200, sorted(positions)):
        side[position] = f"changed {position}"
    assert sum(line != old for line, old in zip(ours, base)) == 200

    start = time.perf_counter()
    result = merge_lines(base, ours, theirs)
    elapsed = time.perf_counter() - start

    expected = [
        theirs[index] if ours[index] == line else ours[index]
        for index, line in enumerate(base)
    ]
    assert result == MergeResult(tuple(expected), ())
    assert elapsed < 2, f"merging 20,000 lines took {elapsed:.2f} s"


def test_far_apart_changes_to_repeated_lines_merge(tmp_path):
    # SequenceMatcher alone aligns runs of equal lines away from the changes.
    base = ["x"] * 1000
    ours, theirs = list(base), list(base)
    ours[249], theirs[749] = "ours", "theirs"
    expected = list(base)
    expected[249], expected[749] = "ours", "theirs"

    assert merge_lines(base, ours, theirs) == MergeResult(tuple(expected), ())
    if GIT is not None:
        assert git_merge(tmp_path, base, ours, theirs) == (True, joined(expected))


def test_repetitive_tables_merge_quickly():
    base = [f"value {index % 50}" for index in range(20_000)]
    ours, theirs = list(base), list(base)
    ours[5_000], theirs[15_000] = "ours", "theirs"
    expected = list(base)
    expected[5_000], expected[15_000] = "ours", "theirs"

    start = time.perf_counter()
    result = merge_lines(base, ours, theirs)
    elapsed = time.perf_counter() - start

    assert result == MergeResult(tuple(expected), ())
    assert elapsed < 2, f"merging 20,000 lines took {elapsed:.2f} s"


@pytest.mark.parametrize("inserted", [0, 3])
def test_conflicts_in_repeated_lines_start_where_they_are(inserted):
    base = ["x"] * 1000
    ours = [f"new {index}" for index in range(inserted)] + list(base)
    theirs = list(base)
    ours[inserted + 499], theirs[499] = "ours", "theirs"

    result = merge_lines(base, ours, theirs)

    assert result.conflicts == (
        Conflict(("x",), ("ours",), ("theirs",), 499, inserted + 499, 499),
    )
