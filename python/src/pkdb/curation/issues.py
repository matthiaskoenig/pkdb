"""GitHub assignment refresh and issue to study matching for the curation engine.

Reads and writes engine attributes: lock, github, github_user, repository, mappings, studies.
Uses engine methods _save and snapshot.
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

    def map_assignment(self, number, study_id):
        with self.lock:
            row = self._selected([study_id])[0]
            if number not in {
                issue["number"] for issue in self.github.data.get("issues", [])
            }:
                raise ValueError("Unknown GitHub issue")
            key = f"{self.repository}#{number}"
            self.mappings.setdefault(key, [])
            if str(row["_folder"]) not in self.mappings[key]:
                self.mappings[key].append(str(row["_folder"]))
            self._save()
        return self.snapshot()

    def _issue_rows(self):
        issues = []
        for raw in self.github.data.get("issues", []):
            issue = dict(raw)
            mapped = self.mappings.get(f"{self.repository}#{raw['number']}")
            title = raw["title"].strip().replace("\\", "/")
            candidates = [
                row["id"]
                for row in self.studies.values()
                if row["path"] == title
                or row["path"] == f"studies/{title}"
                or (row["_folder"].parent.name + "/" + row["_folder"].name) == title
            ]
            issue["study_ids"] = (
                [r["id"] for r in self.studies.values() if str(r["_folder"]) in mapped]
                if mapped is not None
                else candidates
                if len(candidates) == 1
                else []
            )
            issues.append(issue)
        return issues
