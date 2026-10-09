"""Match studies without an issue to existing GitHub issues by title."""

from collections.abc import Set
from dataclasses import dataclass

from pkdb.issues.github import Issue
from pkdb.issues.state import StudyState

PREFIXES = ("Curate ", "Check ", "Check and curate ")
DUPLICATE = "Duplicate of #{number}"
SIMILAR = (
    "{location}: issue #{number} has a similar title ({title}); rename it to adopt it"
)


@dataclass(frozen=True)
class Adoption:
    """The issue to keep for a study, the further matches, and near misses.

    `similar` lists, for a study without a match, the issues whose title
    matches only after ignoring case and repeated spaces.
    """

    study: StudyState
    keep: Issue | None
    duplicates: tuple[Issue, ...]
    similar: tuple[Issue, ...] = ()


def _exact(title: str, location: str) -> bool | None:
    """True for the canonical title, False for a known prefix, None otherwise."""
    if title == location:
        return True
    if any(title == prefix + location for prefix in PREFIXES):
        return False
    return None


def _normal(title: str) -> str:
    """A title in lower case with single spaces."""
    return " ".join(title.split()).casefold()


def _similar(title: str, location: str) -> bool:
    """Whether a title is the location, with or without a prefix, but for case and spaces."""
    return _normal(title) in {_normal(prefix + location) for prefix in ("", *PREFIXES)}


def match(
    states: list[StudyState], issues: list[Issue], claimed: Set[int] = frozenset()
) -> list[Adoption]:
    """The adoption of each study without issue.

    Issues named by a study, or `claimed` by a study that cannot be read, are
    never adopted. Of the exact matches, the canonical title wins over a
    prefixed one, then an open issue over a closed one, then the lowest number.
    """
    claimed = {state.issue for state in states if state.issue is not None} | claimed
    free = [issue for issue in issues if issue.number not in claimed]
    found: dict[str, list[Issue]] = {}
    for state in states:
        if state.issue is not None:
            continue
        candidates = []
        for issue in free:
            if (exact := _exact(issue.title, state.location)) is not None:
                candidates.append(
                    (not exact, issue.state != "open", issue.number, issue)
                )
        candidates.sort(key=lambda candidate: candidate[:3])
        found[state.location] = [candidate[3] for candidate in candidates]
    matched = {issue.number for issues in found.values() for issue in issues}
    adoptions = []
    for state in states:
        if (issues_found := found.get(state.location)) is None:
            continue
        similar = ()
        if not issues_found:
            similar = tuple(
                issue
                for issue in free
                if issue.number not in matched and _similar(issue.title, state.location)
            )
        keep = issues_found[0] if issues_found else None
        adoptions.append(Adoption(state, keep, tuple(issues_found[1:]), similar))
    return adoptions
