"""Rules for the `<substance>/<name>` location of a study."""

import re
from pathlib import Path

from pkdb.studyformat.layout import RESERVED_NAMES

NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
MAX_STUDY_NAME = 24
_RULE = "letters, digits, '_' and '-', starting with a letter or a digit"


def parse_location(value: str) -> tuple[str, str]:
    """Split `<substance>/<name>` and check both parts."""
    parts = value.split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"{value!r} is not <substance>/<name>")
    substance, name = parts
    for kind, part in (("substance", substance), ("name", name)):
        if not NAME.fullmatch(part):
            raise ValueError(f"The {kind} {part!r} must use {_RULE}")
    if len(name) > MAX_STUDY_NAME:
        raise ValueError(
            f"The name {name!r} is longer than {MAX_STUDY_NAME} characters"
        )
    if name in RESERVED_NAMES:
        raise ValueError(f"The name {name!r} is reserved")
    return substance, name


def case_twin(folder: Path, name: str) -> str | None:
    """The entry of `folder` whose name differs from `name` only in case, or None.

    Such names collide on the file systems of macOS and Windows.
    """
    if not folder.is_dir():
        return None
    for entry in folder.iterdir():
        if entry.name != name and entry.name.casefold() == name.casefold():
            return entry.name
    return None
