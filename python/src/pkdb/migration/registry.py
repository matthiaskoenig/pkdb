"""The registry `studies/study_identifiers.json` of released format 1 studies."""

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from pkdb.migration.model import NotConverted, RegistryFindings
from pkdb.schemas.review import Release


@dataclass(frozen=True)
class Registry:
    """PKDB identifiers with the `<substance>/<name>` location and the release date."""

    entries: dict[str, tuple[str, date]] = field(default_factory=dict)

    @classmethod
    def read(cls, path: Path | None) -> Registry:
        if path is None:
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            {
                pkdb_id: (location, date.fromisoformat(day))
                for pkdb_id, (location, day) in sorted(data.items())
            }
        )

    @property
    def identifiers(self) -> dict[str, str]:
        return {pkdb_id: location for pkdb_id, (location, _) in self.entries.items()}

    def _by_location(self) -> dict[str, list[str]]:
        located = defaultdict(list)
        for pkdb_id, (location, _) in self.entries.items():
            located[location].append(pkdb_id)
        return located

    def release(self, location: str) -> Release | None:
        ids = self._by_location().get(location, [])
        if len(ids) > 1:
            raise NotConverted(
                "double_identifier",
                f"{location} has the PKDB identifiers {', '.join(ids)} in the registry; "
                "keep one",
            )
        if not ids:
            return None
        return Release(pkdb_id=ids[0], date=self.entries[ids[0]][1])

    def findings(self, root: Path) -> RegistryFindings:
        """Studies with two identifiers and locations without a folder below root/studies."""
        located = self._by_location()
        return RegistryFindings(
            double_identifiers={
                location: ids
                for location, ids in sorted(located.items())
                if len(ids) > 1
            },
            missing_paths=sorted(
                location
                for location in located
                if not (root / "studies" / location).is_dir()
            ),
        )
