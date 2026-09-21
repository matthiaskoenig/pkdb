from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from pkdb.db.models.base import Base


class VocabularyVersion(Base):
    __tablename__ = "vocabulary_version"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    version: Mapped[str]
    __table_args__ = (CheckConstraint("id = 1", name="singleton"),)


class VocabularyNode(Base):
    __tablename__ = "vocabulary_nodes"
    sid: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    definition: Mapped[dict] = mapped_column(JSONB, default=dict)
    mass: Mapped[float | None]
    formula: Mapped[str | None]
    charge: Mapped[int | None]
    __table_args__ = (
        CheckConstraint("mass IS NULL OR mass > 0", name="positive_mass"),
    )


class VocabularyEdge(Base):
    __tablename__ = "vocabulary_edges"
    child: Mapped[str] = mapped_column(
        ForeignKey("vocabulary_nodes.sid", ondelete="CASCADE"), primary_key=True
    )
    parent: Mapped[str] = mapped_column(
        ForeignKey("vocabulary_nodes.sid"), primary_key=True
    )
    __table_args__ = (CheckConstraint("child <> parent", name="not_self"),)


class VocabularyTerm(Base):
    __tablename__ = "vocabulary_terms"
    node_sid: Mapped[str] = mapped_column(
        ForeignKey("vocabulary_nodes.sid", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(String(32), primary_key=True)
    value: Mapped[str] = mapped_column(primary_key=True)
