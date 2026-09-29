"""Search vocabulary nodes by substrings of their complete information."""

import sqlalchemy as sa

from alembic import op

revision = "p005vocabsearch"
down_revision = "p004sources"
branch_labels = None
depends_on = None

# Every string value of a node, its definition and its terms, except link URLs.
# Triggers keep the document current for every writer, including direct inserts.
FUNCTIONS = """
CREATE FUNCTION vocabulary_search_document(
    item_sid text, item_name text, item_kind text, item_formula text,
    item_definition jsonb
) RETURNS text LANGUAGE sql STABLE AS $$
SELECT lower(concat_ws(' ',
    item_sid, item_name, item_kind, item_formula,
    (SELECT string_agg(leaf #>> '{}', ' ')
     FROM jsonb_path_query(
         item_definition, 'strict $.** ? (@.type() == "string")'
     ) AS leaf),
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
     WHERE t.node_sid = item_sid)
))
$$;

CREATE FUNCTION vocabulary_node_search() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.search_text := vocabulary_search_document(
        NEW.sid, NEW.name, NEW.kind, NEW.formula, NEW.definition
    );
    RETURN NEW;
END
$$;

CREATE FUNCTION vocabulary_terms_search() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        UPDATE vocabulary_nodes AS n SET search_text = vocabulary_search_document(
            n.sid, n.name, n.kind, n.formula, n.definition
        ) WHERE n.sid IN (SELECT node_sid FROM changed_before);
    ELSIF TG_OP = 'INSERT' THEN
        UPDATE vocabulary_nodes AS n SET search_text = vocabulary_search_document(
            n.sid, n.name, n.kind, n.formula, n.definition
        ) WHERE n.sid IN (SELECT node_sid FROM changed_after);
    ELSE
        UPDATE vocabulary_nodes AS n SET search_text = vocabulary_search_document(
            n.sid, n.name, n.kind, n.formula, n.definition
        ) WHERE n.sid IN (
            SELECT node_sid FROM changed_before
            UNION SELECT node_sid FROM changed_after
        );
    END IF;
    RETURN NULL;
END
$$;

CREATE TRIGGER vocabulary_node_search
BEFORE INSERT OR UPDATE OF sid, name, kind, formula, definition
ON vocabulary_nodes FOR EACH ROW EXECUTE FUNCTION vocabulary_node_search();

CREATE TRIGGER vocabulary_terms_search_insert
AFTER INSERT ON vocabulary_terms REFERENCING NEW TABLE AS changed_after
FOR EACH STATEMENT EXECUTE FUNCTION vocabulary_terms_search();

CREATE TRIGGER vocabulary_terms_search_update
AFTER UPDATE ON vocabulary_terms
REFERENCING OLD TABLE AS changed_before NEW TABLE AS changed_after
FOR EACH STATEMENT EXECUTE FUNCTION vocabulary_terms_search();

CREATE TRIGGER vocabulary_terms_search_delete
AFTER DELETE ON vocabulary_terms REFERENCING OLD TABLE AS changed_before
FOR EACH STATEMENT EXECUTE FUNCTION vocabulary_terms_search();
"""


def upgrade():
    op.add_column(
        "vocabulary_nodes",
        sa.Column("search_text", sa.String(), nullable=False, server_default=""),
    )
    op.execute(FUNCTIONS)
    op.execute(
        "UPDATE vocabulary_nodes AS n SET search_text = vocabulary_search_document("
        "n.sid, n.name, n.kind, n.formula, n.definition)"
    )


def downgrade():
    for trigger, table in [
        ("vocabulary_terms_search_delete", "vocabulary_terms"),
        ("vocabulary_terms_search_update", "vocabulary_terms"),
        ("vocabulary_terms_search_insert", "vocabulary_terms"),
        ("vocabulary_node_search", "vocabulary_nodes"),
    ]:
        op.execute(f"DROP TRIGGER {trigger} ON {table}")
    op.execute("DROP FUNCTION vocabulary_terms_search()")
    op.execute("DROP FUNCTION vocabulary_node_search()")
    op.execute(
        "DROP FUNCTION vocabulary_search_document(text, text, text, text, jsonb)"
    )
    op.drop_column("vocabulary_nodes", "search_text")
