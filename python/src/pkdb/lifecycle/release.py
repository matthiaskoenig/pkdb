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


@dataclass(frozen=True)
class Numbered:
    """A released study: its location, its PKDB identifier and its access now."""

    location: str
    pkdb_id: str
    access: str


class ReleaseRefused(Exception):
    """At least one study cannot be released; nothing was written."""

    def __init__(self, refusals: list[Refusal]):
        super().__init__(f"{len(refusals)} studies cannot be released")
        self.refusals = refusals


class ReleaseConflict(Exception):
    """A study.json changed during the release; `released` keeps its numbers.

    `access` is the access given to the release, which the studies written
    before the conflict have now too.
    """

    def __init__(
        self,
        where: str,
        released: list[Numbered],
        reason: str = "study.json changed on disk since it was read",
        access: str | None = None,
    ):
        message = f"{where}: {reason}; nothing was written for it"
        if released:
            new_access = f" with access {access}" if access is not None else ""
            done = ", ".join(
                f"{item.location}: {item.pkdb_id}{new_access}" for item in released
            )
            message += f"; these studies keep their identifiers: {done}"
        super().__init__(message)
        self.location, self.released, self.access = where, released, access


class LargestIdentifierUnknown(ValueError):
    """A study.json or the registry file cannot be read; nothing was written."""

    def __init__(self, reason: str):
        super().__init__(
            f"Cannot find the largest identifier: {reason}; no study was released"
        )


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
    root: Path,
    folders: list[Path],
    vocabulary,
    *,
    on: datetime.date,
    access: str | None = None,
) -> list[Numbered]:
    """Number the studies in argument order after the largest identifier.

    Every study is checked first; when one is refused nothing is written.
    `access`, when given, is written with the release block of every study,
    in the same write; otherwise each study keeps its access.
    """
    revisions, accesses = {}, {}
    refusals = []
    for folder in folders:
        try:
            document = read_metadata(folder)
        except MetadataError as error:
            refusals.append(Refusal(location(folder), [str(error)]))
            continue
        revisions[folder] = document.revision
        accesses[folder] = access or document.metadata.access
        if reasons := check(folder, vocabulary):
            refusals.append(Refusal(location(folder), reasons))
    if refusals:
        raise ReleaseRefused(refusals)
    found = scan(root)
    if found.errors:
        raise LargestIdentifierUnknown("; ".join(found.errors))
    try:
        first = next_identifier(found, root)
    except ValueError as error:
        raise LargestIdentifierUnknown(str(error)) from None
    done: list[Numbered] = []
    for number, folder in enumerate(folders, first):
        pkdb_id = identifier(number)
        patch: dict = {"release": {"pkdb_id": pkdb_id, "date": on.isoformat()}}
        if access is not None:
            patch["access"] = access
        try:
            patch_metadata(folder, patch, revisions[folder])
        except RevisionConflict:
            raise ReleaseConflict(location(folder), done, access=access) from None
        except (MetadataError, OSError) as error:
            raise ReleaseConflict(
                location(folder), done, str(error), access=access
            ) from None
        done.append(Numbered(location(folder), pkdb_id, accesses[folder]))
    return done
