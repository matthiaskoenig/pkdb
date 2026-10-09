"""Match studies without an issue to existing GitHub issues by title."""

from dataclasses import dataclass

from pkdb.issues.github import Issue
from pkdb.issues.state import StudyState

PREFIXES = ("Curate ", "Check ", "Check and curate ")
DUPLICATE = "Duplicate of #{number}"


@dataclass(frozen=True)
class Adoption:
    study: StudyState
    keep: Issue | None
    duplicates: tuple[Issue, ...]


def _exact(title: str, location: str) -> bool | None:
    """True for the canonical title, False for a known prefix, None otherwise."""
    if title == location:
        return True
    if any(title == prefix + location for prefix in PREFIXES):
        return False
    return None


def match(states: list[StudyState], issues: list[Issue]) -> list[Adoption]:
    claimed = {state.issue for state in states if state.issue is not None}
    adoptions = []
    for state in states:
        if state.issue is not None:
            continue
        candidates = []
        for issue in issues:
            exact = _exact(issue.title, state.location)
            if exact is not None and issue.number not in claimed:
                candidates.append(
                    (not exact, issue.state != "open", issue.number, issue)
                )
        candidates.sort(key=lambda candidate: candidate[:3])
        found = [candidate[3] for candidate in candidates]
        adoptions.append(Adoption(state, found[0] if found else None, tuple(found[1:])))
    return adoptions
