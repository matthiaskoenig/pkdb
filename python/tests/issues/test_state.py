from issue_fixtures import issue, study

from pkdb.issues.state import Roster, plan, read_studies
from pkdb.schemas.curators import Curator

REPOSITORY = "owner/data"
ROSTER = Roster.of(
    [
        Curator(username="ana", name="Ana", github="ana-gh"),
        Curator(username="bo", name="Bo", github="bo-gh"),
    ],
    {"ana-gh", "bo-gh"},
)


def run(
    root, issues, roster=ROSTER, labels=("curate", "check", "approved", "caffeine")
):
    studies = read_studies(root)
    return plan(
        studies.states,
        issues,
        roster,
        substance_names=["caffeine", "codeine"],
        label_names=list(labels),
        repository=REPOSITORY,
    )


def test_a_matching_issue_needs_no_change(tmp_path):
    study(tmp_path, "caffeine/A", issue=1)
    result = run(
        tmp_path,
        [issue(1, "caffeine/A", labels=["caffeine", "curate"], assignees=["ana-gh"])],
    )
    assert result.changes == [] and result.errors == [] and result.warnings == []
    assert result.labels == []


def test_labels_and_assignees_are_compared_case_insensitively(tmp_path):
    study(tmp_path, "caffeine/A", issue=1, curators=("ana", "bo"))
    roster = Roster.of(
        [
            Curator(username="ana", name="Ana", github="Ana-GH"),
            Curator(username="bo", name="Bo", github="bo-gh"),
        ],
        {"ana-gh", "Bo-Gh"},
    )
    current = issue(
        1, "caffeine/A", labels=["Caffeine", "CURATE"], assignees=["ANA-gh", "bo-GH"]
    )
    result = run(tmp_path, [current], roster)
    assert result.changes == [] and result.warnings == []


def test_title_labels_assignees_and_state_are_aligned(tmp_path):
    study(
        tmp_path,
        "caffeine/A",
        issue=1,
        status="approved",
        reviewers=["bo"],
        release={"pkdb_id": "PKDB00001", "date": "2026-10-01"},
    )
    current = issue(
        1,
        "Curate caffeine/A",
        labels=["curate", "Codeine", "help wanted"],
        assignees=["zed"],
    )
    [change] = run(tmp_path, [current]).changes
    assert change.study == "caffeine/A" and change.number == 1
    assert change.title == "caffeine/A"
    assert change.labels == ["help wanted", "caffeine", "approved"]
    assert change.add_labels == ["caffeine", "approved"]
    assert change.remove_labels == ["curate", "Codeine"]
    assert change.assignees == ["ana-gh", "bo-gh"]
    assert (change.state, change.state_reason) == ("closed", "completed")


def test_a_released_study_closed_as_not_planned_is_closed_as_completed(tmp_path):
    study(
        tmp_path,
        "caffeine/A",
        issue=1,
        status="approved",
        reviewers=["ana"],
        release={"pkdb_id": "PKDB00001", "date": "2026-10-01"},
    )
    current = issue(
        1,
        "caffeine/A",
        state="closed",
        reason="not_planned",
        labels=["caffeine", "approved"],
        assignees=["ana-gh"],
    )
    [change] = run(tmp_path, [current]).changes
    assert change.model_dump(exclude_defaults=True) == {
        "study": "caffeine/A",
        "number": 1,
        "state": "closed",
        "state_reason": "completed",
    }


def test_an_approved_study_without_release_stays_open(tmp_path):
    study(tmp_path, "caffeine/A", issue=1, status="approved", reviewers=["ana"])
    current = issue(
        1, "caffeine/A", labels=["caffeine", "approved"], assignees=["ana-gh"]
    )
    assert run(tmp_path, [current]).changes == []


def test_a_closed_issue_of_an_unreleased_study_is_reopened(tmp_path):
    study(tmp_path, "caffeine/A", issue=1, status="in_review")
    current = issue(
        1,
        "caffeine/A",
        state="closed",
        reason="completed",
        labels=["caffeine", "check"],
        assignees=["ana-gh"],
    )
    [change] = run(tmp_path, [current]).changes
    assert (change.state, change.state_reason) == ("open", "reopened")
    assert change.title is None and change.labels is None and change.assignees is None


def test_two_studies_with_one_issue_are_errors_and_untouched(tmp_path):
    study(tmp_path, "caffeine/A", issue=1)
    study(tmp_path, "caffeine/B", issue=1)
    study(tmp_path, "caffeine/C", issue=2)
    result = run(tmp_path, [issue(1, "x"), issue(2, "x")])
    assert result.errors == [
        "Issue #1 is named by several studies: caffeine/A, caffeine/B"
    ]
    assert [change.study for change in result.changes] == ["caffeine/C"]


def test_missing_issues_and_studies_without_issue(tmp_path):
    study(tmp_path, "caffeine/A", issue=9)
    study(tmp_path, "caffeine/B")
    result = run(tmp_path, [])
    assert result.errors == [
        "caffeine/A names issue #9, which is not an issue of owner/data"
    ]
    assert result.warnings == [
        "caffeine/B has no issue; pkdb issues sync --adopt gives it one"
    ]
    assert result.changes == []


def test_unassignable_users_are_warnings(tmp_path):
    users = ("ana", "bo", "cy", "dee", *(f"u{i}" for i in range(10)))
    study(tmp_path, "caffeine/A", issue=1, curators=users)
    curators = [
        Curator(username="ana", name="Ana", github="ana-gh"),
        Curator(username="bo", name="Bo", github="bo-gh"),
        Curator(username="cy", name="Cy"),
    ]
    curators += [
        Curator(username=f"u{i}", name=f"U{i}", github=f"u{i}-gh") for i in range(10)
    ]
    roster = Roster.of(curators, {"ana-gh", *(f"u{i}-gh" for i in range(10))})
    [change] = run(
        tmp_path, [issue(1, "caffeine/A", labels=["caffeine", "curate"])], roster
    ).changes
    assert change.assignees == sorted(["ana-gh", *(f"u{i}-gh" for i in range(9))])
    assert sorted(run(tmp_path, [issue(1, "caffeine/A")], roster).warnings) == [
        "GitHub user bo-gh cannot be assigned in owner/data (1 study)",
        "User cy has no GitHub login in the PK-DB roster (1 study)",
        "User dee is not in the PK-DB roster (1 study)",
        "caffeine/A has 11 assignees; GitHub assigns at most 10",
    ]


def test_a_user_problem_is_counted_once_per_study(tmp_path):
    study(tmp_path, "caffeine/A", issue=1, curators=("ana", "dee"), reviewers=("dee",))
    study(tmp_path, "caffeine/B", issue=2, curators=("dee", "eve", "fay"))
    roster = Roster.of(
        [
            Curator(username="ana", name="Ana", github="ana-gh"),
            Curator(username="eve", name="Eve", github="shared-gh"),
            Curator(username="fay", name="Fay", github="Shared-GH"),
        ],
        {"ana-gh"},
    )
    result = run(tmp_path, [issue(1, "caffeine/A"), issue(2, "caffeine/B")], roster)
    assert result.warnings == [
        "GitHub user shared-gh cannot be assigned in owner/data (1 study)",
        "User dee is not in the PK-DB roster (2 studies)",
    ]


def test_missing_labels_are_created(tmp_path):
    study(tmp_path, "codeine/A", issue=1, status="in_review")
    study(tmp_path, "codeine/B", issue=2, status="in_review")
    result = run(
        tmp_path, [issue(1, "codeine/A"), issue(2, "codeine/B")], labels=["CHECK"]
    )
    assert result.labels == ["codeine"]


def test_unreadable_studies_are_errors_and_format_1_is_counted(tmp_path):
    folder = study(tmp_path, "caffeine/A", issue=1)
    (folder / "review.json").write_text("{", encoding="utf-8")
    v1 = tmp_path / "studies" / "caffeine" / "Old"
    v1.mkdir()
    (v1 / "study.json").write_text('{"sid": "1", "name": "Old"}', encoding="utf-8")
    (tmp_path / "studies" / "caffeine" / "Empty").mkdir()
    studies = read_studies(tmp_path)
    assert studies.states == [] and studies.format_1 == 1
    assert len(studies.errors) == 1 and studies.errors[0].startswith("caffeine/A: ")


def test_a_study_is_read_with_its_users_and_revisions(tmp_path):
    folder = study(
        tmp_path,
        "caffeine/A",
        issue=3,
        status="approved",
        curators=("ana", "bo"),
        reviewers=("bo", "cy"),
        release={"pkdb_id": "PKDB00001", "date": "2026-10-01"},
    )
    [state] = read_studies(tmp_path).states
    assert (state.location, state.folder, state.issue) == ("caffeine/A", folder, 3)
    assert (state.status, state.released) == ("approved", True)
    assert state.users == ("ana", "bo", "cy")
    assert state.metadata_revision and state.review_revision
