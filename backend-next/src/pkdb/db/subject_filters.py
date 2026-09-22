"""SQL view of inherited characteristics with closest-ancestor overrides."""

from sqlalchemy import func, literal, or_, select
from sqlalchemy.orm import aliased

from pkdb.db.models.subjects import Characteristic, Group, Individual
from pkdb.db.models.vocabulary import VocabularyEdge, VocabularyNode


def effective_characteristics(entity):
    individual = entity == "individuals"
    subject = Individual if individual else Group
    group_id = Individual.group_id if individual else Group.id
    lineage = select(
        subject.id.label("subject_id"),
        group_id.label("ancestor_id"),
        literal(1 if individual else 0).label("depth"),
    ).cte(recursive=True)
    ancestor = aliased(Group)
    lineage = lineage.union_all(
        select(lineage.c.subject_id, ancestor.parent_id, lineage.c.depth + 1)
        .join(ancestor, ancestor.id == lineage.c.ancestor_id)
        .where(ancestor.parent_id.is_not(None))
    )
    candidates = (
        select(lineage.c.subject_id, lineage.c.depth, *Characteristic.__table__.c)
        .join(Characteristic, Characteristic.group_id == lineage.c.ancestor_id)
        .where(Characteristic.origin == "normalized")
    )
    if individual:
        candidates = candidates.union_all(
            select(
                Individual.id.label("subject_id"),
                literal(0).label("depth"),
                *Characteristic.__table__.c,
            )
            .join(Characteristic, Characteristic.individual_id == Individual.id)
            .where(Characteristic.origin == "normalized")
        )
    candidates = candidates.cte()
    ranked = select(
        candidates,
        func.min(candidates.c.depth)
        .over(partition_by=(candidates.c.subject_id, candidates.c.measurement_type))
        .label("nearest"),
    ).cte()
    additive = select(VocabularyNode.sid).where(
        VocabularyNode.name.in_(["disease", "abstinence"])
    )
    return (
        select(ranked)
        .where(
            or_(
                ranked.c.depth == ranked.c.nearest,
                ranked.c.measurement_type.in_(additive),
            )
        )
        .cte()
    )


def characteristic_fields(effective):
    fields = {
        name: effective.c[name]
        for name in (
            "measurement_type",
            "substance",
            "choice",
            "value",
            "mean",
            "median",
            "minimum",
            "maximum",
            "sd",
            "se",
            "cv",
            "unit",
            "count",
        )
    }
    fields["choice_sid"] = (
        select(VocabularyNode.sid)
        .join(VocabularyEdge, VocabularyEdge.child == VocabularyNode.sid)
        .where(
            VocabularyNode.kind == "choice",
            VocabularyNode.name == effective.c.choice,
            VocabularyEdge.parent == effective.c.measurement_type,
        )
        .scalar_subquery()
    )
    return fields
