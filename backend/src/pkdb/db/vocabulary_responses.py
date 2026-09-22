"""Vocabulary responses assembled with bounded batched relationship reads."""

import json
from collections import defaultdict

from sqlalchemy import select

from pkdb.db.models.vocabulary import VocabularyEdge, VocabularyNode, VocabularyTerm
from pkdb.schemas.responses import VocabularyResponse


def vocabulary_responses(session, rows):
    if not rows:
        return []
    ids = {row.sid for row in rows}
    edges = list(
        session.scalars(
            select(VocabularyEdge)
            .where(VocabularyEdge.child.in_(ids) | VocabularyEdge.parent.in_(ids))
            .order_by(VocabularyEdge.parent, VocabularyEdge.child)
        )
    )
    related_ids = ids | {edge.parent for edge in edges} | {edge.child for edge in edges}
    nodes = {
        row.sid: row
        for row in session.scalars(
            select(VocabularyNode).where(VocabularyNode.sid.in_(related_ids))
        )
    }
    terms = defaultdict(lambda: defaultdict(list))
    for term in session.scalars(
        select(VocabularyTerm)
        .where(VocabularyTerm.node_sid.in_(related_ids))
        .order_by(VocabularyTerm.kind, VocabularyTerm.value)
    ):
        terms[term.node_sid][term.kind].append(
            term.value if term.kind == "synonyms" else json.loads(term.value)
        )
    parents, children = defaultdict(list), defaultdict(list)
    for edge in edges:
        parents[edge.child].append(edge.parent)
        children[edge.parent].append(edge.child)

    def scalar(sid, name, default):
        return next(iter(terms[sid][name]), default)

    def summary(sid):
        node = nodes[sid]
        return {"sid": sid, "name": node.name, "label": scalar(sid, "label", node.name)}

    result = []
    for row in rows:
        measurement = None
        substance = None
        if row.kind == "measurement":
            allowed_choices = set(row.definition.get("choices", []))
            measurement = {
                "units": row.definition.get("units", []),
                "choices": [
                    summary(sid)
                    for sid in children[row.sid]
                    if nodes[sid].kind == "choice"
                    and nodes[sid].name in allowed_choices
                ],
            }
        if row.kind == "substance":
            substance = {
                "mass": row.mass,
                "charge": row.charge,
                "formula": row.formula,
            }
        result.append(
            VocabularyResponse.model_validate(
                {
                    **summary(row.sid),
                    "deprecated": scalar(row.sid, "deprecated", False),
                    "ntype": "measurement_type"
                    if row.kind == "measurement"
                    else row.kind,
                    "dtype": scalar(
                        row.sid, "dtype", row.definition.get("dtype", "undefined")
                    ),
                    "description": scalar(row.sid, "description", ""),
                    "synonyms": terms[row.sid]["synonyms"],
                    "parents": [summary(sid) for sid in parents[row.sid]],
                    "annotations": terms[row.sid]["annotations"],
                    "xrefs": terms[row.sid]["xrefs"],
                    "measurement_type": measurement,
                    "substance": substance,
                }
            ).model_dump()
        )
    return result
