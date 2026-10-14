"""The stored documents of the study page of the website (#963)."""

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from pkdb_server.db.models.base import Base


class StudyView(Base):
    """A document of the study page, built by `pkdb.studyformat.views` at upload.

    `kind` is `study` (the page) or `row` (its row in the list of studies), both with the key
    "", `table` with the file of the table as key, or `source` with the source as key.
    `version` is the `VIEW_VERSION` that built it.
    """

    __tablename__ = "study_views"
    study_id: Mapped[int] = mapped_column(
        ForeignKey("studies.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(String(8), primary_key=True)
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    version: Mapped[int]
    document: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (
        CheckConstraint("kind IN ('study', 'row', 'table', 'source')", name="kind"),
    )
