"""Read-only GitHub assignments; cached data remains usable without connectivity."""

import re
from datetime import UTC, datetime
from typing import Any

import httpx2


class GitHubAssignments:
    def __init__(self, repository, token=None, cached=None, transport=None):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("GitHub repository must be owner/name")
        self.repository = repository
        self.token = token
        self.data: dict[str, Any] = cached or {
            "users": [],
            "issues": [],
            "status": "not_loaded",
        }
        self.transport = transport

    def refresh(self):
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            with httpx2.Client(
                headers=headers, timeout=20, transport=self.transport
            ) as client:
                users = {}
                limited = False

                def pages(resource):
                    result = []
                    for page in range(1, 101):
                        response = client.get(
                            f"https://api.github.com/repos/{self.repository}/{resource}",
                            params={"state": "all", "per_page": 100, "page": page},
                        )
                        response.raise_for_status()
                        values = response.json()
                        if not isinstance(values, list):
                            raise ValueError("Unexpected GitHub response")
                        result.extend(values)
                        if len(values) < 100:
                            return result
                    raise ValueError(
                        "Repository exceeds the 10,000-item scan limit; narrow the repository"
                    )

                def add(user):
                    if user.get("type") != "Bot" and isinstance(user.get("login"), str):
                        users[user["id"]] = {
                            "id": user["id"],
                            "login": user["login"],
                            "name": user.get("name"),
                            "avatar_url": user.get("avatar_url"),
                        }

                try:
                    for user in pages("assignees"):
                        add(user)
                except httpx2.HTTPStatusError as error:
                    if error.response.status_code not in {403, 404}:
                        raise
                    limited = True
                issues = []
                for issue in pages("issues"):
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
        except httpx2.HTTPError, ValueError, KeyError, TypeError:
            self.data = {
                **self.data,
                "status": "unavailable",
                "error": "Could not refresh GitHub. Cached assignments are retained; check repository access or request limits.",
            }
        return self.data
