"""Substring search over the complete information of vocabulary nodes.

Database triggers from migration p005vocabsearch keep search_text current.
"""

from sqlalchemy import (
    case,
    cast,
    exists,
    func,
    literal,
    literal_column,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB

from pkdb_server.db.models.vocabulary import VocabularyNode, VocabularyTerm


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
