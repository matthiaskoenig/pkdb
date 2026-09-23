"""Explicit schema operations; application startup never runs migrations."""

import os

from sqlalchemy import create_engine, pool

from alembic import context
from pkdb_server.db.models import Base

config = context.config
url = config.get_main_option("sqlalchemy.url") or os.environ.get("PKDB_DATABASE_URL")
if not url:
    raise RuntimeError("PKDB_DATABASE_URL is required for migrations")
if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
