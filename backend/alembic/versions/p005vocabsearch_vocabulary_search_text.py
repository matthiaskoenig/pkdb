"""Search vocabulary nodes by substrings of their complete information."""

import sqlalchemy as sa

from alembic import op

revision = "p005vocabsearch"
down_revision = "p004sources"
branch_labels = None
depends_on = None

# Frozen copy of pkdb_server.db.vocabulary_search.DOCUMENT at this revision.
DOCUMENT = """
lower(concat_ws(' ',
    n.sid, n.name, n.kind, n.formula,
    (SELECT string_agg(leaf #>> '{}', ' ')
     FROM jsonb_path_query(n.definition, 'strict $.** ? (@.type() == "string")')
        AS leaf),
    (SELECT string_agg(part, ' ' ORDER BY t.kind, t.value, part)
     FROM vocabulary_terms AS t
     CROSS JOIN LATERAL (
         SELECT CASE WHEN t.kind = 'synonyms' THEN to_jsonb(t.value)
                ELSE t.value::jsonb END AS document
     ) AS parsed
     CROSS JOIN LATERAL (
         SELECT parsed.document #>> '{}'
         WHERE jsonb_typeof(parsed.document) = 'string'
         UNION ALL
         SELECT field.value #>> '{}'
         FROM jsonb_each(
             CASE WHEN jsonb_typeof(parsed.document) = 'object'
             THEN parsed.document ELSE '{}'::jsonb END
         ) AS field
         WHERE field.key <> 'url' AND jsonb_typeof(field.value) = 'string'
     ) AS parts(part)
     WHERE t.node_sid = n.sid)
))
"""


def upgrade():
    op.add_column(
        "vocabulary_nodes",
        sa.Column("search_text", sa.String(), nullable=False, server_default=""),
    )
    op.execute(f"UPDATE vocabulary_nodes AS n SET search_text = {DOCUMENT}")


def downgrade():
    op.drop_column("vocabulary_nodes", "search_text")
