import pytest
from fake_github import FakeGitHub

from pkdb.issues.github import GitHubError
from pkdb.issues.single import issue_for_new_study, rename_issue


def test_an_existing_issue_with_the_exact_title_is_adopted():
    github = FakeGitHub(
        issues=[
            {"number": 3, "title": "Curate caffeine/A"},
            {
                "number": 5,
                "title": "caffeine/A",
                "state": "closed",
                "state_reason": "completed",
            },
            {"number": 8, "title": "caffeine/A"},
        ]
    )
    with github.client() as client:
        issue, created = issue_for_new_study(client, "caffeine/A")
    assert (issue.number, created) == (8, False) and github.writes == []


def test_a_closed_issue_is_adopted_when_it_is_the_only_one():
    github = FakeGitHub(
        issues=[{"number": 5, "title": "caffeine/A", "state": "closed"}]
    )
    with github.client() as client:
        issue, created = issue_for_new_study(client, "caffeine/A")
    assert (issue.number, created) == (5, False)


def test_without_a_match_an_issue_is_created_with_labels():
    github = FakeGitHub()
    with github.client() as client:
        issue, created = issue_for_new_study(client, "caffeine/A")
    assert created and github.issues[issue.number]["title"] == "caffeine/A"
    assert sorted(github.issues[issue.number]["labels"]) == ["caffeine", "curate"]
    assert sorted(github.labels) == ["caffeine", "curate"]


def test_existing_labels_are_not_created_again():
    github = FakeGitHub(labels=["Caffeine", "curate"])
    with github.client() as client:
        issue_for_new_study(client, "caffeine/A")
    assert github.labels == ["Caffeine", "curate"]


def test_a_token_without_push_access_is_an_error():
    github = FakeGitHub(push_access=False)
    with github.client() as client:
        with pytest.raises(GitHubError, match="did not apply the labels"):
            issue_for_new_study(client, "caffeine/A")


def test_rename():
    github = FakeGitHub(issues=[{"number": 2, "title": "caffeine/A"}])
    with github.client() as client:
        rename_issue(client, 2, "codeine/B")
    assert github.issues[2]["title"] == "codeine/B"


def test_an_issue_that_another_study_names_is_not_taken():
    github = FakeGitHub(issues=[{"number": 4, "title": "caffeine/A"}])
    with github.client() as client:
        issue, created = issue_for_new_study(client, "caffeine/A", claimed={4})
    assert created and issue.number == 5
