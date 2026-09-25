"""PK-DB Python client and shared scientific preparation engine."""

from typing import TYPE_CHECKING

__version__ = "0.11.1"

if TYPE_CHECKING:
    from pkdb.batch import upload_many
    from pkdb.client import Client
    from pkdb.domain.vocabulary import Vocabulary
    from pkdb.preparation import PreparedBundle, prepare


def __getattr__(name):
    if name == "Vocabulary":
        from pkdb.domain.vocabulary import Vocabulary

        return Vocabulary
    if name in {"PreparedBundle", "prepare"}:
        from pkdb.preparation import PreparedBundle, prepare

        return PreparedBundle if name == "PreparedBundle" else prepare
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
