"""Scan the format 2 studies of a checkout for release blocks and issue numbers."""

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from pkdb.repository import STUDIES, location, study_folders

REGISTRY_FILE = "study_identifiers.json"
REGISTRY_PATH = f"{STUDIES}/{REGISTRY_FILE}"
PKDB_ID = re.compile(r"PKDB([0-9]{5})")


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


def identifier_number(pkdb_id: str) -> int:
    """The number of a PKDB identifier such as `PKDB00001`."""
    match = PKDB_ID.fullmatch(pkdb_id)
    if match is None:
        raise ValueError(f"{pkdb_id!r} is not a PKDB identifier such as PKDB00001")
    return int(match[1])


def read_registry_file(root: Path) -> dict[str, str] | None:
    """The identifier to location mapping of `studies/study_identifiers.json`, or None.

    Raises a ValueError that names the file and the problem.
    """
    path = Path(root) / STUDIES / REGISTRY_FILE
    if not path.is_file():
        return None
    try:
        content = path.read_bytes()
    except OSError as error:
        raise ValueError(f"{REGISTRY_PATH}: cannot be read as JSON: {error}") from None
    return registry_locations(content)


def registry_locations(content: bytes) -> dict[str, str]:
    """The identifier to location mapping of the content of the registry file.

    Raises a ValueError that names the file and the problem.
    """
    try:
        data = json.loads(content.decode("utf-8"))
    except ValueError as error:
        raise ValueError(f"{REGISTRY_PATH}: cannot be read as JSON: {error}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{REGISTRY_PATH}: must be a JSON object")
    locations = {}
    for key, value in data.items():
        try:
            identifier_number(key)
        except ValueError as error:
            raise ValueError(f"{REGISTRY_PATH}: {error}") from None
        if not (isinstance(value, list) and value and isinstance(value[0], str)):
            raise ValueError(
                f"{REGISTRY_PATH}: {key} must map to [location, date], not {value!r}"
            )
        locations[key] = value[0]
    return locations


def registry_problems(scan: Scan, root: Path) -> list[str]:
    """Release blocks that the registry file assigns to another location, or its read error."""
    try:
        registered = read_registry_file(root)
    except ValueError as error:
        return [str(error)]
    return sorted(
        f"{item.pkdb_id} is the identifier of {item.location}, but {REGISTRY_FILE} gives it to {registered[item.pkdb_id]}"
        for item in scan.released
        if registered and registered.get(item.pkdb_id, item.location) != item.location
    )


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
    ids = [item.pkdb_id for item in scan.released]
    ids += read_registry_file(root) or {}
    return max((identifier_number(pkdb_id) for pkdb_id in ids), default=0) + 1
