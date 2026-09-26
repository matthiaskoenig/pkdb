from datetime import date as Date

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy import Identity as AutoIdentity
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from pkdb_server.db.models.base import Base, Identity, Timestamped
from pkdb_server.db.textsearch import vector


class Publication(Identity, Base):
    __tablename__ = "publications"


class PublicationIdentifier(Base):
    __tablename__ = "publication_identifiers"
    namespace: Mapped[str] = mapped_column(String(16), primary_key=True)
    value: Mapped[str] = mapped_column(primary_key=True)
    publication_id: Mapped[int] = mapped_column(
        ForeignKey("publications.id"), index=True
    )


class Reference(Identity, Base):
    __tablename__ = "references"
    sid: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str]
    pmid: Mapped[str | None]
    doi: Mapped[str | None]
    url: Mapped[str | None]
    title: Mapped[str | None]
    abstract: Mapped[str | None]
    publication_date: Mapped[str | None] = mapped_column(String(10))
    provenance: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    journal: Mapped[str | None]
    date: Mapped[Date | None]


class Author(Base):
    __tablename__ = "reference_authors"
    id: Mapped[int] = mapped_column(AutoIdentity(), unique=True)
    reference_id: Mapped[int] = mapped_column(
        ForeignKey("references.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(default="")
    last_name: Mapped[str]
    organization: Mapped[str | None]
    __table_args__ = (CheckConstraint("position >= 0", name="position"),)


class Study(Identity, Timestamped, Base):
    __tablename__ = "studies"
    publication_id: Mapped[int | None] = mapped_column(
        ForeignKey("publications.id"), index=True
    )
    source_key: Mapped[str] = mapped_column(
        String(255), default="pkdb.manual", server_default="pkdb.manual"
    )
    acquisition: Mapped[dict] = mapped_column(
        JSONB,
        default=lambda: {"kind": "manual_curation", "source_key": "pkdb.manual"},
        server_default='{"kind":"manual_curation","source_key":"pkdb.manual"}',
    )
    sid: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(index=True)
    date: Mapped[Date | None]
    access: Mapped[str] = mapped_column(String(16))
    licence: Mapped[str] = mapped_column(String(16))
    creator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    reference_id: Mapped[int | None] = mapped_column(
        ForeignKey("references.id"), unique=True
    )
    source_digest: Mapped[str | None] = mapped_column(String(64))
    vocabulary_version: Mapped[str | None]
    processing_version: Mapped[str | None]
    validation_report: Mapped[dict] = mapped_column(JSONB, default=dict)
    source_manifest: Mapped[dict] = mapped_column(JSONB, default=dict)
    __table_args__ = (
        UniqueConstraint("publication_id", "source_key"),
        CheckConstraint("access IN ('public', 'private')", name="access"),
        CheckConstraint("licence IN ('open', 'closed')", name="licence"),
        CheckConstraint("length(sid) > 0", name="sid"),
    )


class StudyUser(Base):
    __tablename__ = "study_users"
    study_id: Mapped[int] = mapped_column(
        ForeignKey("studies.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), primary_key=True)
    rating: Mapped[float | None]
    __table_args__ = (
        CheckConstraint("role IN ('curator', 'collaborator')", name="role"),
        CheckConstraint(
            "rating IS NULL OR (rating >= 0 AND rating <= 5)", name="rating"
        ),
    )


class StudyGrant(Base):
    """Effective access, independent of replaceable contributor attribution."""

    __tablename__ = "study_grants"
    study_id: Mapped[int] = mapped_column(
        ForeignKey("studies.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), primary_key=True)
    __table_args__ = (CheckConstraint("role = 'curator'", name="role"),)


class Note(Identity, Base):
    __tablename__ = "notes"
    study_id: Mapped[int] = mapped_column(
        ForeignKey("studies.id", ondelete="CASCADE"), index=True
    )
    record_key: Mapped[str]
    kind: Mapped[str] = mapped_column(String(16))
    position: Mapped[int]
    text: Mapped[str]
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


Base.metadata.tables["studies"].append_constraint(
    Index("ix_studies_search", vector([Study.sid, Study.name]), postgresql_using="gin")
)

Base.metadata.tables["references"].append_constraint(
    Index(
        "ix_references_search",
        vector(
            [
                Reference.sid,
                Reference.name,
                Reference.pmid,
                Reference.title,
                Reference.abstract,
            ]
        ),
        postgresql_using="gin",
    )
)
