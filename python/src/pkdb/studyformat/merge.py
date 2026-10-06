"""Three-way merge of text lines with diff3 semantics, as in `git merge-file`.

The algorithm reimplements the `merge3` module of bzr (Breezy). Each side is diffed against the base, the matching blocks of both diffs are intersected into sync regions where base, ours and theirs agree, and every gap between two sync regions is classified:

- unchanged on both sides, or changed identically on both sides: taken once;
- changed on one side only: that side;
- changed differently on both sides: a conflict.

Changes to the same or adjacent base lines therefore conflict; changes are adjacent when no unchanged base line separates them.

Lines carry no line terminators. Callers split canonical TSV text with `text.removesuffix("\\n").split("\\n")`, and an empty text has no lines. Never use `str.splitlines()`, because it also breaks at U+0085, U+2028 and U+2029, which cells may contain.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal, get_args

# The side whose lines resolve a conflicting region.
Preference = Literal["ours", "theirs"]
PREFERENCES: tuple[Preference, ...] = get_args(Preference)


@dataclass(frozen=True)
class Conflict:
    """Different changes of both sides to the same or adjacent base lines.

    Each side holds its lines of the region. The starts are the 0-based indices of the region in the base, ours and theirs sequences.
    """

    base: tuple[str, ...]
    ours: tuple[str, ...]
    theirs: tuple[str, ...]
    base_start: int
    ours_start: int
    theirs_start: int


@dataclass(frozen=True)
class MergeResult:
    """Merged lines, None exactly when there are conflicts and no preferred side.

    With a preferred side, the lines resolve every conflict to that side, and the conflicts still list what was resolved.
    """

    lines: tuple[str, ...] | None
    conflicts: tuple[Conflict, ...]


def merge_lines(
    base: Sequence[str],
    ours: Sequence[str],
    theirs: Sequence[str],
    *,
    prefer: Preference | None = None,
) -> MergeResult:
    """Merge the changes of ours and theirs to base.

    With `prefer`, each conflicting region takes that side's lines, and every other region merges normally.
    """
    for name, content in (("base", base), ("ours", ours), ("theirs", theirs)):
        if isinstance(content, str):
            raise TypeError(f"{name} must be a sequence of lines, not a string")
    if prefer is not None and prefer not in PREFERENCES:
        raise ValueError(f"prefer must be 'ours', 'theirs' or None, not {prefer!r}")
    base, ours, theirs = tuple(base), tuple(ours), tuple(theirs)

    merged: list[str] = []
    conflicts: list[Conflict] = []
    base_at = ours_at = theirs_at = 0
    for base_sync, ours_sync, theirs_sync, length in _sync_regions(base, ours, theirs):
        base_gap = base[base_at:base_sync]
        ours_gap = ours[ours_at:ours_sync]
        theirs_gap = theirs[theirs_at:theirs_sync]
        if ours_gap == theirs_gap or theirs_gap == base_gap:
            merged.extend(ours_gap)
        elif ours_gap == base_gap:
            merged.extend(theirs_gap)
        else:
            conflicts.append(
                Conflict(base_gap, ours_gap, theirs_gap, base_at, ours_at, theirs_at)
            )
            if prefer == "ours":
                merged.extend(ours_gap)
            elif prefer == "theirs":
                merged.extend(theirs_gap)
        merged.extend(base[base_sync : base_sync + length])
        base_at = base_sync + length
        ours_at = ours_sync + length
        theirs_at = theirs_sync + length

    lines = None if conflicts and prefer is None else tuple(merged)
    return MergeResult(lines, tuple(conflicts))


def _matching_blocks(
    base: tuple[str, ...], side: tuple[str, ...]
) -> list[tuple[int, int, int]]:
    """Runs of equal lines of base and side, as `SequenceMatcher.get_matching_blocks` gives them.

    The common prefix and suffix are matched first and only the lines between them are diffed, as `xdl_trim_ends` of git's xdiff does. Otherwise SequenceMatcher, which matches the longest run of equal lines first, aligns repeated lines away from a change, and the diff is slow for tables with few distinct lines.
    """
    limit = min(len(base), len(side))
    prefix = 0
    while prefix < limit and base[prefix] == side[prefix]:
        prefix += 1
    suffix = 0
    while suffix < limit - prefix and base[-1 - suffix] == side[-1 - suffix]:
        suffix += 1
    middle = SequenceMatcher(
        None,
        base[prefix : len(base) - suffix],
        side[prefix : len(side) - suffix],
        autojunk=False,
    ).get_matching_blocks()
    found = [
        (0, 0, prefix),
        *((start + prefix, other + prefix, length) for start, other, length in middle),
        (len(base) - suffix, len(side) - suffix, suffix),
    ]
    blocks: list[tuple[int, int, int]] = []
    for start, other, length in found:
        if not length:
            continue
        if blocks and blocks[-1][0] + blocks[-1][2] == start:
            if blocks[-1][1] + blocks[-1][2] == other:
                # Adjacent runs are one block, as SequenceMatcher gives them.
                blocks[-1] = (*blocks[-1][:2], blocks[-1][2] + length)
                continue
        blocks.append((start, other, length))
    blocks.append((len(base), len(side), 0))
    return blocks


def _sync_regions(
    base: tuple[str, ...], ours: tuple[str, ...], theirs: tuple[str, ...]
) -> list[tuple[int, int, int, int]]:
    """Runs of base lines that both sides kept, in order.

    Each region is (base start, ours start, theirs start, length). The last region has length zero and starts at the ends of all three sequences.
    """
    ours_blocks, theirs_blocks = (
        _matching_blocks(base, side) for side in (ours, theirs)
    )
    regions: list[tuple[int, int, int, int]] = []
    ours_index = theirs_index = 0
    while ours_index < len(ours_blocks) and theirs_index < len(theirs_blocks):
        ours_base, ours_start, ours_length = ours_blocks[ours_index]
        theirs_base, theirs_start, theirs_length = theirs_blocks[theirs_index]
        start = max(ours_base, theirs_base)
        ours_end = ours_base + ours_length
        theirs_end = theirs_base + theirs_length
        end = min(ours_end, theirs_end)
        if start < end:
            regions.append(
                (
                    start,
                    ours_start + start - ours_base,
                    theirs_start + start - theirs_base,
                    end - start,
                )
            )
        # Advance the block that ends first in the base.
        if ours_end < theirs_end:
            ours_index += 1
        else:
            theirs_index += 1
    regions.append((len(base), len(ours), len(theirs), 0))
    return regions
