import json

import httpx2
import pytest

from pkdb.issues.github import (
    DEFAULT_REPOSITORY,
    GitHub,
    GitHubError,
    repository_from,
    token_from,
)


class Clock:
    def __init__(self, now=1000.0):
        self.now = now
        self.slept = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


def github(handler, clock=None, **options):
    clock = clock or Clock()
    return GitHub(
        "owner/data",
        "secret-token",
        transport=httpx2.MockTransport(handler),
        sleep=clock.sleep,
        clock=clock.time,
        **options,
    )


def issue(number, **fields):
    return {
        "number": number,
        "title": f"drug/S{number}",
        "state": "open",
        "labels": [],
        "assignees": [],
        **fields,
    }


def test_issues_of_all_pages_without_pull_requests():
    pages = []

    def handler(request):
        page = int(request.url.params["page"])
        pages.append((request.url.path, request.url.params["state"], page))
        assert request.headers["authorization"] == "Bearer secret-token"
        if page == 1:
            return httpx2.Response(
                200,
                json=[issue(n) for n in range(1, 100)]
                + [{**issue(100), "pull_request": {}}],
            )
        return httpx2.Response(
            200,
            json=[
                issue(101, labels=[{"name": "curate"}], assignees=[{"login": "ana"}])
            ],
        )

    with github(handler) as client:
        issues = client.issues()
    assert [i.number for i in issues] == [*range(1, 100), 101]
    assert issues[-1].labels == ("curate",) and issues[-1].assignees == ("ana",)
    assert pages == [
        ("/repos/owner/data/issues", "all", 1),
        ("/repos/owner/data/issues", "all", 2),
    ]


def test_waits_for_retry_after():
    answers = [
        httpx2.Response(
            403, headers={"retry-after": "7"}, json={"message": "secondary"}
        ),
        httpx2.Response(200, json=[]),
    ]
    clock = Clock()
    with github(lambda request: answers.pop(0), clock) as client:
        assert client.issues() == []
    assert clock.slept == [7.0]


def test_waits_for_the_reset_of_an_exhausted_limit():
    clock = Clock(now=1000.0)
    answers = [
        httpx2.Response(
            403,
            headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1060"},
            json={"message": "limit"},
        ),
        httpx2.Response(200, json=[]),
    ]
    with github(lambda request: answers.pop(0), clock) as client:
        client.labels()
    assert clock.slept == [61.0]


def test_a_wait_above_max_wait_is_an_error():
    response = httpx2.Response(
        429, headers={"retry-after": "30"}, json={"message": "slow down"}
    )
    with github(lambda request: response, max_wait=0) as client:
        with pytest.raises(GitHubError, match="limit"):
            client.issues()


def test_a_forbidden_request_is_an_error_without_the_token():
    response = httpx2.Response(
        403, json={"message": "Resource not accessible by integration"}
    )
    clock = Clock()
    with github(lambda request: response, clock) as client:
        with pytest.raises(GitHubError) as error:
            client.update_issue(5, title="drug/S5")
    assert error.value.status_code == 403
    assert "Resource not accessible by integration" in str(error.value)
    assert "secret-token" not in str(error.value)
    assert clock.slept == []


def test_writes_send_only_the_given_fields_one_second_apart():
    bodies = []

    def handler(request):
        bodies.append((request.method, request.url.path, json.loads(request.content)))
        return httpx2.Response(
            200,
            json=issue(5, title="drug/S5", state="closed", state_reason="completed"),
        )

    clock = Clock()
    with github(handler, clock) as client:
        updated = client.update_issue(5, state="closed", state_reason="completed")
        client.comment(6, "Duplicate of #5")
    assert bodies[0] == (
        "PATCH",
        "/repos/owner/data/issues/5",
        {"state": "closed", "state_reason": "completed"},
    )
    assert bodies[1] == (
        "POST",
        "/repos/owner/data/issues/6/comments",
        {"body": "Duplicate of #5"},
    )
    assert updated.state_reason == "completed"
    assert clock.slept == [1.0]


def test_repository_and_token_from_the_environment():
    assert repository_from(environ={}) == DEFAULT_REPOSITORY
    assert repository_from(environ={"PKDB_ISSUES_REPO": "me/data"}) == "me/data"
    assert (
        repository_from("you/data", environ={"PKDB_ISSUES_REPO": "me/data"})
        == "you/data"
    )
    with pytest.raises(ValueError, match="owner/name"):
        repository_from("not a repository", environ={})
    assert token_from({"GITHUB_TOKEN": "b"}) == "b"
    assert token_from({"GH_TOKEN": "a", "GITHUB_TOKEN": "b"}) == "a"
    assert token_from({}) is None
