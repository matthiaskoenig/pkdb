"""Unique issue numbers of studies.

A GitHub issue belongs to one study, so an upload of a moved study can take over
the stored study by its issue number. The upgrade refuses to run while stored
studies share an issue number and names them.
"""

import sqlalchemy as sa

from alembic import op

revision = "p007issueunique"
down_revision = "p006studyformat"
branch_labels = None
depends_on = None


def upgrade():
    shared = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT issue, string_agg(sid, ', ' ORDER BY sid) FROM studies "
                "WHERE issue IS NOT NULL GROUP BY issue HAVING count(*) > 1 "
                "ORDER BY issue"
            )
        )
        .all()
    )
    if shared:
        names = "; ".join(f"#{issue}: {sids}" for issue, sids in shared)
        raise RuntimeError(
            "Studies share an issue number; give each study its own issue first "
            f"({names})"
        )
    op.create_index(
        "uq_studies_issue",
        "studies",
        ["issue"],
        unique=True,
        postgresql_where=sa.text("issue IS NOT NULL"),
    )


def downgrade():
    op.drop_index("uq_studies_issue", table_name="studies")
