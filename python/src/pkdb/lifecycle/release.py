"""Give approved studies the next PKDB identifiers."""

import datetime
from dataclasses import dataclass
from pathlib import Path

from pkdb.lifecycle.registry import identifier, next_identifier, scan
from pkdb.repository import location
from pkdb.studyformat.metadata import MetadataError, patch_metadata, read_metadata
from pkdb.studyformat.review_edit import ReviewError, approval_blockers, read_review
from pkdb.studyformat.revision import RevisionConflict


@dataclass(frozen=True)
class Refusal:
    location: str
    reasons: list[str]


class ReleaseRefused(Exception):
    """At least one study cannot be released; nothing was written."""

    def __init__(self, refusals: list[Refusal]):
        super().__init__(f"{len(refusals)} studies cannot be released")
        self.refusals = refusals


class ReleaseConflict(Exception):
    """A study.json changed during the release; `released` keeps its numbers."""

    def __init__(
        self,
        where: str,
        released: list[tuple[str, str]],
        reason: str = "study.json changed on disk since it was read",
    ):
        message = f"{where}: {reason}; nothing was written for it"
        if released:
            done = ", ".join(f"{place}: {pkdb_id}" for place, pkdb_id in released)
            message += f"; these studies keep their identifiers: {done}"
        super().__init__(message)
        self.location, self.released = where, released


def check(folder: Path, vocabulary) -> list[str]:
    """The reasons a study cannot be released; empty when it can."""
    reasons = []
    try:
        review = read_review(folder).review
    except ReviewError as error:
        return [str(error)]
    if review.status != "approved":
        reasons.append(
            f"The review status is {review.status}; a study must be approved"
        )
    reasons += [
        str(blocker) for blocker in approval_blockers(folder, review, vocabulary)
    ]
    try:
        released = read_metadata(folder).metadata.release
    except MetadataError as error:
        return [*reasons, str(error)]
    if released is not None:
        reasons.append(f"The study is already released as {released.pkdb_id}")
    return reasons


def release(
    root: Path, folders: list[Path], vocabulary, *, on: datetime.date
) -> list[tuple[str, str]]:
    """Number the studies in argument order after the largest identifier.

    Every study is checked first; when one is refused nothing is written.
    """
    revisions = {}
    refusals = []
    for folder in folders:
        try:
            revisions[folder] = read_metadata(folder).revision
        except MetadataError as error:
            refusals.append(Refusal(location(folder), [str(error)]))
            continue
        if reasons := check(folder, vocabulary):
            refusals.append(Refusal(location(folder), reasons))
    if refusals:
        raise ReleaseRefused(refusals)
    found = scan(root)
    if found.errors:
        raise ValueError(
            "Cannot find the largest identifier: " + "; ".join(found.errors)
        )
    first = next_identifier(found, root)
    done: list[tuple[str, str]] = []
    for number, folder in enumerate(folders, first):
        pkdb_id = identifier(number)
        patch = {"release": {"pkdb_id": pkdb_id, "date": on.isoformat()}}
        try:
            patch_metadata(folder, patch, revisions[folder])
        except RevisionConflict:
            raise ReleaseConflict(location(folder), done) from None
        except (MetadataError, OSError) as error:
            raise ReleaseConflict(location(folder), done, str(error)) from None
        done.append((location(folder), pkdb_id))
    return done
