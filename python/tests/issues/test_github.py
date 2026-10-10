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


def test_issues_are_listed_oldest_first_and_repeats_are_dropped():
    seen = []

    def handler(request):
        params = request.url.params
        seen.append((params["sort"], params["direction"]))
        if params["page"] == "1":
            return httpx2.Response(200, json=[issue(n) for n in range(1, 101)])
        return httpx2.Response(200, json=[issue(100), issue(101)])

    with github(handler) as client:
        issues = client.issues()
    assert [i.number for i in issues] == list(range(1, 102))
    assert seen == [("created", "asc")] * 2


@pytest.mark.parametrize(
    "headers",
    [
        {"retry-after": "soon"},
        {"retry-after": "nan"},
        {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "later"},
        {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "inf"},
    ],
)
def test_malformed_limit_headers_wait_the_fallback(headers):
    answers = [
        httpx2.Response(403, headers=headers, json={"message": "m"}),
        httpx2.Response(200, json=[]),
    ]
    clock = Clock()
    with github(lambda request: answers.pop(0), clock) as client:
        client.labels()
    assert clock.slept == [60.0]


def test_an_http_date_retry_after_is_waited_for():
    answers = [
        httpx2.Response(
            429,
            headers={"retry-after": "Thu, 01 Jan 1970 00:17:30 GMT"},
            json={"message": "m"},
        ),
        httpx2.Response(200, json=[]),
    ]
    clock = Clock(now=1000.0)
    with github(lambda request: answers.pop(0), clock) as client:
        client.labels()
    assert clock.slept == [50.0]


def test_an_infinite_retry_after_does_not_escape_the_error_contract():
    response = httpx2.Response(
        429, headers={"retry-after": "inf"}, json={"message": "m"}
    )
    with github(lambda request: response, max_wait=0) as client:
        with pytest.raises(GitHubError) as error:
            client.labels()
    assert error.value.rate_limited


def test_exhausted_waits_are_a_rate_limit_error_but_other_errors_are_not():
    response = httpx2.Response(429, headers={"retry-after": "1"}, json={"message": "m"})
    with github(lambda request: response) as client:
        with pytest.raises(GitHubError) as error:
            client.labels()
    assert error.value.rate_limited and error.value.status_code == 429
    with github(
        lambda request: httpx2.Response(404, json={"message": "Not Found"})
    ) as client:
        with pytest.raises(GitHubError) as error:
            client.labels()
    assert not error.value.rate_limited


def test_a_secondary_rate_limit_message_waits_a_minute():
    answers = [
        httpx2.Response(
            403, json={"message": "You have exceeded a Secondary Rate Limit."}
        ),
        httpx2.Response(200, json=[]),
    ]
    clock = Clock()
    with github(lambda request: answers.pop(0), clock) as client:
        client.labels()
    assert clock.slept == [60.0]


def test_a_redirect_is_an_error_naming_the_location():
    response = httpx2.Response(
        301, headers={"location": "https://api.github.com/repositories/1/issues"}
    )
    with github(lambda request: response) as client:
        with pytest.raises(GitHubError, match="301.*repositories/1/issues") as error:
            client.issues()
        with pytest.raises(GitHubError):
            client.update_issue(5, title="drug/S5")
    assert error.value.status_code == 301


@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(200, content=b"<html>"),
        httpx2.Response(200, json={"title": "drug/S5", "state": "open"}),
        httpx2.Response(200, json=issue(5, labels="curate")),
        httpx2.Response(200, json=issue(5, title=None)),
        httpx2.Response(200, json=[]),
    ],
)
def test_unexpected_bodies_are_errors(response):
    with github(lambda request: response) as client:
        with pytest.raises(GitHubError):
            client.update_issue(5, title="drug/S5")


def test_unexpected_listings_are_errors():
    for body in (b"<html>", b'[{"number": 1}]', b'{"a": 1}', b'[{"name": 3}]'):
        with github(
            lambda request, body=body: httpx2.Response(200, content=body)
        ) as client:
            for call in (client.issues, client.labels, client.assignable):
                with pytest.raises(GitHubError):
                    call()


def test_token_and_repository_are_validated():
    assert token_from({"GH_TOKEN": "  ", "GITHUB_TOKEN": " b\n"}) == "b"
    assert token_from({"GH_TOKEN": ""}) is None
    for token in ("a b", "a\nb", "a\x00b"):
        with pytest.raises(ValueError, match="token"):
            GitHub("owner/data", token)
    for value in ("../..", "./x", "a/..", ".hidden/x", "x/.hidden", "a/b/c"):
        with pytest.raises(ValueError, match="owner/name"):
            repository_from(value, environ={})
    assert repository_from("a.b/c.d-e_f", environ={}) == "a.b/c.d-e_f"


def test_waits_over_five_seconds_are_announced():
    answers = [
        httpx2.Response(429, headers={"retry-after": "7"}, json={"message": "m"}),
        httpx2.Response(429, headers={"retry-after": "5"}, json={"message": "m"}),
        httpx2.Response(200, json=[]),
    ]
    announced = []
    clock = Clock()
    with github(
        lambda request: answers.pop(0),
        clock,
        on_wait=lambda seconds, reason: announced.append((seconds, reason)),
    ) as client:
        client.labels()
    assert clock.slept == [7.0, 5.0]
    assert announced == [(7.0, "GitHub limits the requests")]


def test_an_unreachable_github_is_marked():
    def handler(request):
        raise httpx2.ConnectError("down", request=request)

    with github(handler) as client:
        with pytest.raises(GitHubError, match="cannot be reached") as error:
            client.labels()
    assert error.value.unreachable and error.value.status_code is None
    with github(lambda request: httpx2.Response(200, content=b"<html>")) as client:
        with pytest.raises(GitHubError) as error:
            client.labels()
    assert not error.value.unreachable


def test_a_not_found_without_token_names_the_token():
    def handler(request):
        assert "authorization" not in request.headers
        return httpx2.Response(404, json={"message": "Not Found"})

    with GitHub("owner/data", transport=httpx2.MockTransport(handler)) as client:
        with pytest.raises(GitHubError) as error:
            client.issues()
    assert str(error.value) == (
        "GitHub answered 404 for GET /repos/owner/data/issues: Not Found; "
        "a private repository needs GH_TOKEN or GITHUB_TOKEN"
    )
    with github(
        lambda request: httpx2.Response(404, json={"message": "Not Found"})
    ) as client:
        with pytest.raises(GitHubError) as error:
            client.issues()
    assert str(error.value).endswith(": Not Found")


@pytest.mark.parametrize(
    ("after", "message"),
    [("1", "1 second"), ("0.2", "1 second"), ("30.5", "31 seconds")],
)
def test_an_exhausted_wait_names_the_last_wait(after, message):
    response = httpx2.Response(
        429, headers={"retry-after": after}, json={"message": "m"}
    )
    with github(lambda request: response) as client:
        with pytest.raises(GitHubError) as error:
            client.labels()
    assert str(error.value) == f"GitHub limits the requests; try again in {message}"


def test_an_empty_assignee_list_is_sent():
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx2.Response(200, json=issue(5))

    with github(handler) as client:
        client.update_issue(5, assignees=[], labels=[])
    assert bodies == [{"labels": [], "assignees": []}]


def test_the_comments_of_an_issue_are_read_from_every_page():
    requests = []

    def handler(request):
        requests.append((request.url.path, request.url.params["page"]))
        page = int(request.url.params["page"])
        count = 100 if page == 1 else 1
        return httpx2.Response(200, json=[{"body": f"{page}"}] * count)

    with github(handler) as client:
        bodies = client.comments(5)
    assert bodies == ["1"] * 100 + ["2"]
    assert requests == [
        ("/repos/owner/data/issues/5/comments", "1"),
        ("/repos/owner/data/issues/5/comments", "2"),
    ]


def test_comments_without_a_text_body_are_left_out():
    comments = [{"body": "Duplicate of #4"}, {"body": None}, {"id": 3}, {"body": 5}]
    with github(lambda request: httpx2.Response(200, json=comments)) as client:
        assert client.comments(5) == ["Duplicate of #4"]
    for body in (b"<html>", b'{"a": 1}', b"[1]"):
        with github(
            lambda request, body=body: httpx2.Response(200, content=body)
        ) as client:
            with pytest.raises(GitHubError):
                client.comments(5)


def test_one_issue_is_read():
    paths = []

    def handler(request):
        paths.append((request.method, request.url.path))
        return httpx2.Response(200, json=issue(5, state="closed"))

    with github(handler) as client:
        found = client.issue(5)
    assert (found.number, found.state) == (5, "closed")
    assert paths == [("GET", "/repos/owner/data/issues/5")]
