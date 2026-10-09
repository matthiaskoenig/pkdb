"""GitHub issues of the studies of a pkdb_data checkout."""


def counted(count: int, noun: str, plural: str | None = None) -> str:
    """The count with its noun, singular for one: `1 issue`, `2 issues`."""
    return f"{count} {noun if count == 1 else plural or noun + 's'}"
