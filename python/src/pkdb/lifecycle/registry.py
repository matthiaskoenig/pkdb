"""Scan the format 2 studies of a checkout for release blocks and issue numbers."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from pkdb.repository import STUDIES, location, study_folders

REGISTRY_FILE = "study_identifiers.json"


@dataclass(frozen=True)
class Released:
    pkdb_id: str
    location: str
    date: date


@dataclass(frozen=True)
class Scan:
    released: list[Released]
    issues: dict[int, list[str]]
    errors: list[str]


def identifier(number: int) -> str:
    return f"PKDB{number:05d}"


def scan(root: Path) -> Scan:
    """The release blocks and issue numbers of every format 2 study."""
    from pkdb.studyformat.metadata import MetadataError, read_metadata
    from pkdb.studyformat.validation import is_v2_folder

    released: list[Released] = []
    issues: dict[int, list[str]] = defaultdict(list)
    errors: list[str] = []
    for folder in study_folders(root):
        if not is_v2_folder(folder):
            continue
        where = location(folder)
        try:
            metadata = read_metadata(folder).metadata
        except (MetadataError, OSError) as error:
            errors.append(f"{where}: {error}")
            continue
        if metadata.release is not None:
            released.append(
                Released(metadata.release.pkdb_id, where, metadata.release.date)
            )
        if metadata.issue is not None:
            issues[metadata.issue].append(where)
    released.sort(key=lambda item: (item.pkdb_id, item.location))
    return Scan(released, dict(issues), errors)


def duplicates(scan: Scan) -> list[str]:
    """Identifiers and issue numbers shared by several studies, sorted."""
    by_id: dict[str, list[str]] = defaultdict(list)
    for item in scan.released:
        by_id[item.pkdb_id].append(item.location)
    problems = [
        f"{pkdb_id} is the identifier of several studies: {', '.join(sorted(places))}"
        for pkdb_id, places in by_id.items()
        if len(places) > 1
    ]
    problems += [
        f"Issue #{number} is named by several studies: {', '.join(sorted(places))}"
        for number, places in scan.issues.items()
        if len(places) > 1
    ]
    return sorted(problems)


def next_identifier(scan: Scan, root: Path) -> int:
    """One more than the largest identifier number in the studies and the registry file."""
    from pkdb.migration.registry import Registry

    path = Path(root) / STUDIES / REGISTRY_FILE
    ids = [item.pkdb_id for item in scan.released]
    if path.is_file():
        ids += Registry.read(path).identifiers
    return max((int(pkdb_id[4:]) for pkdb_id in ids), default=0) + 1
