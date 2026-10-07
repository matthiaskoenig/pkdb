"""Who writes study files: the PK-DB user and, for AI agents, the agent.

The CLI and the curation app resolve the author the same way (curation app design D5 and 7.4):
the account of the API key when a server confirms it, otherwise the configured user. A key of
another account than the configured user is refused.
"""

import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass

USER_PATTERN = re.compile(r"^\S{1,255}$")
CLI_HINT = "pass --user or set PKDB_USER"
# The account check must not hold up a write for long when the server is slow.
CHECK_SECONDS = 5


class IdentityError(ValueError):
    """No usable user was given."""


class UserMismatch(IdentityError):
    """The API key belongs to another PK-DB account than the configured user."""

    code = "user_mismatch"


@dataclass(frozen=True)
class Author:
    """The user responsible for a write and the AI agent that made it, if any."""

    user: str
    agent: str | None = None


def author_from(
    user: str | None,
    agent: str | None,
    *,
    environ: Mapping[str, str] = os.environ,
    hint: str = CLI_HINT,
) -> Author:
    """The author from `--user`/`--agent` or PKDB_USER/PKDB_AGENT, without a server check."""
    user = user or environ.get("PKDB_USER") or ""
    if not USER_PATTERN.fullmatch(user):
        raise IdentityError(
            f"A PK-DB user name is required: {hint}"
            if not user
            else f"{user!r} is not a PK-DB user name; {hint}"
        )
    return Author(user, agent or environ.get("PKDB_AGENT") or None)


def check_account(endpoint: str, api_key: str, user: str | None) -> str | None:
    """The account of an API key as the server reports it, or None when it cannot tell.

    UserMismatch when the key belongs to another account than `user`. A server that cannot be
    reached or that refuses the request gives None, so that the configured user writes.
    """
    import httpx2

    from pkdb.client import Client
    from pkdb.errors import ClientError

    transport = httpx2.Client(
        timeout=httpx2.Timeout(CHECK_SECONDS), follow_redirects=False
    )
    try:
        with Client(
            endpoint, api_key=api_key, user=user or "", transport=transport
        ) as client:
            return client.identity().username
    except ClientError as error:
        if error.code == UserMismatch.code:
            raise UserMismatch(str(error)) from None
        return None
    except OSError, ValueError:
        return None
    finally:
        transport.close()


def resolve_author(
    user: str | None,
    agent: str | None,
    *,
    endpoint: str | None = None,
    api_key: str | None = None,
    offline: bool = False,
    environ: Mapping[str, str] = os.environ,
    check: Callable[[str, str, str | None], str | None] | None = None,
    hint: str = CLI_HINT,
) -> Author:
    """The author of a write: the checked account of the API key, else the configured user.

    The key is checked with `check(endpoint, api_key, user)`, `check_account` by default, only
    when an API key and an endpoint are given and not `offline`. UserMismatch when the key
    belongs to another account; IdentityError without a usable user.
    """
    user = user or environ.get("PKDB_USER") or ""
    if api_key and endpoint and not offline:
        account = (check or check_account)(endpoint, api_key, user or None)
        if account:
            user = account
    return author_from(user, agent, environ=environ, hint=hint)
