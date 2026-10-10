"""The GitHub issue of one study, for the lifecycle commands."""

from collections.abc import Set

from pkdb.issues.github import GitHub, GitHubError, Issue
from pkdb.issues.state import LABEL_COLORS, SUBSTANCE_COLOR, WORKFLOW


def issue_for_new_study(
    github: GitHub, location: str, claimed: Set[int] = frozenset()
) -> tuple[Issue, bool]:
    """The issue titled exactly `location`, or a new one; True when it was created.

    Issues in `claimed`, which other studies name, are never taken.

    Of several issues with the title an open one wins, then the lowest number.
    """
    matches = [
        issue
        for issue in github.issues()
        if issue.title == location and issue.number not in claimed
    ]
    if matches:
        best = min(matches, key=lambda issue: (issue.state != "open", issue.number))
        return best, False
    labels = [location.partition("/")[0], WORKFLOW["draft"]]
    known = {name.casefold() for name in github.labels()}
    for name in labels:
        if name.casefold() not in known:
            github.create_label(name, LABEL_COLORS.get(name, SUBSTANCE_COLOR))
            known.add(name.casefold())
    issue = github.create_issue(location, labels=labels, assignees=[])
    if {name.casefold() for name in issue.labels} != {n.casefold() for n in labels}:
        # GitHub drops labels silently for a token without push access.
        raise GitHubError(
            f"GitHub did not apply the labels of #{issue.number}; "
            "the token may lack write access"
        )
    return issue, True


def rename_issue(github: GitHub, number: int, location: str) -> Issue:
    """Give the issue the title `location`."""
    return github.update_issue(number, title=location)
