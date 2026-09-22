"""Each factory call creates an independent transaction/session."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def make_session_factory(database_url: str) -> sessionmaker[Session]:
    engine = create_engine(database_url, pool_pre_ping=True)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        raise ValueError("PK-DB requires PostgreSQL")
    return sessionmaker(engine, expire_on_commit=False)
