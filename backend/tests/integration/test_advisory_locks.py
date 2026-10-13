from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from pkdb_server.db.bootstrap import VOCABULARY_LOCK
from pkdb_server.db.locks import advisory_xact_lock


def test_advisory_locks_of_two_schemas_do_not_block_each_other(session_factory):
    """Two schemas of one database keep their advisory locks apart.

    While a vocabulary bootstrap in another schema holds the exclusive vocabulary
    lock, a publication here takes its shared lock; in the same schema the
    exclusive lock still waits for it.
    """
    engine = session_factory.kw["bind"]
    other = f"other_{uuid4().hex}"
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{other}"'))
    try:
        with (
            engine.connect() as theirs,
            engine.connect() as mine,
            engine.connect() as neighbour,
        ):
            theirs.execute(text(f'SET search_path TO "{other}"'))
            advisory_xact_lock(theirs, VOCABULARY_LOCK)
            mine.execute(text("SET LOCAL lock_timeout = '5s'"))
            advisory_xact_lock(mine, VOCABULARY_LOCK, shared=True)
            neighbour.execute(text("SET LOCAL lock_timeout = '200ms'"))
            with pytest.raises(OperationalError, match="lock timeout"):
                advisory_xact_lock(neighbour, VOCABULARY_LOCK)
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{other}" CASCADE'))
