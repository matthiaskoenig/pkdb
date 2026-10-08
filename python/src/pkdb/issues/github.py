"""A small GitHub REST client for the issues of the pkdb_data repository."""

import os
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import httpx2

from pkdb import __version__

API = "https://api.github.com"
DEFAULT_REPOSITORY = "matthiaskoenig/pkdb_data"
REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
PER_PAGE = 100
MAX_PAGES = 1000
MAX_WAITS = 5
# GitHub asks for at least one second between mutating requests.
WRITE_INTERVAL = 1.0


class GitHubError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    state: str
    state_reason: str | None
    labels: tuple[str, ...]
    assignees: tuple[str, ...]

    @classmethod
    def from_api(cls, data: dict) -> Issue:
        return cls(
            number=data["number"],
            title=data["title"],
            state=data["state"],
            state_reason=data.get("state_reason"),
            labels=tuple(label["name"] for label in data.get("labels", [])),
            assignees=tuple(user["login"] for user in data.get("assignees", [])),
        )


def repository_from(
    value: str | None = None, environ: Mapping[str, str] = os.environ
) -> str:
    repository = value or environ.get("PKDB_ISSUES_REPO") or DEFAULT_REPOSITORY
    if not REPOSITORY.fullmatch(repository):
        raise ValueError("GitHub repository must be owner/name")
    return repository


def token_from(environ: Mapping[str, str] = os.environ) -> str | None:
    return environ.get("GH_TOKEN") or environ.get("GITHUB_TOKEN") or None


class GitHub:
    def __init__(
        self,
        repository: str,
        token: str | None = None,
        *,
        transport: httpx2.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
        write_interval: float = WRITE_INTERVAL,
        max_wait: float | None = None,
    ):
        self.repository = repository_from(repository, environ={})
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": f"pkdb/{__version__}",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx2.Client(headers=headers, timeout=30, transport=transport)
        self._sleep = sleep
        self._clock = clock
        self._write_interval = write_interval
        self._max_wait = max_wait
        self._last_write: float | None = None

    def __enter__(self) -> GitHub:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def pages(
        self, resource: str, params: Mapping[str, str | int] | None = None
    ) -> list[dict]:
        items: list[dict] = []
        for page in range(1, MAX_PAGES + 1):
            response = self._send(
                "GET",
                f"/repos/{self.repository}/{resource}",
                params={**(params or {}), "per_page": PER_PAGE, "page": page},
            )
            values = response.json()
            if not isinstance(values, list):
                raise GitHubError(f"GitHub answered {resource} with no list")
            items.extend(values)
            if len(values) < PER_PAGE:
                return items
        raise GitHubError(f"GitHub lists more than {MAX_PAGES} pages of {resource}")

    def issues(self) -> list[Issue]:
        return [
            Issue.from_api(item)
            for item in self.pages("issues", {"state": "all"})
            if "pull_request" not in item
        ]

    def assignable(self) -> set[str]:
        return {
            user["login"]
            for user in self.pages("assignees")
            if user.get("type") != "Bot"
        }

    def labels(self) -> list[str]:
        return [label["name"] for label in self.pages("labels")]

    def create_label(self, name: str, color: str) -> None:
        self._write(
            "POST", f"/repos/{self.repository}/labels", {"name": name, "color": color}
        )

    def create_issue(
        self, title: str, *, labels: list[str], assignees: list[str]
    ) -> Issue:
        body = {"title": title, "labels": labels, "assignees": assignees}
        return Issue.from_api(
            self._write("POST", f"/repos/{self.repository}/issues", body).json()
        )

    def update_issue(
        self,
        number: int,
        *,
        title: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
        state: str | None = None,
        state_reason: str | None = None,
    ) -> Issue:
        fields = {
            "title": title,
            "labels": labels,
            "assignees": assignees,
            "state": state,
            "state_reason": state_reason,
        }
        body = {key: value for key, value in fields.items() if value is not None}
        return Issue.from_api(
            self._write(
                "PATCH", f"/repos/{self.repository}/issues/{number}", body
            ).json()
        )

    def comment(self, number: int, body: str) -> None:
        self._write(
            "POST", f"/repos/{self.repository}/issues/{number}/comments", {"body": body}
        )

    def _write(self, method: str, path: str, body: dict) -> httpx2.Response:
        if self._last_write is not None:
            delay = self._last_write + self._write_interval - self._clock()
            if delay > 0:
                self._sleep(delay)
        try:
            return self._send(method, path, json=body)
        finally:
            self._last_write = self._clock()

    def _send(self, method: str, path: str, **kwargs) -> httpx2.Response:
        waits = 0
        while True:
            try:
                response = self._client.request(method, API + path, **kwargs)
            except httpx2.RequestError as error:
                raise GitHubError(
                    f"GitHub cannot be reached: {type(error).__name__}"
                ) from None
            wait = self._wait(response)
            if wait is None:
                break
            if waits == MAX_WAITS or (
                self._max_wait is not None and wait > self._max_wait
            ):
                raise GitHubError(
                    f"GitHub limits the requests; try again in {round(wait)} seconds",
                    status_code=response.status_code,
                )
            waits += 1
            self._sleep(wait)
        if response.is_error:
            raise GitHubError(
                f"GitHub answered {response.status_code} for {method} {path}: {_message(response)}",
                status_code=response.status_code,
            )
        return response

    def _wait(self, response: httpx2.Response) -> float | None:
        if response.status_code not in (403, 429):
            return None
        if (after := response.headers.get("retry-after")) is not None:
            return max(float(after), 1.0)
        if response.headers.get("x-ratelimit-remaining") == "0":
            reset = float(response.headers.get("x-ratelimit-reset", "0"))
            return max(reset - self._clock(), 0.0) + 1.0
        return None


def _message(response: httpx2.Response) -> str:
    try:
        message = response.json().get("message")
    except ValueError, AttributeError:
        message = None
    return message if isinstance(message, str) and message else response.reason_phrase
