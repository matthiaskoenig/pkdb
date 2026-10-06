"""Who writes study files: the PK-DB user and, for AI agents, the agent."""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass

USER_PATTERN = re.compile(r"^\S{1,255}$")


class IdentityError(ValueError):
    """No usable user was given."""


@dataclass(frozen=True)
class Author:
    """The user responsible for a write and the AI agent that made it, if any."""

    user: str
    agent: str | None = None


def author_from(
    user: str | None, agent: str | None, *, environ: Mapping[str, str] = os.environ
) -> Author:
    """The author from `--user`/`--agent` or PKDB_USER/PKDB_AGENT."""
    user = user or environ.get("PKDB_USER") or ""
    if not USER_PATTERN.fullmatch(user):
        raise IdentityError(
            "A PK-DB user name is required: pass --user or set PKDB_USER"
            if not user
            else f"{user!r} is not a PK-DB user name"
        )
    return Author(user, agent or environ.get("PKDB_AGENT") or None)
