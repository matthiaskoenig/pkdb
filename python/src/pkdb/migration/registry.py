"""The registry `studies/study_identifiers.json` of released format 1 studies."""

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from functools import cached_property
from pathlib import Path

from pkdb.migration.model import NotConverted, RegistryFindings
from pkdb.schemas.review import Release

PKDB_ID = re.compile(r"PKDB[0-9]{5}")


@dataclass(frozen=True)
class Registry:
    """PKDB identifiers with the `<substance>/<name>` location and the release date."""

    entries: dict[str, tuple[str, date]] = field(default_factory=dict)

    @classmethod
    def read(cls, path: Path | None) -> Registry:
        if path is None:
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(
                f"The registry {path.as_posix()} is not JSON: {error}"
            ) from error
        if not isinstance(data, dict):
            raise ValueError(
                f"The registry {path.as_posix()} must map PKDB identifiers to "
                "[location, date]"
            )
        entries = {}
        for pkdb_id, entry in sorted(data.items()):
            try:
                location, day = entry
                entries[pkdb_id] = (str(location), date.fromisoformat(day))
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"The registry {path.as_posix()} entry {pkdb_id} must be "
                    f"[location, YYYY-MM-DD], not {entry!r}"
                ) from error
        return cls(entries)

    @property
    def identifiers(self) -> dict[str, str]:
        return {pkdb_id: location for pkdb_id, (location, _) in self.entries.items()}

    @cached_property
    def _by_location(self) -> dict[str, list[str]]:
        located = defaultdict(list)
        for pkdb_id, (location, _) in self.entries.items():
            located[location].append(pkdb_id)
        return located

    def release(self, location: str, sid: str) -> Release | None:
        """The release of the study at `location` whose v1 study.json has `sid`.

        A v1 sid that is a PKDB identifier marks a released study, so the
        registry must give that identifier to that location; otherwise the
        study is refused rather than written without its release.
        """
        ids = self._by_location.get(location, [])
        if len(ids) > 1:
            raise NotConverted(
                "double_identifier",
                f"{location} has the PKDB identifiers {', '.join(ids)} in the registry; "
                "keep one",
            )
        release = Release(pkdb_id=ids[0], date=self.entries[ids[0]][1]) if ids else None
        if PKDB_ID.fullmatch(sid) and (release is None or release.pkdb_id != sid):
            raise NotConverted("registry_sid", self._conflict(location, sid, release))
        return release

    def _conflict(self, location: str, sid: str, release: Release | None) -> str:
        """What the registry says about a study whose v1 sid it does not give it."""
        if release is None:
            said, gives = f"has no identifier for {location}", "gives "
        else:
            said, gives = f"gives {location} the identifier {release.pkdb_id}", ""
        if sid in self.entries:
            said += f" and {gives}{sid} to {self.entries[sid][0]}"
        return (
            f"study.json has the identifier {sid}, but the registry {said}. "
            "Fix the registry or the sid."
        )

    def findings(self, root: Path) -> RegistryFindings:
        """Studies with two identifiers and locations without a folder below root/studies."""
        located = self._by_location
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
