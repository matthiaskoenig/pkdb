"""Give studies their GitHub issue and align the issues with the studies.

GitHub is written first and `study.json` last: an interrupted adoption leaves
no number on disk, and the rerun finds the renamed or created issue by its
exact title.
"""

from dataclasses import dataclass, replace
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from pkdb.identity import Author
from pkdb.issues.adopt import DUPLICATE, Adoption, match
from pkdb.issues.github import GitHub, GitHubError, Issue
from pkdb.issues.state import (
    LABEL_COLORS,
    SUBSTANCE_COLOR,
    WORKFLOW,
    Problems,
    Roster,
    StudyState,
    SyncPlan,
    desired_assignees,
    plan,
    read_studies,
)
from pkdb.repository import substances
from pkdb.schemas.curators import Curator
from pkdb.studyformat.metadata import MetadataError, patch_metadata
from pkdb.studyformat.review_edit import ReviewError, set_status
from pkdb.studyformat.revision import RevisionConflict


class AdoptionResult(BaseModel):
    """The issue a study without one got; `number` is None for a new issue in a dry run."""

    model_config = ConfigDict(extra="forbid")

    study: str
    number: int | None
    created: bool = False
    renamed: bool = False
    duplicates: list[int] = Field(default_factory=list)
    in_review: bool = False


class SyncResult(BaseModel):
    """What a sync adopted, planned and changed, with its warnings and errors."""

    model_config = ConfigDict(extra="forbid")

    repository: str
    dry_run: bool
    adopted: list[AdoptionResult] = Field(default_factory=list)
    plan: SyncPlan
    applied: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    format_1: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def sync(
    root: Path,
    github: GitHub,
    roster: list[Curator],
    *,
    adopt: bool = False,
    author: Author | None = None,
    dry_run: bool = False,
) -> SyncResult:
    """Align the issue of every format 2 study; with `adopt`, give studies an issue.

    Adoption is the only part that writes files, `study.json` and `review.json`
    of the adopted studies. A dry run reads GitHub and writes nothing. A
    GitHubError for the token, a permission or the rate limit stops the run;
    any other failure is an error of its study, and the run goes on.
    """
    if adopt and author is None:
        raise ValueError("Adoption writes study.json and needs a PK-DB user")
    studies = read_studies(root)
    run = _Run(
        github=github,
        dry_run=dry_run,
        issues={issue.number: issue for issue in github.issues()},
        roster=Roster.of(roster, github.assignable()),
        label_names=github.labels(),
        errors=list(studies.errors),
    )
    states, adopted = studies.states, []
    if adopt and author is not None:
        states, adopted = _adopt(run, states, author)
    changes = plan(
        states,
        list(run.issues.values()),
        run.roster,
        substance_names=substances(root),
        label_names=run.label_names,
        repository=github.repository,
    )
    run.errors += changes.errors
    applied = 0 if dry_run else _apply(run, changes)
    return SyncResult(
        repository=github.repository,
        dry_run=dry_run,
        adopted=adopted,
        plan=changes,
        applied=applied,
        warnings=changes.warnings,
        errors=run.errors,
        format_1=studies.format_1,
    )


@dataclass
class _Run:
    """The GitHub repository as the sync knows it, and the errors so far."""

    github: GitHub
    dry_run: bool
    issues: dict[int, Issue]
    roster: Roster
    label_names: list[str]
    errors: list[str]

    def fail(self, where: str, error: GitHubError) -> None:
        """Record a failed GitHub request, or raise one that every request would hit."""
        if error.rate_limited or error.status_code in (401, 403):
            raise error
        self.errors.append(f"{where}: {error}")


def _adopt(
    run: _Run, states: list[StudyState], author: Author
) -> tuple[list[StudyState], list[AdoptionResult]]:
    """Give each study without issue one; the states to plan and the adoptions.

    A study whose adoption fails, or that gets a new issue in a dry run, is
    left out of the plan.
    """
    adoptions = {
        adoption.study.location: adoption
        for adoption in match(states, list(run.issues.values()))
    }
    planned: list[StudyState] = []
    adopted: list[AdoptionResult] = []
    for state in states:
        if (adoption := adoptions.get(state.location)) is None:
            planned.append(state)
            continue
        try:
            result, adopted_state = _adopt_one(run, adoption, author)
        except GitHubError as error:
            run.fail(state.location, error)
            continue
        except RevisionConflict as conflict:
            run.errors.append(
                f"{state.location}: {conflict.file} changed on disk; run the sync again"
            )
            continue
        except (MetadataError, ReviewError) as error:
            run.errors.append(f"{state.location}: {error}")
            continue
        adopted.append(result)
        if adopted_state is not None:
            planned.append(adopted_state)
    return planned, adopted


def _adopt_one(
    run: _Run, adoption: Adoption, author: Author
) -> tuple[AdoptionResult, StudyState | None]:
    """Adopt or create the issue of one study and record its number.

    The review status is written before the number, so that a study whose
    `review.json` cannot be written keeps no number and is adopted again by
    the rerun, which still sees the `check` label.
    """
    state, keep = adoption.study, adoption.keep
    renamed = keep is not None and keep.title != state.location
    in_review = (
        keep is not None
        and not state.released
        and state.status == "draft"
        and any(label.casefold() == "check" for label in keep.labels)
    )
    status = "in_review" if in_review else state.status
    duplicates = [
        duplicate.number
        for duplicate in adoption.duplicates
        if duplicate.state == "open"
    ]
    result = AdoptionResult(
        study=state.location,
        number=keep.number if keep else None,
        created=keep is None,
        renamed=renamed,
        duplicates=duplicates,
        in_review=in_review,
    )
    if run.dry_run:
        if keep is None:
            return result, None
        run.issues[keep.number] = replace(keep, title=state.location)
        return result, replace(state, issue=keep.number, status=status)
    if keep is None:
        issue = _create(run, state)
    elif renamed:
        issue = run.github.update_issue(keep.number, title=state.location)
    else:
        issue = keep
    for number in duplicates:
        run.github.comment(number, DUPLICATE.format(number=issue.number))
        run.github.update_issue(number, state="closed", state_reason="not_planned")
    review_revision = state.review_revision
    if in_review:
        review_revision = set_status(
            state.folder,
            author,
            "in_review",
            vocabulary=None,
            revision=state.review_revision,
        )
    written = patch_metadata(
        state.folder, {"issue": issue.number}, state.metadata_revision
    )
    run.issues[issue.number] = issue
    result.number = issue.number
    return result, replace(
        state,
        issue=issue.number,
        status=status,
        metadata_revision=written.revision,
        review_revision=review_revision,
    )


def _create(run: _Run, state: StudyState) -> Issue:
    """A new issue titled with the location, with its labels and assignees."""
    labels = [state.location.partition("/")[0], WORKFLOW[state.status]]
    for name in labels:
        _create_label(run, name)
    assignees = desired_assignees(
        state, run.roster, Problems(), repository=run.github.repository
    )
    issue = run.github.create_issue(state.location, labels=labels, assignees=assignees)
    _check_applied(run, state.location, issue, labels, assignees)
    return issue


def _create_label(run: _Run, name: str) -> None:
    """Create a label unless the repository has it, ignoring case."""
    if name.casefold() in {label.casefold() for label in run.label_names}:
        return
    run.github.create_label(name, LABEL_COLORS.get(name, SUBSTANCE_COLOR))
    run.label_names.append(name)


def _apply(run: _Run, changes: SyncPlan) -> int:
    """Create the missing labels, then change the issues; the number changed."""
    for name in changes.labels:
        try:
            _create_label(run, name)
        except GitHubError as error:
            run.fail(f"Label {name}", error)
    applied = 0
    for change in changes.changes:
        try:
            if change.reopen_first:
                run.github.update_issue(change.number, state="open")
            issue = run.github.update_issue(
                change.number,
                title=change.title,
                labels=change.labels,
                assignees=change.assignees,
                state=change.state,
                state_reason=change.state_reason,
            )
        except GitHubError as error:
            run.fail(change.study, error)
        else:
            applied += _check_applied(
                run, change.study, issue, change.labels, change.assignees
            )
    return applied


def _check_applied(
    run: _Run,
    where: str,
    issue: Issue,
    labels: list[str] | None,
    assignees: list[str] | None,
) -> bool:
    """Whether GitHub took the labels and assignees it was sent, ignoring case.

    GitHub drops both silently for a token without push access; that is an
    error of the study.
    """
    if _folded(issue.labels, labels) and _folded(issue.assignees, assignees):
        return True
    run.errors.append(
        f"{where}: GitHub did not apply the labels or assignees of "
        f"#{issue.number}; the token may lack write access"
    )
    return False


def _folded(current: tuple[str, ...], sent: list[str] | None) -> bool:
    """True when nothing was sent or GitHub has what was sent, ignoring case."""
    return sent is None or {name.casefold() for name in current} == {
        name.casefold() for name in sent
    }
