"""GitHub assignment refresh and issue lookup by number for the curation engine.

Reads and writes engine attributes: lock, github, github_user, repository, studies.
Uses engine method _save.
"""

from pkdb.curation.state import EngineState


class IssuesMixin(EngineState):
    def refresh_assignments(self):
        if self.offline:
            return {**self.github.data, "status": "offline"}
        result = self.github.refresh()
        with self.lock:
            self._save()
        return result

    def _issue_for(self, number):
        if number is None:
            return None
        for issue in self.github.data.get("issues", []):
            if issue.get("number") == number:
                return {
                    "number": number,
                    "state": issue.get("state"),
                    "labels": issue.get("labels", []),
                    "assignees": issue.get("assignees", []),
                    "url": issue.get("html_url"),
                }
        return {
            "number": number,
            "state": None,
            "labels": [],
            "assignees": [],
            "url": None,
        }
