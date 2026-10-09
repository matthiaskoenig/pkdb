from pathlib import Path

from issue_fixtures import issue

from pkdb.issues.adopt import match
from pkdb.issues.state import StudyState


def state(location, number=None):
    return StudyState(
        location, Path(location), number, "draft", False, ("ana",), "r1", "r2"
    )


def test_the_exact_open_lowest_issue_is_kept():
    issues = [
        issue(5, "Curate caffeine/A"),
        issue(7, "caffeine/A", state="closed", reason="completed"),
        issue(9, "caffeine/A"),
        issue(3, "Check and curate caffeine/A"),
        issue(4, "Check caffeine/AB"),
    ]
    [adoption] = match([state("caffeine/A")], issues)
    assert adoption.keep is not None and adoption.keep.number == 9
    assert [i.number for i in adoption.duplicates] == [7, 3, 5]


def test_issues_named_by_a_study_are_never_adopted():
    issues = [issue(1, "caffeine/A"), issue(2, "Curate caffeine/A")]
    [adoption] = match([state("caffeine/A"), state("caffeine/B", number=1)], issues)
    assert adoption.keep is not None and adoption.keep.number == 2
    assert adoption.duplicates == ()


def test_a_study_without_candidates_gets_a_new_issue():
    [adoption] = match(
        [state("caffeine/A")], [issue(1, "caffeine/AB"), issue(2, "Curate: caffeine/A")]
    )
    assert adoption.keep is None and adoption.duplicates == ()
