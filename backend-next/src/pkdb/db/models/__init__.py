"""Import every model so Alembic and SQLAlchemy see the complete schema."""

from pkdb.db.models import (
    files,
    interventions,
    measurements,
    saved_queries,
    studies,
    subjects,
    users,
    vocabulary,
)
from pkdb.db.models.base import Base

__all__ = [
    "Base",
    "files",
    "interventions",
    "measurements",
    "saved_queries",
    "studies",
    "subjects",
    "users",
    "vocabulary",
]
