"""Read-only GitHub assignments; cached data remains usable without connectivity."""

import re
from datetime import UTC, datetime
from typing import Any

from pkdb.issues.github import GitHub, GitHubError


class GitHubAssignments:
    def __init__(self, repository, token=None, cached=None, transport=None):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("GitHub repository must be owner/name")
        self.repository = repository
        self.token = token
        self.data = cached or {"users": [], "issues": [], "status": "not_loaded"}
        self.transport = transport

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    @data.setter
    def data(self, value: dict[str, Any]) -> None:
        self._data = value
        # Rows look their issue up by number on every snapshot; the first one counts.
        self._issues: dict[Any, dict] = {}
        for issue in value.get("issues", []):
            self._issues.setdefault(issue.get("number"), issue)

    def issue(self, number) -> dict | None:
        """The issue with this number, or None."""
        return self._issues.get(number)

    def refresh(self):
        try:
            with GitHub(
                self.repository,
                self.token,
                transport=self.transport,
                write_interval=0,
                max_wait=0,
            ) as github:
                users = {}
                limited = False

                def add(user):
                    if user.get("type") != "Bot" and isinstance(user.get("login"), str):
                        users[user["id"]] = {
                            "id": user["id"],
                            "login": user["login"],
                            "name": user.get("name"),
                            "avatar_url": user.get("avatar_url"),
                        }

                try:
                    for user in github.pages("assignees"):
                        add(user)
                except GitHubError as error:
                    if error.rate_limited or error.status_code not in {403, 404}:
                        raise
                    limited = True
                issues = []
                # Oldest first: issues created while paging land on the last page.
                params = {"state": "all", "sort": "created", "direction": "asc"}
                for issue in github.pages("issues", params):
                    if "pull_request" in issue:
                        continue
                    for user in issue.get("assignees", []):
                        add(user)
                    issues.append(
                        {
                            "number": issue["number"],
                            "title": issue["title"],
                            "html_url": f"https://github.com/{self.repository}/issues/{issue['number']}",
                            "state": issue["state"],
                            "assignees": [
                                u["login"] for u in issue.get("assignees", [])
                            ],
                            "labels": [v["name"] for v in issue.get("labels", [])],
                        }
                    )
                self.data = {
                    "users": sorted(
                        users.values(), key=lambda u: u["login"].casefold()
                    ),
                    "issues": issues,
                    "limited": limited,
                    "status": "ready",
                    "refreshed_at": datetime.now(UTC).isoformat(),
                    "error": None,
                }
        except GitHubError, ValueError, KeyError, TypeError:
            self.data = {
                **self.data,
                "status": "unavailable",
                "error": "Could not refresh GitHub. Cached assignments are retained; check repository access or request limits.",
            }
        return self.data
