"""Source-qualified study identity and nullable unknown group sizes."""

import re
from urllib.parse import unquote

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "p004sources"
down_revision = "p003reference"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("publications", sa.Column("id", sa.Integer(), primary_key=True))
    op.create_table(
        "publication_identifiers",
        sa.Column("namespace", sa.String(16), primary_key=True),
        sa.Column("value", sa.String(), primary_key=True),
        sa.Column(
            "publication_id",
            sa.Integer(),
            sa.ForeignKey("publications.id"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_publication_identifiers_publication_id",
        "publication_identifiers",
        ["publication_id"],
    )
    op.add_column("references", sa.Column("url", sa.String(), nullable=True))
    op.add_column("studies", sa.Column("publication_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_studies_publication_id_publications"),
        "studies",
        "publications",
        ["publication_id"],
        ["id"],
    )
    op.create_index("ix_studies_publication_id", "studies", ["publication_id"])
    op.add_column(
        "studies",
        sa.Column(
            "source_key", sa.String(255), nullable=False, server_default="pkdb.manual"
        ),
    )
    op.add_column(
        "studies",
        sa.Column(
            "acquisition",
            postgresql.JSONB(),
            nullable=False,
            server_default='{"kind":"manual_curation","source_key":"pkdb.manual"}',
        ),
    )
    bind = op.get_bind()
    seen = set()
    for row in bind.execute(
        sa.text(
            'SELECT s.id, r.sid, r.pmid, r.doi FROM studies s JOIN "references" r ON r.id=s.reference_id ORDER BY s.id'
        )
    ).mappings():
        aliases = []
        if row["pmid"]:
            aliases.append(("pmid", str(int(row["pmid"]))))
        if row["doi"]:
            doi = re.sub(
                r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)",
                "",
                row["doi"].strip(),
                flags=re.I,
            )
            aliases.append(("doi", unquote(doi).lower()))
        if not aliases:
            aliases = [("reference", row["sid"])]
        if any(alias in seen for alias in aliases):
            raise RuntimeError(
                "Duplicate manual publication identities require reconciliation before p004sources"
            )
        seen.update(aliases)
        publication = bind.scalar(
            sa.text("INSERT INTO publications DEFAULT VALUES RETURNING id")
        )
        for namespace, value in aliases:
            bind.execute(
                sa.text(
                    "INSERT INTO publication_identifiers(namespace,value,publication_id) VALUES (:namespace,:value,:publication)"
                ),
                dict(namespace=namespace, value=value, publication=publication),
            )
        bind.execute(
            sa.text("UPDATE studies SET publication_id=:publication WHERE id=:id"),
            dict(publication=publication, id=row["id"]),
        )
    op.create_unique_constraint(
        op.f("uq_studies_publication_id_source_key"),
        "studies",
        ["publication_id", "source_key"],
    )
    op.alter_column("subjects", "count", existing_type=sa.Integer(), nullable=True)


def downgrade():
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS(SELECT 1 FROM subjects WHERE count IS NULL)")
    ):
        raise RuntimeError(
            "Cannot downgrade unknown group sizes without inventing counts"
        )
    op.alter_column("subjects", "count", existing_type=sa.Integer(), nullable=False)
    op.drop_constraint(
        op.f("uq_studies_publication_id_source_key"), "studies", type_="unique"
    )
    op.drop_column("studies", "acquisition")
    op.drop_column("studies", "source_key")
    op.drop_index("ix_studies_publication_id", table_name="studies")
    op.drop_constraint(
        op.f("fk_studies_publication_id_publications"), "studies", type_="foreignkey"
    )
    op.drop_column("studies", "publication_id")
    op.drop_column("references", "url")
    op.drop_table("publication_identifiers")
    op.drop_table("publications")
