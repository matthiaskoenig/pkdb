"""An in-memory GitHub repository behind httpx2.MockTransport for the issue sync tests."""

import json
import re
from collections.abc import Callable
from typing import Any

import httpx2

from pkdb.issues.github import GitHub

PER_PAGE = 100


class FakeGitHub:
    """Issues, labels and assignable users of `owner/data`, served to the real client.

    `writes` records every request that is not a GET as (method, path, body);
    `fail` maps (method, issue number or None) to the status of a refusal, or
    to a transport error to raise, and a 429 refusal carries Retry-After like a
    GitHub rate limit; `refuse`, when set, returns the status of a refusal for
    (method, issue number or None, body), or None to answer; `sleeps` records
    the waits of the client, which never sleeps.

    Like GitHub, a PATCH changes `state_reason` only together with `state`, and
    without `push_access` labels and assignees of a write are dropped silently.
    """

    def __init__(self, issues=(), labels=(), assignable=(), push_access=True):
        self.issues: dict[int, dict[str, Any]] = {
            issue["number"]: {
                "state": "open",
                "state_reason": None,
                "labels": [],
                "assignees": [],
                **issue,
            }
            for issue in issues
        }
        self.labels = list(labels)
        self.assignable = list(assignable)
        self.comments: list[tuple[int | None, str]] = []
        self.writes: list[tuple[str, str, dict[str, Any]]] = []
        self.fail: dict[tuple[str, int | None], int | httpx2.TransportError] = {}
        self.refuse: Callable[[str, int | None, dict[str, Any]], int | None] | None = (
            None
        )
        self.sleeps: list[float] = []
        self.push_access = push_access

    def handler(self, request):
        path = request.url.path.removeprefix("/repos/owner/data")
        body: dict[str, Any] = json.loads(request.content) if request.content else {}
        if request.method != "GET":
            self.writes.append((request.method, path, body))
        found = re.fullmatch(r"/issues/(\d+)(?:/comments)?", path)
        number = int(found[1]) if found else None
        if isinstance(status := self.fail.get((request.method, number)), Exception):
            raise status
        if status is None and self.refuse is not None:
            status = self.refuse(request.method, number, body)
        if status is not None:
            headers = {"retry-after": "60"} if status == 429 else {}
            return httpx2.Response(status, headers=headers, json={"message": "refused"})
        if (
            request.method == "GET"
            and number is not None
            and path == f"/issues/{number}"
        ):
            if number not in self.issues:
                return httpx2.Response(404, json={"message": "Not Found"})
            return httpx2.Response(200, json=self._api(self.issues[number]))
        if request.method == "GET":
            return self._page(path, number, int(request.url.params.get("page", "1")))
        if path == "/labels":
            self.labels.append(body["name"])
            return httpx2.Response(201, json=body)
        if not self.push_access:
            body = {
                key: value
                for key, value in body.items()
                if key not in ("labels", "assignees")
            }
        if path == "/issues":
            number = max(self.issues, default=0) + 1
            self.issues[number] = {
                "number": number,
                "state": "open",
                "state_reason": None,
                "labels": [],
                "assignees": [],
                **body,
            }
            return httpx2.Response(201, json=self._api(self.issues[number]))
        if path.endswith("/comments"):
            self.comments.append((number, body["body"]))
            return httpx2.Response(201, json={"body": body["body"]})
        assert request.method == "PATCH" and number is not None
        issue = self.issues[number]
        state = body.get("state", issue["state"])
        if state == issue["state"]:
            body = {key: value for key, value in body.items() if key != "state_reason"}
        else:
            default = "completed" if state == "closed" else "reopened"
            body = {"state_reason": default, **body}
        issue.update(body)
        return httpx2.Response(200, json=self._api(issue))

    def _page(self, path, number, page):
        # Query parameters other than the page (state, sort, direction) are ignored.
        if path.endswith("/comments"):
            items = [{"body": body} for n, body in self.comments if n == number]
        else:
            items = {
                "/issues": [self._api(issue) for issue in self.issues.values()],
                "/labels": [{"name": name} for name in self.labels],
                "/assignees": [
                    {"login": login, "type": "User"} for login in self.assignable
                ],
            }[path]
        return httpx2.Response(200, json=items[(page - 1) * PER_PAGE : page * PER_PAGE])

    @staticmethod
    def _api(issue):
        return {
            **issue,
            "labels": [{"name": name} for name in issue["labels"]],
            "assignees": [{"login": login} for login in issue["assignees"]],
        }

    def client(self, **options):
        return GitHub(
            "owner/data",
            "token",
            transport=httpx2.MockTransport(self.handler),
            sleep=self.sleeps.append,
            write_interval=0,
            **options,
        )
