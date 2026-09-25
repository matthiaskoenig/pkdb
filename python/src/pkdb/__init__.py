"""PK-DB Python client and shared scientific preparation engine."""

from typing import TYPE_CHECKING

__version__ = "0.11.1"

from pkdb.domain.vocabulary import Vocabulary
from pkdb.preparation import PreparedBundle, prepare

if TYPE_CHECKING:
    from pkdb.batch import upload_many
    from pkdb.client import Client


def __getattr__(name):
    if name == "upload_many":
        from pkdb.batch import upload_many

        return upload_many
    if name == "Client":
        from pkdb.client import Client

        return Client
    raise AttributeError(name)


__all__ = [
    "Client",
    "PreparedBundle",
    "Vocabulary",
    "__version__",
    "prepare",
    "upload_many",
]
