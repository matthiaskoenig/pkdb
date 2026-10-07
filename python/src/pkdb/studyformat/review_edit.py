"""Checked edits of `review.json`, shared by `pkdb review` and the curation app."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from pkdb.identity import Author
from pkdb.schemas.review import Review, ReviewItem, ReviewTarget, ThreadEntry
from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.issues import make_issue
from pkdb.studyformat.jsonio import JsonFileError, load_json
from pkdb.studyformat.layout import scan_folder
from pkdb.studyformat.load import LoadedStudy, load_study, validation_issues
from pkdb.studyformat.models import canonical_review_json
from pkdb.studyformat.revision import (
    check_revision,
    folder_lock,
    read_revision,
    write_checked,
)
from pkdb.studyformat.tables import REVIEW_JSON
from pkdb.studyformat.ulid import new_ulid
from pkdb.studyformat.validation import validate_folder

CODE = "invalid_review_json"
APPROVED = "The study is approved; set the status to in_review first"


class ReviewError(ValueError):
    """An unknown item, an invalid transition or an invalid file; nothing was written."""

    def __init__(self, message: str, issues: list[ValidationIssue] | None = None):
        super().__init__(message)
        self.issues = issues or []


class ApprovalRefused(ReviewError):
    """Approval needs zero open items, zero validation errors and a person."""


@dataclass(frozen=True)
class ReviewDocument:
    review: Review
    revision: str


def _now(now: datetime | None) -> datetime:
    return (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)


def read_review(folder: Path) -> ReviewDocument:
    data, revision = read_revision(Path(folder) / REVIEW_JSON)
    if data is None:
        raise _invalid(
            [make_issue("missing_file", f"{REVIEW_JSON} is required", file=REVIEW_JSON)]
        )
    try:
        value = load_json(data)
    except JsonFileError as error:
        raise _invalid([make_issue(error.code, str(error), file=REVIEW_JSON)]) from None
    return ReviewDocument(_validated(value), revision)


def _invalid(issues: list[ValidationIssue]) -> ReviewError:
    return ReviewError("; ".join(issue.message for issue in issues), issues)


def _validated(data: object) -> Review:
    try:
        return Review.model_validate(data)
    except ValidationError as error:
        raise _invalid(validation_issues(error, REVIEW_JSON, CODE)) from None


def _update(
    folder: Path, revision: str | None, change: Callable[[Review], Review]
) -> tuple[Review, str]:
    """Read, change and write review.json under the folder lock.

    The changed review is validated before writing. `revision` None writes over
    the current revision. A change that returns the review it was given writes
    nothing and returns the current revision.
    """
    path = Path(folder) / REVIEW_JSON
    with folder_lock(folder):
        document = read_review(folder)
        expected = document.revision if revision is None else revision
        changed = change(document.review)
        if changed is document.review:
            return changed, check_revision(path, expected)
        review = _validated(changed.model_dump(mode="json"))
        new_revision = write_checked(path, canonical_review_json(review), expected)
    return review, new_revision


def _item(review: Review, item_id: str) -> ReviewItem:
    for item in review.items:
        if item.id == item_id:
            return item
    raise ReviewError(f"Review item {item_id} does not exist")


def _replace(review: Review, item: ReviewItem) -> Review:
    items = [item if other.id == item.id else other for other in review.items]
    return review.model_copy(update={"items": items})


def _entry(author: Author, now: datetime | None, text: str) -> ThreadEntry:
    return ThreadEntry(author=author.user, created=_now(now), text=text)


def add_item(
    folder: Path,
    author: Author,
    *,
    kind: Literal["question", "uncertainty", "issue"],
    text: str,
    target: ReviewTarget | None = None,
    acknowledges: str | None = None,
    revision: str | None = None,
    now: datetime | None = None,
) -> tuple[ReviewItem, str]:
    """Add an open item; refused while the study is approved or for a file it lacks."""
    if target is not None and target.file is not None:
        if target.file not in scan_folder(Path(folder)).files:
            message = f"{target.file} is not a file of this study"
            raise ReviewError(
                message,
                [make_issue("unknown_review_target", message, file=REVIEW_JSON)],
            )
    item = ReviewItem(
        id=new_ulid(),
        kind=kind,
        text=text,
        author=author.user,
        agent=author.agent,
        created=_now(now),
        target=target,
        acknowledges=acknowledges,
    )
    return item, _add(folder, item, revision)


def _add(folder: Path, item: ReviewItem, revision: str | None) -> str:
    def change(review: Review) -> Review:
        if item.state == "open" and review.status == "approved":
            raise ReviewError(APPROVED)
        return review.model_copy(update={"items": [*review.items, item]})

    return _update(folder, revision, change)[1]


def reply(
    folder: Path,
    author: Author,
    item_id: str,
    text: str,
    *,
    revision: str | None = None,
    now: datetime | None = None,
) -> str:
    def change(review: Review) -> Review:
        item = _item(review, item_id)
        thread = [*item.thread, _entry(author, now, text)]
        return _replace(review, item.model_copy(update={"thread": thread}))

    return _update(folder, revision, change)[1]


def _close(
    state: str,
    folder: Path,
    author: Author,
    item_id: str,
    text: str | None,
    revision: str | None,
    now: datetime | None,
) -> str:
    """Resolve an open item, or dismiss an open or resolved one."""
    allowed = ("open", "resolved") if state == "dismissed" else ("open",)

    def change(review: Review) -> Review:
        item = _item(review, item_id)
        if item.state not in allowed:
            raise ReviewError(
                f"Review item {item_id} is {item.state}, not {' or '.join(allowed)}"
            )
        thread = [*item.thread, _entry(author, now, text)] if text else item.thread
        changes = {
            "state": state,
            "resolved_by": author.user,
            "resolved": _now(now),
            "thread": thread,
        }
        return _replace(review, item.model_copy(update=changes))

    return _update(folder, revision, change)[1]


def resolve(
    folder: Path,
    author: Author,
    item_id: str,
    text: str | None = None,
    *,
    revision: str | None = None,
    now: datetime | None = None,
) -> str:
    return _close("resolved", folder, author, item_id, text, revision, now)


def dismiss(
    folder: Path,
    author: Author,
    item_id: str,
    text: str | None = None,
    *,
    revision: str | None = None,
    now: datetime | None = None,
) -> str:
    """Dismiss an open or resolved item; a dismissed item acknowledges nothing."""
    return _close("dismissed", folder, author, item_id, text, revision, now)


def reopen(
    folder: Path,
    author: Author,
    item_id: str,
    text: str | None = None,
    *,
    revision: str | None = None,
    now: datetime | None = None,
) -> str:
    def change(review: Review) -> Review:
        item = _item(review, item_id)
        if item.state == "open":
            raise ReviewError(f"Review item {item_id} is open already")
        if review.status == "approved":
            raise ReviewError(APPROVED)
        thread = [*item.thread, _entry(author, now, text)] if text else item.thread
        changes = {
            "state": "open",
            "resolved_by": None,
            "resolved": None,
            "thread": thread,
        }
        return _replace(review, item.model_copy(update=changes))

    return _update(folder, revision, change)[1]


def set_status(
    folder: Path,
    author: Author,
    status: str,
    *,
    vocabulary,
    revision: str | None = None,
    now: datetime | None = None,
) -> str:
    """Set the review status; only approval validates the folder with `vocabulary`.

    Approving an approved study writes nothing and keeps who approved it and when.
    """
    if status == "approved" and author.agent:
        raise ApprovalRefused(
            f"A person must approve a study; this command runs for agent {author.agent}"
        )

    def change(review: Review) -> Review:
        if status != "approved":
            changes = {"status": status, "approved_by": None, "approved": None}
            return review.model_copy(update=changes)
        if review.status == "approved":
            return review
        open_items = [item for item in review.items if item.state == "open"]
        if open_items:
            items = "review item is" if len(open_items) == 1 else "review items are"
            raise ApprovalRefused(f"{len(open_items)} {items} open")
        errors = [
            issue
            for issue in validate_folder(folder, vocabulary).issues
            if issue.severity == "error"
        ]
        if errors:
            noun = "error" if len(errors) == 1 else "errors"
            raise ApprovalRefused(f"Validation has {len(errors)} {noun}", errors)
        reviewers = review.reviewers
        if author.user not in reviewers:
            reviewers = [*reviewers, author.user]
        return review.model_copy(
            update={
                "status": status,
                "approved_by": author.user,
                "approved": _now(now),
                "reviewers": reviewers,
            }
        )

    return _update(folder, revision, change)[1]


def target_for_issue(study: LoadedStudy, issue: ValidationIssue) -> ReviewTarget | None:
    """The review target that pins a warning to its file, row and column."""
    source = issue.source
    if source is None:
        return None
    table = study.table(source.file)
    row = None
    if table is not None and source.row is not None:
        row = next((row for row in table.rows if row.line == source.row), None)
    if table is None or row is None:
        return ReviewTarget(file=source.file)
    filters = {
        name: row.cells[name] for name in table.spec.sort_columns if row.cells.get(name)
    }
    for column in table.spec.columns:
        if table.matching_lines(filters) == {row.line}:
            break
        if not column.owned and column.name not in filters and row.cells[column.name]:
            filters[column.name] = row.cells[column.name]
    column = source.header if source.header in table.header else None
    return ReviewTarget(file=source.file, rows=filters, column=column)


def matching_warnings(
    issues: list[ValidationIssue],
    code: str,
    file: str,
    line: int | None = None,
    column: str | None = None,
) -> list[ValidationIssue]:
    """The warnings `code` of `file`, at `line` and `column` when they are given."""
    return [
        issue
        for issue in issues
        if issue.severity == "warning"
        and issue.code == code
        and issue.source is not None
        and issue.source.file == file
        and (line is None or issue.source.row == line)
        and (column is None or issue.source.header == column)
    ]


def warning_locations(
    issues: list[ValidationIssue],
) -> set[tuple[int | None, str | None]]:
    """The rows and columns of these issues; one item acknowledges the warnings of one."""
    return {(source.row, source.header) for issue in issues if (source := issue.source)}


def acknowledge(
    folder: Path,
    author: Author,
    issue: ValidationIssue,
    text: str,
    *,
    revision: str | None = None,
    now: datetime | None = None,
) -> tuple[ReviewItem, str]:
    """Record a resolved review item that acknowledges the warning `issue`."""
    if issue.severity != "warning":
        raise ReviewError(f"Only warnings can be acknowledged, not [{issue.code}]")
    created = _now(now)
    item = ReviewItem(
        id=new_ulid(),
        kind="issue",
        text=text,
        author=author.user,
        agent=author.agent,
        created=created,
        target=target_for_issue(load_study(Path(folder)), issue),
        acknowledges=issue.code,
        state="resolved",
        resolved_by=author.user,
        resolved=created,
    )
    return item, _add(folder, item, revision)
