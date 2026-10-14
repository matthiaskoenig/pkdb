"""The stored documents of the study pages of the website.

Adds the table study_views and the texts of study.json and reference.json of
study format 2 uploads. Studies uploaded before have neither; the website shows
them on the record page until they are uploaded again.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "p008studyviews"
down_revision = "p007issueunique"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("studies", sa.Column("study_json", sa.String(), nullable=True))
    op.add_column("studies", sa.Column("reference_json", sa.String(), nullable=True))
    op.create_table(
        "study_views",
        sa.Column("study_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        # JSON keeps the order of the keys, which JSONB does not.
        sa.Column("document", postgresql.JSON(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('study', 'row', 'table', 'source')",
            name="ck_study_views_kind",
        ),
        sa.ForeignKeyConstraint(
            ["study_id"],
            ["studies.id"],
            name="fk_study_views_study_id_studies",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("study_id", "kind", "key", name="pk_study_views"),
    )


def downgrade():
    op.drop_table("study_views")
    op.drop_column("studies", "reference_json")
    op.drop_column("studies", "study_json")
