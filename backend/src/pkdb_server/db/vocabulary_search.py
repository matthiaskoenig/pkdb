"""Substring search over the complete information of vocabulary nodes."""

from sqlalchemy import (
    bindparam,
    case,
    cast,
    exists,
    func,
    literal,
    literal_column,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from pkdb_server.db.models.vocabulary import VocabularyNode, VocabularyTerm

# Every string value of a node, its definition and its terms, except link URLs.
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


def refresh_search_documents(session: Session, sids) -> None:
    """Rebuild search documents after the nodes or their terms changed."""
    session.execute(
        text(
            f"UPDATE vocabulary_nodes AS n SET search_text = {DOCUMENT} "
            "WHERE n.sid IN :sids"
        ).bindparams(bindparam("sids", expanding=True)),
        {"sids": list(sids)},
    )


def pattern(value: str, prefix: str = "%"):
    """Case-fold like the stored documents, with LIKE wildcards taken literally."""
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return func.lower(literal(prefix + escaped + "%"))


def search_match(term: str):
    return VocabularyNode.search_text.like(pattern(term), escape="\\")


def relevance(search: str):
    """Rank exact, then prefix matches of identifiers, names, labels and synonyms."""
    query = search.strip()
    # CASE keeps the JSON cast away from plain-text synonym values.
    term = func.lower(
        case(
            (
                VocabularyTerm.kind == "label",
                cast(VocabularyTerm.value, JSONB).op("#>>")(literal_column("'{}'")),
            ),
            else_=VocabularyTerm.value,
        )
    )

    def matches(condition):
        return or_(
            condition(func.lower(VocabularyNode.sid)),
            condition(func.lower(VocabularyNode.name)),
            exists(
                select(VocabularyTerm.node_sid).where(
                    VocabularyTerm.node_sid == VocabularyNode.sid,
                    VocabularyTerm.kind.in_(["label", "synonyms"]),
                    condition(term),
                )
            ),
        )

    return case(
        (matches(lambda column: column == func.lower(literal(query))), 0),
        (
            matches(lambda column: column.like(pattern(query, prefix=""), escape="\\")),
            1,
        ),
        else_=2,
    )
