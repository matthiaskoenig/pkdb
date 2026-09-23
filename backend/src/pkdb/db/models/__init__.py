"""Import every model so Alembic and SQLAlchemy see the complete schema."""

from pkdb.db.models import (
    audit,
    credentials,
    drafts,
    files,
    interventions,
    limits,
    measurements,
    saved_queries,
    security,
    studies,
    subjects,
    users,
    vocabulary,
)
from pkdb.db.models.base import Base

__all__ = [
    "Base",
    "audit",
    "credentials",
    "drafts",
    "files",
    "interventions",
    "limits",
    "measurements",
    "saved_queries",
    "security",
    "studies",
    "subjects",
    "users",
    "vocabulary",
]
