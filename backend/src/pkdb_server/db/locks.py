"""Transaction advisory locks of the current schema."""

from sqlalchemy import text

# PostgreSQL advisory locks belong to the whole database. Combining the key with
# the schema keeps the locks of different schemas apart; within one schema they
# behave as before.
SCHEMA_KEY = "hashtextextended(current_schema() || ':' || CAST(:key AS text), 0)"


def advisory_xact_lock(connection, key: int, *, shared: bool = False) -> None:
    """Hold the advisory lock of `key` in the current schema until the transaction ends.

    `connection` is a session or a connection.
    """
    function = "pg_advisory_xact_lock_shared" if shared else "pg_advisory_xact_lock"
    connection.execute(text(f"SELECT {function}({SCHEMA_KEY})"), {"key": key})
