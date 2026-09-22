"""Access to important environment variables.

The PK-DB instance and the credentials are provided via the environment
variables `API_BASE`, `USER` and `PASSWORD`, see `.env.template`. They are read
when they are needed and not on import, so the package can be imported without
them.
"""

import os
from dataclasses import dataclass
from typing import Final
from urllib.parse import urljoin

DEFAULT_USER_PASSWORD: Final = "pkdb"


class EnvironmentNotInitializedError(RuntimeError):
    """Environment variables for the connection to PK-DB are missing."""


@dataclass(frozen=True)
class Environment:
    """Connection information for a PK-DB instance."""

    api_base: str
    user: str
    password: str

    @property
    def api_url(self) -> str:
        """Url of the API of the PK-DB instance."""
        return urljoin(self.api_base, "api/v1")


def get_environment() -> Environment:
    """Read the connection information from the environment variables.

    Raises:
        EnvironmentNotInitializedError: if a variable is not set
    """
    try:
        return Environment(
            # fix terminal slash
            api_base=os.environ["API_BASE"].removesuffix("/"),
            user=os.environ["USER"],
            password=os.environ["PASSWORD"],
        )
    except KeyError as err:
        raise EnvironmentNotInitializedError(
            f"Environment variable {err} has not been initialized. "
            "1. add authentication credentials; and "
            "2. run `set -a && source .env.local`"
        ) from err
