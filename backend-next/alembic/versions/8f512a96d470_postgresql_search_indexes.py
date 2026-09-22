"""Index deterministic PostgreSQL full-text expressions; no asynchronous indexing."""

import sqlalchemy as sa

from alembic import op

revision = "8f512a96d470"
down_revision = "d37e5b126084"
branch_labels = None
depends_on = None

INDEXES = {
    "vocabulary_nodes": ("sid", "name"),
    "vocabulary_terms": ("value",),
    "studies": ("sid", "name"),
    "references": ("sid", "name", "pmid", "title", "abstract"),
}


def upgrade():
    for table, columns in INDEXES.items():
        document = " || ' ' || ".join(f"coalesce({column}, '')" for column in columns)
        op.create_index(
            f"ix_{table}_search",
            table,
            [sa.text(f"to_tsvector('simple', {document})")],
            postgresql_using="gin",
        )


def downgrade():
    for table in reversed(INDEXES):
        op.drop_index(f"ix_{table}_search", table_name=table)
