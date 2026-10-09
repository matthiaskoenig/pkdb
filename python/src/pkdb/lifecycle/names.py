"""Rules for the `<substance>/<name>` location of a study."""

import re
from pathlib import Path

from pkdb.studyformat.layout import RESERVED_NAMES
from pkdb.studyformat.tables import JSON_FILES, TABLES

NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
MAX_STUDY_NAME = 24
_RULE = "letters, digits, '_' and '-', starting with a letter or a digit"
# Besides the names that PK-DB and the per-source tables reserve, a new name
# is none of the fixed files of a study, such as study.json or subjects.tsv,
# which would look like files named after the study.
_FIXED_FILES = {Path(file).stem for file in JSON_FILES} | {
    spec.kind for spec in TABLES.values() if not spec.per_source
}
_RESERVED = frozenset(name.casefold() for name in RESERVED_NAMES | _FIXED_FILES)


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
    # Ignoring case: Excel sheet names are case-insensitive, so the raw table
    # `Outputs_Tab1` would collide with the table `outputs_Tab1`.
    if name.casefold() in _RESERVED:
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
