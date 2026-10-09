"""The desired GitHub issue of each format 2 study and the changes that align the issues.

Everything here is pure except `read_studies`, which only reads the checkout.
"""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from pkdb.issues.github import Issue
from pkdb.repository import location, study_folders
from pkdb.schemas.curators import Curator
from pkdb.studyformat.metadata import MetadataError, read_metadata
from pkdb.studyformat.review_edit import ReviewError, read_review
from pkdb.studyformat.tables import STUDY_JSON
from pkdb.studyformat.validation import is_v2_folder

WORKFLOW = {"draft": "curate", "in_review": "check", "approved": "approved"}
LABEL_COLORS = {"curate": "fbca04", "check": "1d76db", "approved": "0e8a16"}
SUBSTANCE_COLOR = "c5def5"
MAX_ASSIGNEES = 10


@dataclass(frozen=True)
class StudyState:
    """What the issue sync needs of one format 2 study.

    `users` are the curators, then the reviewers, without repeats.
    """

    location: str
    folder: Path
    issue: int | None
    status: str
    released: bool
    users: tuple[str, ...]
    metadata_revision: str
    review_revision: str


@dataclass(frozen=True)
class Studies:
    """The readable format 2 studies, the unreadable ones, and the format 1 count."""

    states: list[StudyState]
    errors: list[str]
    format_1: int


def read_studies(root: Path) -> Studies:
    """Every format 2 study of a checkout.

    A study whose `study.json` or `review.json` cannot be read is an error;
    format 1 folders are counted; folders without `study.json` are skipped.
    """
    states: list[StudyState] = []
    errors: list[str] = []
    format_1 = 0
    for folder in study_folders(root):
        if not (folder / STUDY_JSON).is_file():
            continue
        if not is_v2_folder(folder):
            format_1 += 1
            continue
        try:
            metadata = read_metadata(folder)
            review = read_review(folder)
        except (MetadataError, ReviewError) as error:
            errors.append(f"{location(folder)}: {error}")
            continue
        users = [curator.user for curator in metadata.metadata.curators]
        users += review.review.reviewers
        states.append(
            StudyState(
                location=location(folder),
                folder=folder,
                issue=metadata.metadata.issue,
                status=review.review.status,
                released=metadata.metadata.release is not None,
                users=tuple(dict.fromkeys(users)),
                metadata_revision=metadata.revision,
                review_revision=review.revision,
            )
        )
    return Studies(states, errors, format_1)


@dataclass(frozen=True)
class Roster:
    """PK-DB usernames with their GitHub login, and the logins GitHub can assign.

    `assignable` holds the logins in lower case, as GitHub compares them; build
    a roster with `Roster.of`.
    """

    logins: dict[str, str | None]
    assignable: frozenset[str]

    @classmethod
    def of(cls, curators: list[Curator], assignable: set[str]) -> Roster:
        return cls(
            logins={curator.username: curator.github or None for curator in curators},
            assignable=frozenset(login.casefold() for login in assignable),
        )


class Problems:
    """Warnings about the users of studies, for the summary of a sync.

    A message about a user is counted once per study in which it occurs: `add`
    counts one more study. A message about a study is kept as it is.
    """

    def __init__(self) -> None:
        self._users: Counter[str] = Counter()
        self._studies: list[str] = []

    def add(self, message: str) -> None:
        """Count a message about a user for one more study."""
        self._users[message] += 1

    def add_study(self, message: str) -> None:
        """Keep a message about one study."""
        self._studies.append(message)

    def extend(self, other: Problems) -> None:
        """Add the problems of another collection."""
        self._users.update(other._users)
        self._studies.extend(other._studies)

    def rendered(self) -> list[str]:
        """Every message, the ones about users with their number of studies, sorted."""
        users = [
            f"{message} ({count} {'study' if count == 1 else 'studies'})"
            for message, count in self._users.items()
        ]
        return sorted([*users, *self._studies])


def desired_assignees(
    state: StudyState, roster: Roster, problems: Problems, *, repository: str
) -> list[str]:
    """The GitHub logins to assign to the issue of a study.

    These are the assignable logins of its users in study order, at most
    `MAX_ASSIGNEES`. Every user who cannot be assigned is a problem, counted
    once for the study.
    """
    found: dict[str, None] = {}
    logins: dict[str, str] = {}
    for user in state.users:
        if user not in roster.logins:
            found[f"User {user} is not in the PK-DB roster"] = None
        elif (login := roster.logins[user]) is None:
            found[f"User {user} has no GitHub login in the PK-DB roster"] = None
        else:
            logins.setdefault(login.casefold(), login)
    assignable = []
    for key, login in logins.items():
        if key in roster.assignable:
            assignable.append(login)
        else:
            found[f"GitHub user {login} cannot be assigned in {repository}"] = None
    for message in found:
        problems.add(message)
    if len(assignable) > MAX_ASSIGNEES:
        problems.add_study(
            f"{state.location} has {len(assignable)} assignees; "
            f"GitHub assigns at most {MAX_ASSIGNEES}"
        )
    return assignable[:MAX_ASSIGNEES]


class IssueChange(BaseModel):
    """What to change on the issue of a study; None leaves a field as it is.

    `labels` is the complete new list; `add_labels` and `remove_labels` show
    the difference.
    """

    model_config = ConfigDict(extra="forbid")

    study: str
    number: int
    title: str | None = None
    labels: list[str] | None = None
    add_labels: list[str] = Field(default_factory=list)
    remove_labels: list[str] = Field(default_factory=list)
    assignees: list[str] | None = None
    state: Literal["open", "closed"] | None = None
    state_reason: str | None = None


class SyncPlan(BaseModel):
    """The changes of the issues, the labels to create first, warnings and errors."""

    model_config = ConfigDict(extra="forbid")

    changes: list[IssueChange] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def plan(
    states: list[StudyState],
    issues: list[Issue],
    roster: Roster,
    *,
    substance_names: list[str],
    label_names: list[str],
    repository: str,
) -> SyncPlan:
    """The changes that align the issue of each study with the study.

    Studies that name one issue together, or an issue the repository does not
    have, are errors and get no change; studies without issue are warnings.
    """
    by_number = {issue.number: issue for issue in issues}
    substances = {name.casefold() for name in substance_names}
    shared = _duplicates(states)
    errors = [
        f"Issue #{number} is named by several studies: {', '.join(locations)}"
        for number, locations in shared.items()
    ]
    warnings: list[str] = []
    changes: list[IssueChange] = []
    problems = Problems()
    for state in states:
        if state.issue is None:
            warnings.append(
                f"{state.location} has no issue; pkdb issues sync --adopt gives it one"
            )
        elif state.issue in shared:
            continue
        elif (issue := by_number.get(state.issue)) is None:
            errors.append(
                f"{state.location} names issue #{state.issue}, "
                f"which is not an issue of {repository}"
            )
        else:
            assignees = desired_assignees(
                state, roster, problems, repository=repository
            )
            fields = (
                _title(state, issue)
                | _labels(state, issue, substances)
                | _assignees(issue, assignees)
                | _state(state, issue)
            )
            if fields:
                changes.append(
                    IssueChange(study=state.location, number=issue.number, **fields)
                )
    return SyncPlan(
        changes=changes,
        labels=_missing_labels(changes, label_names),
        warnings=warnings + problems.rendered(),
        errors=errors,
    )


def _duplicates(states: list[StudyState]) -> dict[int, list[str]]:
    """The issue numbers named by several studies, with their locations."""
    named: dict[int, list[str]] = {}
    for state in states:
        if state.issue is not None:
            named.setdefault(state.issue, []).append(state.location)
    return {
        number: locations
        for number, locations in sorted(named.items())
        if len(locations) > 1
    }


def _title(state: StudyState, issue: Issue) -> dict[str, Any]:
    """The location as title, when the issue has another one."""
    return {} if issue.title == state.location else {"title": state.location}


def _labels(state: StudyState, issue: Issue, substances: set[str]) -> dict[str, Any]:
    """The new labels when the label set differs, ignoring case.

    Labels other than workflow and substance labels stay in their current order
    and spelling; the substance and the workflow label of the study follow.
    """
    substance = state.location.partition("/")[0]
    managed = substances | {substance.casefold(), *WORKFLOW.values()}
    kept = [label for label in issue.labels if label.casefold() not in managed]
    labels = [*kept, substance, WORKFLOW[state.status]]
    current = {label.casefold() for label in issue.labels}
    wanted = {label.casefold() for label in labels}
    if current == wanted:
        return {}
    return {
        "labels": labels,
        "add_labels": [label for label in labels if label.casefold() not in current],
        "remove_labels": [
            label for label in issue.labels if label.casefold() not in wanted
        ],
    }


def _assignees(issue: Issue, assignees: list[str]) -> dict[str, Any]:
    """The desired assignees, sorted, when the set differs, ignoring case."""
    current = {login.casefold() for login in issue.assignees}
    if current == {login.casefold() for login in assignees}:
        return {}
    return {"assignees": sorted(assignees, key=str.casefold)}


def _state(state: StudyState, issue: Issue) -> dict[str, Any]:
    """Closed as completed when the study is released and approved, else open."""
    if state.released and state.status == "approved":
        if issue.state != "closed" or issue.state_reason != "completed":
            return {"state": "closed", "state_reason": "completed"}
    elif issue.state == "closed":
        return {"state": "open", "state_reason": "reopened"}
    return {}


def _missing_labels(changes: list[IssueChange], label_names: list[str]) -> list[str]:
    """The labels the changes add that the repository does not have, sorted."""
    existing = {name.casefold() for name in label_names}
    missing: dict[str, str] = {}
    for change in changes:
        for label in change.add_labels:
            if label.casefold() not in existing:
                missing.setdefault(label.casefold(), label)
    return sorted(missing.values(), key=str.casefold)
