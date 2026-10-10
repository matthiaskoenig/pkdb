"""A small GitHub REST client for the issues of the pkdb_data repository."""

import math
import os
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from email.utils import parsedate_to_datetime

import httpx2

from pkdb import __version__
from pkdb.issues import counted

API = "https://api.github.com"
DEFAULT_REPOSITORY = "matthiaskoenig/pkdb_data"
REPOSITORY = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_.-]*")
PER_PAGE = 100
MAX_PAGES = 1000
MAX_WAITS = 5
# GitHub asks for at least one second between mutating requests.
WRITE_INTERVAL = 1.0
# GitHub documents one minute for a secondary rate limit without a Retry-After header.
FALLBACK_WAIT = 60.0
# Waits longer than this are announced to `on_wait`.
ANNOUNCED_WAIT = 5.0
RATE_LIMIT = "GitHub limits the requests"


class GitHubError(RuntimeError):
    """A failed GitHub request.

    `rate_limited` marks a rate limit that outlasted the waits and
    `unreachable` a request that never got an answer.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        rate_limited: bool = False,
        unreachable: bool = False,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.rate_limited = rate_limited
        self.unreachable = unreachable


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
        try:
            number, title, state = data["number"], data["title"], data["state"]
            if not (
                isinstance(number, int)
                and isinstance(title, str)
                and isinstance(state, str)
            ):
                raise TypeError
            return cls(
                number=number,
                title=title,
                state=state,
                state_reason=data.get("state_reason"),
                labels=tuple(_names(data.get("labels", []), "name")),
                assignees=tuple(_names(data.get("assignees", []), "login")),
            )
        except KeyError, TypeError, AttributeError:
            raise GitHubError(
                "GitHub answered an issue in an unexpected shape"
            ) from None


def repository_from(
    value: str | None = None, environ: Mapping[str, str] = os.environ
) -> str:
    repository = value or environ.get("PKDB_ISSUES_REPO") or DEFAULT_REPOSITORY
    if not REPOSITORY.fullmatch(repository):
        raise ValueError("GitHub repository must be owner/name")
    return repository


def token_from(environ: Mapping[str, str] = os.environ) -> str | None:
    for name in ("GH_TOKEN", "GITHUB_TOKEN"):
        if token := environ.get(name, "").strip():
            return token
    return None


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
        on_wait: Callable[[float, str], None] | None = None,
    ):
        """`on_wait` is told the seconds and the reason of every wait over five seconds."""
        self.repository = repository_from(repository, environ={})
        if token and any(c.isspace() or not c.isprintable() for c in token):
            raise ValueError(
                "GitHub token must not contain whitespace or control characters"
            )
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": f"pkdb/{__version__}",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._authorized = bool(token)
        self._client = httpx2.Client(headers=headers, timeout=30, transport=transport)
        self._sleep = sleep
        self._clock = clock
        self._write_interval = write_interval
        self._max_wait = max_wait
        self._on_wait = on_wait
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
            values = _json(response)
            if not isinstance(values, list) or not all(
                isinstance(value, dict) for value in values
            ):
                raise GitHubError(f"GitHub answered {resource} with no list")
            items.extend(values)
            if len(values) < PER_PAGE:
                return items
        raise GitHubError(f"GitHub lists more than {MAX_PAGES} pages of {resource}")

    def issues(self) -> list[Issue]:
        # Oldest first: new issues land on the last page, so no page repeats an item.
        items = self.pages(
            "issues", {"state": "all", "sort": "created", "direction": "asc"}
        )
        issues: dict[int, Issue] = {}
        for item in items:
            if "pull_request" not in item:
                issue = Issue.from_api(item)
                issues.setdefault(issue.number, issue)
        return list(issues.values())

    def assignable(self) -> set[str]:
        users = [user for user in self.pages("assignees") if user.get("type") != "Bot"]
        return set(_safe_names(users, "login"))

    def labels(self) -> list[str]:
        return _safe_names(self.pages("labels"), "name")

    def create_label(self, name: str, color: str) -> None:
        self._write(
            "POST", f"/repos/{self.repository}/labels", {"name": name, "color": color}
        )

    def create_issue(
        self, title: str, *, labels: list[str], assignees: list[str]
    ) -> Issue:
        body = {"title": title, "labels": labels, "assignees": assignees}
        return Issue.from_api(
            _object(self._write("POST", f"/repos/{self.repository}/issues", body))
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
            _object(
                self._write("PATCH", f"/repos/{self.repository}/issues/{number}", body)
            )
        )

    def issue(self, number: int) -> Issue:
        """The issue `number` as GitHub has it now."""
        response = self._send("GET", f"/repos/{self.repository}/issues/{number}")
        return Issue.from_api(_object(response))

    def comments(self, number: int) -> list[str]:
        """The bodies of the comments of an issue, oldest first.

        A comment without a text body is left out.
        """
        return [
            item["body"]
            for item in self.pages(f"issues/{number}/comments")
            if isinstance(item.get("body"), str)
        ]

    def comment(self, number: int, body: str) -> None:
        self._write(
            "POST", f"/repos/{self.repository}/issues/{number}/comments", {"body": body}
        )

    def _write(self, method: str, path: str, body: dict) -> httpx2.Response:
        if self._last_write is not None:
            delay = self._last_write + self._write_interval - self._clock()
            if delay > 0:
                self._pause(delay, "GitHub asks for a pause between writes")
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
                    f"GitHub cannot be reached: {type(error).__name__}",
                    unreachable=True,
                ) from None
            wait = self._wait(response)
            if wait is None:
                break
            if waits == MAX_WAITS or (
                self._max_wait is not None and wait > self._max_wait
            ):
                raise GitHubError(
                    f"{RATE_LIMIT}; try again in {counted(math.ceil(wait), 'second')}",
                    status_code=response.status_code,
                    rate_limited=True,
                )
            waits += 1
            self._pause(wait, RATE_LIMIT)
        if 300 <= response.status_code < 400:
            location = response.headers.get("location", "unknown")
            raise GitHubError(
                f"GitHub answered {response.status_code} for {method} {path} "
                f"and points to {location}; check the repository name",
                status_code=response.status_code,
            )
        if response.is_error:
            hint = ""
            if response.status_code == 404 and not self._authorized:
                hint = "; a private repository needs GH_TOKEN or GITHUB_TOKEN"
            raise GitHubError(
                f"GitHub answered {response.status_code} for {method} {path}: "
                f"{_message(response)}{hint}",
                status_code=response.status_code,
            )
        return response

    def _pause(self, seconds: float, reason: str) -> None:
        if self._on_wait is not None and seconds > ANNOUNCED_WAIT:
            self._on_wait(seconds, reason)
        self._sleep(seconds)

    def _wait(self, response: httpx2.Response) -> float | None:
        if response.status_code not in (403, 429):
            return None
        if (after := response.headers.get("retry-after")) is not None:
            return max(self._retry_after(after), 1.0)
        if response.headers.get("x-ratelimit-remaining") == "0":
            reset = _number(response.headers.get("x-ratelimit-reset", ""))
            if reset is None:
                return FALLBACK_WAIT
            return max(reset - self._clock(), 0.0) + 1.0
        if "secondary rate limit" in _message(response).lower():
            return FALLBACK_WAIT
        return None

    def _retry_after(self, value: str) -> float:
        if (seconds := _number(value)) is not None:
            return seconds
        try:
            return parsedate_to_datetime(value).timestamp() - self._clock()
        except TypeError, ValueError, OverflowError:
            return FALLBACK_WAIT


def _number(value: str) -> float | None:
    try:
        number = float(value)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _json(response: httpx2.Response):
    try:
        return response.json()
    except ValueError:
        raise GitHubError(
            "GitHub answered with a body that is no JSON",
            status_code=response.status_code,
        ) from None


def _object(response: httpx2.Response) -> dict:
    data = _json(response)
    if not isinstance(data, dict):
        raise GitHubError(
            "GitHub answered an issue in an unexpected shape",
            status_code=response.status_code,
        )
    return data


def _safe_names(items, key: str) -> list[str]:
    try:
        return _names(items, key)
    except KeyError, TypeError, AttributeError:
        raise GitHubError("GitHub answered a list in an unexpected shape") from None


def _names(items, key: str) -> list[str]:
    if not isinstance(items, list):
        raise TypeError
    names = [item[key] for item in items]
    if not all(isinstance(name, str) for name in names):
        raise TypeError
    return names


def _message(response: httpx2.Response) -> str:
    try:
        message = response.json().get("message")
    except ValueError, AttributeError:
        message = None
    return message if isinstance(message, str) and message else response.reason_phrase
