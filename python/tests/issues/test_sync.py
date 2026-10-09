import httpx2
import pytest
from fake_github import FakeGitHub
from issue_fixtures import study

from pkdb.identity import Author
from pkdb.issues import state as state_module
from pkdb.issues.sync import AdoptionResult, sync
from pkdb.schemas.curators import Curator
from pkdb.studyformat.metadata import read_metadata
from pkdb.studyformat.review_edit import read_review

ROSTER = [Curator(username="ana", name="Ana", github="ana-gh")]
AUTHOR = Author("mkoenig")
RELEASE = {"pkdb_id": "PKDB00001", "date": "2026-10-01"}


def number_of(folder):
    return read_metadata(folder).metadata.issue


def status_of(folder):
    return read_review(folder).review.status


def edit(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


def edit_after_reading(monkeypatch, path, old, new):
    """Change a study file right after the sync has read the studies."""

    def read_then_edit(root):
        studies = state_module.read_studies(root)
        edit(path, old, new)
        return studies

    monkeypatch.setattr("pkdb.issues.sync.read_studies", read_then_edit)


def test_sync_aligns_issues(tmp_path):
    study(tmp_path, "caffeine/A", issue=1, status="in_review")
    github = FakeGitHub(
        issues=[{"number": 1, "title": "Check caffeine/A", "labels": ["curate"]}],
        assignable=["ana-gh"],
    )
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER)
    assert result.ok and result.applied == 1
    assert github.issues[1]["title"] == "caffeine/A"
    assert sorted(github.issues[1]["labels"]) == ["caffeine", "check"]
    assert github.issues[1]["assignees"] == ["ana-gh"]
    assert sorted(github.labels) == ["caffeine", "check"]
    with github.client() as client:
        again = sync(tmp_path, client, ROSTER)
    assert again.ok and again.plan.changes == [] and again.applied == 0


def test_a_dry_run_changes_nothing(tmp_path):
    study(tmp_path, "caffeine/A", issue=1)
    github = FakeGitHub(issues=[{"number": 1, "title": "x"}])
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER, dry_run=True)
    assert result.plan.changes and github.writes == []
    assert result.dry_run and result.applied == 0


def test_sync_exits_with_errors_and_changes_the_rest(tmp_path):
    study(tmp_path, "caffeine/A", issue=1)
    study(tmp_path, "caffeine/B", issue=1)
    study(tmp_path, "caffeine/C", issue=2)
    github = FakeGitHub(
        issues=[{"number": 1, "title": "x"}, {"number": 2, "title": "y"}],
        assignable=["ana-gh"],
    )
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER)
    assert not result.ok and result.applied == 1
    assert github.issues[1]["title"] == "x"
    assert github.issues[2]["title"] == "caffeine/C"


def test_unreadable_studies_are_errors_and_format_1_is_counted(tmp_path):
    folder = study(tmp_path, "caffeine/A", issue=1)
    (folder / "review.json").write_text("{", encoding="utf-8")
    legacy = tmp_path / "studies" / "caffeine" / "Old"
    legacy.mkdir()
    (legacy / "study.json").write_text('{"sid": "1", "name": "Old"}', encoding="utf-8")
    github = FakeGitHub(issues=[{"number": 1, "title": "x"}])
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER)
    assert [error.partition(":")[0] for error in result.errors] == ["caffeine/A"]
    assert result.format_1 == 1 and github.writes == []


def test_adoption_needs_an_author(tmp_path):
    study(tmp_path, "caffeine/A")
    github = FakeGitHub()
    with github.client() as client, pytest.raises(ValueError):
        sync(tmp_path, client, ROSTER, adopt=True)


def test_adoption_renames_closes_duplicates_and_records_the_number(tmp_path):
    folder = study(tmp_path, "caffeine/A")
    github = FakeGitHub(
        issues=[
            {"number": 4, "title": "Check caffeine/A", "labels": ["check"]},
            {"number": 6, "title": "Curate caffeine/A"},
        ],
        assignable=["ana-gh"],
    )
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert result.ok
    assert result.adopted == [
        AdoptionResult(
            study="caffeine/A", number=4, renamed=True, duplicates=[6], in_review=True
        )
    ]
    assert number_of(folder) == 4
    assert status_of(folder) == "in_review"
    assert github.issues[4]["title"] == "caffeine/A"
    assert "check" in github.issues[4]["labels"]
    assert (github.issues[6]["state"], github.issues[6]["state_reason"]) == (
        "closed",
        "not_planned",
    )
    assert github.comments == [(6, "Duplicate of #4")]
    with github.client() as client:
        again = sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert again.ok and again.adopted == [] and again.plan.changes == []


def test_adoption_creates_an_issue_without_a_match(tmp_path):
    folder = study(tmp_path, "caffeine/A")
    github = FakeGitHub(assignable=["ana-gh"])
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert result.ok and result.applied == 0
    assert result.adopted == [
        AdoptionResult(study="caffeine/A", number=1, created=True)
    ]
    assert number_of(folder) == 1
    assert github.issues[1]["title"] == "caffeine/A"
    assert sorted(github.issues[1]["labels"]) == ["caffeine", "curate"]
    assert github.issues[1]["assignees"] == ["ana-gh"]
    assert [path for _, path, _ in github.writes] == ["/labels", "/labels", "/issues"]


def test_only_open_duplicates_are_closed(tmp_path):
    folder = study(tmp_path, "caffeine/A")
    github = FakeGitHub(
        issues=[
            {"number": 4, "title": "caffeine/A"},
            {
                "number": 6,
                "title": "Curate caffeine/A",
                "state": "closed",
                "state_reason": "not_planned",
            },
            {
                "number": 7,
                "title": "Check caffeine/A",
                "state": "closed",
                "state_reason": "completed",
            },
            {"number": 8, "title": "Check and curate caffeine/A"},
        ],
        assignable=["ana-gh"],
    )
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert result.adopted == [
        AdoptionResult(study="caffeine/A", number=4, duplicates=[8])
    ]
    assert number_of(folder) == 4
    assert github.comments == [(8, "Duplicate of #4")]
    assert (github.issues[8]["state"], github.issues[8]["state_reason"]) == (
        "closed",
        "not_planned",
    )
    assert github.issues[7]["state_reason"] == "completed"
    assert all(path not in ("/issues/6", "/issues/7") for _, path, _ in github.writes)


def test_sync_converges_on_legacy_closed_issues(tmp_path):
    study(
        tmp_path,
        "caffeine/A",
        issue=1,
        status="approved",
        reviewers=["ana"],
        release=RELEASE,
    )
    study(
        tmp_path,
        "caffeine/B",
        issue=2,
        status="approved",
        reviewers=["ana"],
        release=RELEASE,
    )
    study(tmp_path, "caffeine/C", issue=3)
    study(tmp_path, "caffeine/D", issue=4)
    study(
        tmp_path,
        "caffeine/E",
        issue=5,
        status="approved",
        reviewers=["ana"],
        release=RELEASE,
    )
    closed = {"state": "closed", "labels": ["caffeine"], "assignees": ["ana-gh"]}
    github = FakeGitHub(
        issues=[
            {"number": 1, "title": "caffeine/A", **closed, "state_reason": None},
            {
                "number": 2,
                "title": "caffeine/B",
                **closed,
                "state_reason": "not_planned",
            },
            {"number": 3, "title": "caffeine/C", **closed, "state_reason": "completed"},
            {
                "number": 4,
                "title": "caffeine/D",
                "labels": ["curate"],
                "assignees": ["zed"],
            },
            {"number": 5, "title": "Curate caffeine/E"},
        ],
        labels=["caffeine", "curate", "approved"],
        assignable=["ana-gh", "zed"],
    )
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER)
    assert result.ok and result.applied == 5
    states = {n: (i["state"], i["state_reason"]) for n, i in github.issues.items()}
    assert states == {
        1: ("closed", None),
        2: ("closed", "completed"),
        3: ("open", "reopened"),
        4: ("open", None),
        5: ("closed", "completed"),
    }
    assert [body for _, path, body in github.writes if path == "/issues/2"] == [
        {"state": "open"},
        {
            "labels": ["caffeine", "approved"],
            "state": "closed",
            "state_reason": "completed",
        },
    ]
    with github.client() as client:
        again = sync(tmp_path, client, ROSTER)
    assert again.ok and again.plan.changes == [] and again.applied == 0


def test_labels_and_assignees_github_drops_are_errors(tmp_path):
    study(tmp_path, "caffeine/A", issue=1)
    github = FakeGitHub(
        issues=[{"number": 1, "title": "caffeine/A"}],
        labels=["caffeine", "curate"],
        assignable=["ana-gh"],
        push_access=False,
    )
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER)
    assert result.errors == [
        "caffeine/A: GitHub did not apply the labels or assignees of #1; "
        "the token may lack write access"
    ]
    assert result.applied == 0


def test_a_new_issue_without_its_labels_and_assignees_is_an_error(tmp_path):
    folder = study(tmp_path, "caffeine/A")
    github = FakeGitHub(
        labels=["caffeine", "curate"], assignable=["ana-gh"], push_access=False
    )
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert result.errors[0] == (
        "caffeine/A: GitHub did not apply the labels or assignees of #1; "
        "the token may lack write access"
    )
    assert number_of(folder) == 1


@pytest.mark.parametrize(
    ("status", "release", "labels", "expected"),
    [
        ("draft", None, ["Check"], "in_review"),
        ("draft", None, ["curate"], "draft"),
        ("draft", RELEASE, ["check"], "draft"),
        ("approved", None, ["check"], "approved"),
    ],
)
def test_only_an_unreleased_draft_with_a_check_label_goes_in_review(
    tmp_path, status, release, labels, expected
):
    folder = study(
        tmp_path, "caffeine/A", status=status, reviewers=["ana"], release=release
    )
    github = FakeGitHub(
        issues=[{"number": 4, "title": "Curate caffeine/A", "labels": labels}],
        assignable=["ana-gh"],
    )
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert result.ok and result.adopted[0].in_review == (expected != status)
    assert status_of(folder) == expected and number_of(folder) == 4


def test_a_dry_run_adoption_shows_what_would_happen_and_writes_nothing(tmp_path):
    folders = [study(tmp_path, "caffeine/A"), study(tmp_path, "caffeine/B")]
    files = [
        folder / name for folder in folders for name in ("study.json", "review.json")
    ]
    before = [path.read_bytes() for path in files]
    github = FakeGitHub(
        issues=[
            {"number": 4, "title": "Check caffeine/A", "labels": ["check"]},
            {"number": 6, "title": "Curate caffeine/A"},
        ],
        labels=["check"],
        assignable=["ana-gh"],
    )
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR, dry_run=True)
    assert result.ok and result.warnings == []
    assert result.adopted == [
        AdoptionResult(
            study="caffeine/A", number=4, renamed=True, duplicates=[6], in_review=True
        ),
        AdoptionResult(study="caffeine/B", number=None, created=True),
    ]
    changes = [
        (change.number, change.title, change.add_labels, change.assignees)
        for change in result.plan.changes
    ]
    assert changes == [(4, None, ["caffeine"], ["ana-gh"])]
    assert github.writes == []
    assert [path.read_bytes() for path in files] == before


def test_an_interrupted_adoption_is_finished_by_the_rerun(tmp_path, monkeypatch):
    folder = study(tmp_path, "caffeine/A")
    github = FakeGitHub(
        issues=[{"number": 4, "title": "Curate caffeine/A"}], assignable=["ana-gh"]
    )

    def stop(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("pkdb.issues.sync.patch_metadata", stop)
    with github.client() as client:
        stopped = sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert stopped.stopped == "Interrupted." and not stopped.ok
    assert github.issues[4]["title"] == "caffeine/A" and number_of(folder) is None
    monkeypatch.undo()
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert result.ok and number_of(folder) == 4 and len(github.issues) == 1


def test_an_interrupted_creation_is_adopted_without_a_second_issue(
    tmp_path, monkeypatch
):
    folder = study(tmp_path, "caffeine/A")
    github = FakeGitHub(assignable=["ana-gh"])

    def stop(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("pkdb.issues.sync.patch_metadata", stop)
    with github.client() as client:
        stopped = sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert stopped.stopped == "Interrupted." and number_of(folder) is None
    monkeypatch.undo()
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert result.ok and result.adopted == [
        AdoptionResult(study="caffeine/A", number=1)
    ]
    assert number_of(folder) == 1
    assert [path for method, path, _ in github.writes if method == "POST"].count(
        "/issues"
    ) == 1


def test_an_interruption_keeps_what_was_done(tmp_path):
    first = study(tmp_path, "caffeine/A")
    second = study(tmp_path, "caffeine/B")
    github = FakeGitHub(
        issues=[
            {"number": 4, "title": "Curate caffeine/A"},
            {"number": 5, "title": "caffeine/B"},
        ],
        assignable=["ana-gh"],
    )
    lines = []

    def progress(line):
        lines.append(line)
        raise KeyboardInterrupt

    with github.client() as client:
        result = sync(
            tmp_path, client, ROSTER, adopt=True, author=AUTHOR, progress=progress
        )
    assert result.stopped == "Interrupted."
    assert result.adopted == [
        AdoptionResult(study="caffeine/A", number=4, renamed=True)
    ]
    assert lines == ["caffeine/A: adopted #4, renamed"]
    assert number_of(first) == 4 and number_of(second) is None


def test_progress_names_each_adoption_and_change(tmp_path):
    study(tmp_path, "caffeine/A", issue=1)
    study(tmp_path, "caffeine/B")
    github = FakeGitHub(
        issues=[
            {"number": 1, "title": "Curate caffeine/A"},
            {"number": 2, "title": "Check caffeine/B", "labels": ["check"]},
            {"number": 3, "title": "caffeine/B"},
        ],
        labels=["caffeine", "curate", "check"],
        assignable=["ana-gh"],
    )
    lines = []
    with github.client() as client:
        result = sync(
            tmp_path, client, ROSTER, adopt=True, author=AUTHOR, progress=lines.append
        )
    assert result.ok and result.applied == 2
    assert lines == [
        "caffeine/B: adopted #3, closed #2 as duplicate",
        "#1 caffeine/A: title, labels +caffeine +curate, assignees ana-gh",
        "#3 caffeine/B: labels +caffeine +curate, assignees ana-gh",
    ]


def test_a_changed_study_json_is_not_written_over(tmp_path, monkeypatch):
    first = study(tmp_path, "caffeine/A")
    second = study(tmp_path, "caffeine/B")
    github = FakeGitHub(
        issues=[
            {"number": 4, "title": "caffeine/A"},
            {"number": 5, "title": "caffeine/B"},
        ],
        assignable=["ana-gh"],
    )
    edit_after_reading(
        monkeypatch, first / "study.json", '"licence": "open"', '"licence": "closed"'
    )
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert result.errors == [
        "caffeine/A: study.json changed on disk; run the sync again"
    ]
    assert '"licence": "closed"' in (first / "study.json").read_text(encoding="utf-8")
    assert number_of(first) is None and number_of(second) == 5
    assert [change.study for change in result.plan.changes] == ["caffeine/B"]


def test_a_changed_review_json_leaves_the_adoption_to_the_rerun(tmp_path, monkeypatch):
    folder = study(tmp_path, "caffeine/A")
    github = FakeGitHub(
        issues=[{"number": 4, "title": "Check caffeine/A", "labels": ["check"]}],
        assignable=["ana-gh"],
    )
    edit_after_reading(
        monkeypatch, folder / "review.json", '"reviewers": []', '"reviewers": ["ana"]'
    )
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert result.errors == [
        "caffeine/A: review.json changed on disk; run the sync again"
    ]
    assert number_of(folder) is None and status_of(folder) == "draft"
    assert github.issues[4]["labels"] == ["check"]
    monkeypatch.undo()
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert result.ok and number_of(folder) == 4 and status_of(folder) == "in_review"
    assert sorted(github.issues[4]["labels"]) == ["caffeine", "check"]


def test_a_failed_adoption_is_an_error_and_the_run_goes_on(tmp_path):
    folder = study(tmp_path, "caffeine/A")
    study(tmp_path, "caffeine/B", issue=2)
    github = FakeGitHub(
        issues=[
            {"number": 2, "title": "y"},
            {"number": 4, "title": "Curate caffeine/A"},
        ],
        assignable=["ana-gh"],
    )
    github.fail[("PATCH", 4)] = 422
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert len(result.errors) == 1
    assert result.errors[0].startswith("caffeine/A: GitHub answered 422")
    assert result.adopted == [] and number_of(folder) is None
    assert github.issues[2]["title"] == "caffeine/B"


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        (403, "GitHub answered 403 for PATCH /repos/owner/data/issues/2: refused"),
        (401, "GitHub answered 401 for PATCH /repos/owner/data/issues/2: refused"),
        (429, "GitHub limits the requests; try again in 60 seconds"),
        (httpx2.ConnectError("down"), "GitHub cannot be reached: ConnectError"),
    ],
)
def test_a_failure_every_request_would_hit_stops_the_run(tmp_path, failure, message):
    for number, name in enumerate("ABC", start=1):
        study(tmp_path, f"caffeine/{name}", issue=number)
    github = FakeGitHub(
        issues=[{"number": n, "title": "x"} for n in (1, 2, 3)],
        assignable=["ana-gh"],
    )
    github.fail[("PATCH", 2)] = failure
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER)
    assert result.stopped == message and not result.ok
    assert result.applied == 1 and len(result.plan.changes) == 3
    assert github.issues[1]["title"] == "caffeine/A"
    assert github.issues[3]["title"] == "x"
    assert [path for _, path, _ in github.writes].count("/issues/3") == 0


def test_a_failed_read_stops_the_run_before_any_write(tmp_path):
    study(tmp_path, "caffeine/A", issue=1)
    github = FakeGitHub(issues=[{"number": 1, "title": "x"}])
    github.fail[("GET", None)] = 401
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER)
    assert result.stopped == (
        "GitHub answered 401 for GET /repos/owner/data/issues: refused"
    )
    assert result.plan.changes == [] and github.writes == []


def test_a_failed_issue_is_an_error_and_the_run_goes_on(tmp_path):
    study(tmp_path, "caffeine/A", issue=1)
    study(tmp_path, "caffeine/B", issue=2)
    github = FakeGitHub(
        issues=[{"number": 1, "title": "x"}, {"number": 2, "title": "y"}],
        assignable=["ana-gh"],
    )
    github.fail[("PATCH", 1)] = 422
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER)
    assert result.errors and result.errors[0].startswith(
        "caffeine/A: GitHub answered 422"
    )
    assert github.issues[2]["title"] == "caffeine/B"
