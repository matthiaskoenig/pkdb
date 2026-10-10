"""Give studies their GitHub issue and align the issues with the studies.

GitHub is written first and `study.json` last: an interrupted adoption leaves
no number on disk, and the rerun finds the renamed or created issue by its
exact title.
"""

from collections.abc import Callable, Set
from dataclasses import dataclass, field, replace
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from pkdb.identity import Author
from pkdb.issues.adopt import DUPLICATE, SIMILAR, SIMILAR_CREATED, Adoption, match
from pkdb.issues.github import GitHub, GitHubError, Issue
from pkdb.issues.state import (
    LABEL_COLORS,
    SUBSTANCE_COLOR,
    WORKFLOW,
    IssueChange,
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

INTERRUPTED = "Interrupted."


class AdoptionResult(BaseModel):
    """The issue a study without one got; `number` is None for a new issue in a dry run.

    `labels` and `assignees` are those of a new issue, which is titled with
    the study: the ones to send in a dry run, else the ones GitHub applied.
    """

    model_config = ConfigDict(extra="forbid")

    study: str
    number: int | None
    created: bool = False
    renamed: bool = False
    duplicates: list[int] = Field(default_factory=list)
    in_review: bool = False
    labels: list[str] = Field(default_factory=list)
    assignees: list[str] = Field(default_factory=list)


class SyncResult(BaseModel):
    """What a sync adopted, planned and changed, with its warnings and errors.

    `stopped` says why a run stopped early; the result then holds what was
    done until then.
    """

    model_config = ConfigDict(extra="forbid")

    repository: str
    dry_run: bool
    adopted: list[AdoptionResult] = Field(default_factory=list)
    plan: SyncPlan = Field(default_factory=SyncPlan)
    applied: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    format_1: int = 0
    stopped: str | None = None

    @property
    def ok(self) -> bool:
        return not self.errors and self.stopped is None


def sync(
    root: Path,
    github: GitHub,
    roster: list[Curator],
    *,
    adopt: bool = False,
    author: Author | None = None,
    dry_run: bool = False,
    progress: Callable[[str], None] | None = None,
) -> SyncResult:
    """Align the issue of every format 2 study; with `adopt`, give studies an issue.

    Adoption is the only part that writes files, `study.json` and `review.json`
    of the adopted studies. A dry run reads GitHub and writes nothing.
    `progress` gets one line for each adoption and each changed issue as soon
    as it is done.

    A GitHub failure that every following request would hit (the token, a
    permission, the rate limit, an unreachable GitHub), a failed read of the
    issues, labels or assignees, and Ctrl-C stop the run: the result holds
    what was done until then and names the reason in `stopped`. Any other
    GitHub failure is an error of its study, and the run goes on.
    """
    if adopt and author is None:
        raise ValueError("Adoption writes study.json and needs a PK-DB user")
    result = SyncResult(repository=github.repository, dry_run=dry_run)
    try:
        _sync(root, github, roster, result, author if adopt else None, progress)
    except GitHubError as error:
        result.stopped = str(error)
    except KeyboardInterrupt:
        result.stopped = INTERRUPTED
    return result


def _sync(
    root: Path,
    github: GitHub,
    roster: list[Curator],
    result: SyncResult,
    author: Author | None,
    progress: Callable[[str], None] | None,
) -> None:
    """Fill `result` step by step, so that a stopped run keeps what was done."""
    studies = read_studies(root)
    result.errors += studies.errors
    result.format_1 = studies.format_1
    run = _Run(
        github=github,
        result=result,
        issues={issue.number: issue for issue in github.issues()},
        roster=Roster.of(roster, github.assignable()),
        label_names=github.labels(),
        progress=progress,
    )
    states = studies.states
    if author is not None:
        states = _adopt(run, states, studies.claimed.keys(), author)
    result.plan = plan(
        states,
        list(run.issues.values()),
        run.roster,
        substance_names=substances(root),
        label_names=run.label_names,
        repository=github.repository,
        problems=run.problems,
        claimed=studies.claimed,
    )
    result.warnings += result.plan.warnings
    result.errors += result.plan.errors
    if not result.dry_run:
        _apply(run, result.plan)


@dataclass
class _Run:
    """The GitHub repository as the sync knows it, and the result so far.

    `problems` holds the user problems of new issues in a dry run, which the
    plan does not see; `dropped` the issues whose labels or assignees GitHub
    dropped, which are reported once; `created` the number of the issue
    created for a study, also when its adoption failed afterwards.
    """

    github: GitHub
    result: SyncResult
    issues: dict[int, Issue]
    roster: Roster
    label_names: list[str]
    progress: Callable[[str], None] | None
    problems: Problems = field(default_factory=Problems)
    dropped: set[int] = field(default_factory=set)
    created: dict[str, int] = field(default_factory=dict)

    @property
    def dry_run(self) -> bool:
        return self.result.dry_run

    def error(self, message: str) -> None:
        self.result.errors.append(message)

    def fail(self, where: str, error: GitHubError) -> None:
        """Record a failed GitHub request, or raise one that every request would hit."""
        if _stops(error):
            raise error
        self.error(f"{where}: {error}")

    def done(self, line: str) -> None:
        if self.progress is not None:
            self.progress(line)


def _adopt(
    run: _Run, states: list[StudyState], claimed: Set[int], author: Author
) -> list[StudyState]:
    """Give each study without issue one; the states to plan.

    The issues `claimed` by unreadable studies are left alone. A study whose
    adoption fails, or that gets a new issue in a dry run, is left out of the
    plan.
    """
    adoptions = {
        adoption.study.location: adoption
        for adoption in match(states, list(run.issues.values()), claimed)
    }
    planned: list[StudyState] = []
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
            run.error(
                f"{state.location}: {conflict.file} changed on disk; run the sync again"
            )
            continue
        except (MetadataError, ReviewError) as error:
            run.error(f"{state.location}: {error}")
            continue
        finally:
            run.result.warnings += _similar(adoption, run.created.get(state.location))
        run.result.adopted.append(result)
        if not run.dry_run:
            run.done(adoption_line(result, dry_run=False))
        if adopted_state is not None:
            planned.append(adopted_state)
    return planned


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
    if keep is None:
        # The plan repeats the problems of a new issue, except in a dry run.
        problems = run.problems if run.dry_run else Problems()
        result.labels = [state.location.partition("/")[0], WORKFLOW[state.status]]
        result.assignees = desired_assignees(
            state, run.roster, problems, repository=run.github.repository
        )
    if run.dry_run:
        if keep is None:
            return result, None
        run.issues[keep.number] = replace(keep, title=state.location)
        return result, replace(state, issue=keep.number, status=status)
    if keep is None:
        issue = _create(run, state, result.labels, result.assignees)
        result.labels, result.assignees = list(issue.labels), list(issue.assignees)
    elif renamed:
        issue = run.github.update_issue(keep.number, title=state.location)
    else:
        issue = keep
    for number in duplicates:
        # A rerun after a failed close finds the comment of the earlier run.
        comment = DUPLICATE.format(number=issue.number)
        if comment not in run.github.comments(number):
            run.github.comment(number, comment)
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


def _create(
    run: _Run, state: StudyState, labels: list[str], assignees: list[str]
) -> Issue:
    """A new issue titled with the location, with its labels and assignees."""
    for name in labels:
        _create_label(run, name)
    issue = run.github.create_issue(state.location, labels=labels, assignees=assignees)
    run.created[state.location] = issue.number
    _check_applied(run, state.location, issue, labels, assignees)
    return issue


def _create_label(run: _Run, name: str) -> None:
    """Create a label unless the repository has it, ignoring case."""
    if name.casefold() in {label.casefold() for label in run.label_names}:
        return
    run.github.create_label(name, LABEL_COLORS.get(name, SUBSTANCE_COLOR))
    run.label_names.append(name)


def _similar(adoption: Adoption, created: int | None) -> list[str]:
    """The warnings about issues with a title similar to the study's.

    They ask to rename the issue unless a new issue was created for the study,
    also one whose adoption failed afterwards; then they name both issues.
    """
    location = adoption.study.location
    if created is None:
        return [
            SIMILAR.format(location=location, number=issue.number, title=issue.title)
            for issue in adoption.similar
        ]
    return [
        SIMILAR_CREATED.format(
            location=location,
            created=created,
            number=issue.number,
            title=issue.title,
        )
        for issue in adoption.similar
    ]


def _apply(run: _Run, changes: SyncPlan) -> None:
    """Create the missing labels, then change the issues."""
    for name in changes.labels:
        try:
            _create_label(run, name)
        except GitHubError as error:
            run.fail(f"Label {name}", error)
    for change in changes.changes:
        try:
            issue = _change(run, change)
        except GitHubError as error:
            run.fail(change.study, error)
            continue
        if issue is None:
            continue
        if _check_applied(run, change.study, issue, change.labels, change.assignees):
            run.result.applied += 1
            run.done(change_line(change))


def _change(run: _Run, change: IssueChange) -> Issue | None:
    """Write the change of one issue; None when it was not closed as completed.

    An issue closed with another reason than completed is reopened with the
    other changes and then closed as completed. When that close fails, the
    issue is closed again with its former reason, and the error of the study
    names the state that GitHub then reports for the issue. A run that stops
    or is interrupted on the way names the issue as possibly left open.
    """
    if not change.reopen_first:
        return run.github.update_issue(
            change.number,
            title=change.title,
            labels=change.labels,
            assignees=change.assignees,
            state=change.state,
            state_reason=change.state_reason,
        )
    # The plan reopens only an issue closed with another reason than completed.
    reason = run.issues[change.number].state_reason
    assert reason is not None
    try:
        run.github.update_issue(
            change.number,
            title=change.title,
            labels=change.labels,
            assignees=change.assignees,
            state="open",
        )
    except KeyboardInterrupt:
        run.error(_not_closed(change, None, None))
        raise
    refused: GitHubError | None = None
    try:
        try:
            return run.github.update_issue(
                change.number, state="closed", state_reason="completed"
            )
        except GitHubError as error:
            if _stops(error):
                raise
            refused = error
        try:
            # GitHub keeps the reason of a close it applied despite the error.
            run.github.update_issue(change.number, state="closed", state_reason=reason)
        except GitHubError as error:
            if _stops(error):
                raise
        issue = run.github.issue(change.number)
    except KeyboardInterrupt:
        run.error(_not_closed(change, refused, None))
        raise
    except GitHubError as error:
        run.error(_not_closed(change, refused, None))
        if _stops(error):
            raise
        return None
    run.error(_not_closed(change, refused, issue))
    return None


def _not_closed(
    change: IssueChange, refused: GitHubError | None, issue: Issue | None
) -> str:
    """The error of a reopened issue that was not closed as completed.

    `refused` is the failed close, None when the run stopped on it; `issue`
    the issue as GitHub reports it afterwards, None when that is unknown.
    """
    number = change.number
    if issue is None:
        state = f"#{number} was reopened and may be left open"
    elif issue.state == "open":
        state = f"#{number} was reopened and is left open"
    elif issue.state_reason is None:
        state = f"#{number} is closed"
    else:
        state = f"#{number} is closed as {issue.state_reason.replace('_', ' ')}"
    if refused is None:
        return f"{change.study}: {state}"
    return f"{change.study}: {refused}; {state}"


def _stops(error: GitHubError) -> bool:
    """Whether every following request would hit the failure, so the run stops."""
    return error.rate_limited or error.unreachable or error.status_code in (401, 403)


def _check_applied(
    run: _Run,
    where: str,
    issue: Issue,
    labels: list[str] | None,
    assignees: list[str] | None,
) -> bool:
    """Whether GitHub took the labels and assignees it was sent, ignoring case.

    GitHub drops both silently for a token without push access; that is an
    error of the study, reported once for an issue that is written again, such
    as a new issue that the plan changes.
    """
    if _folded(issue.labels, labels) and _folded(issue.assignees, assignees):
        return True
    if issue.number not in run.dropped:
        run.dropped.add(issue.number)
        run.error(
            f"{where}: GitHub did not apply the labels or assignees of "
            f"#{issue.number}; the token may lack write access"
        )
    return False


def _folded(current: tuple[str, ...], sent: list[str] | None) -> bool:
    """True when nothing was sent or GitHub has what was sent, ignoring case."""
    return sent is None or {name.casefold() for name in current} == {
        name.casefold() for name in sent
    }


def adoption_line(item: AdoptionResult, *, dry_run: bool) -> str:
    """One line about an adoption: what a dry run would do, or what was done."""
    adopt, rename, close = (
        ("adopt", "rename", "close") if dry_run else ("adopted", "renamed", "closed")
    )
    if item.created:
        new = "new issue" if item.number is None else f"created #{item.number}"
        labels, assignees = " ".join(item.labels), " ".join(item.assignees)
        parts = [
            f"{new} titled {item.study}",
            f"labels {labels}" if labels else "no labels",
            f"assignees {assignees}" if assignees else "no assignees",
        ]
    else:
        parts = [f"{adopt} #{item.number}"]
        if item.renamed:
            parts.append(rename)
        parts += [f"{close} #{number} as duplicate" for number in item.duplicates]
        if item.in_review:
            parts.append("set review status in_review")
    return f"{item.study}: {', '.join(parts)}"


def change_line(change: IssueChange) -> str:
    """One line about the change of an issue."""
    parts = []
    if change.title is not None:
        parts.append("title")
    if change.add_labels or change.remove_labels:
        labels = [f"+{name}" for name in change.add_labels]
        labels += [f"-{name}" for name in change.remove_labels]
        parts.append(f"labels {' '.join(labels)}")
    if change.assignees is not None:
        parts.append(
            f"assignees {' '.join(change.assignees)}"
            if change.assignees
            else "no assignees"
        )
    if change.reopen_first:
        parts.append("reopen and close as completed")
    elif change.state is not None:
        parts.append("close" if change.state == "closed" else "reopen")
    return f"#{change.number} {change.study}: {', '.join(parts)}"
