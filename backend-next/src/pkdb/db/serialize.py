"""Page-scoped batched loading; response serialization never performs lazy SQL."""

import json
from collections import defaultdict

from sqlalchemy import select

from pkdb.db.models.interventions import Intervention
from pkdb.db.models.measurements import MeasurementIntervention
from pkdb.db.models.studies import Study
from pkdb.db.models.subjects import Group, Individual
from pkdb.db.models.vocabulary import VocabularyEdge, VocabularyNode, VocabularyTerm
from pkdb.schemas.responses import OutputResponse


class VocabularyResponses:
    def __init__(self, session, records):
        sids = {
            getattr(row, field, None)
            for row in records
            for field in (
                "measurement_type",
                "calculation_type",
                "substance",
                "tissue",
                "method",
                "route",
                "form",
                "application",
            )
        }
        choices = {row.choice for row in records if row.choice is not None}
        choice_rows = (
            session.execute(
                select(VocabularyNode, VocabularyEdge.parent)
                .join(VocabularyEdge, VocabularyNode.sid == VocabularyEdge.child)
                .where(
                    VocabularyNode.kind == "choice",
                    VocabularyNode.name.in_(choices),
                    VocabularyEdge.parent.in_(sids),
                )
            ).all()
            if choices
            else []
        )
        self.choices = {(parent, row.name): row.sid for row, parent in choice_rows}
        sids.update(self.choices.values())
        nodes = list(
            session.scalars(select(VocabularyNode).where(VocabularyNode.sid.in_(sids)))
        )
        labels = {
            row.node_sid: json.loads(row.value)
            for row in session.scalars(
                select(VocabularyTerm).where(
                    VocabularyTerm.node_sid.in_(sids), VocabularyTerm.kind == "label"
                )
            )
        }
        self.nodes = {
            row.sid: {
                "sid": row.sid,
                "name": row.name,
                "label": labels.get(row.sid) or row.name,
            }
            for row in nodes
        }

    def node(self, sid):
        return self.nodes.get(sid)

    def science(self, row):
        result = {
            name: getattr(row, name)
            for name in ("value", "mean", "median", "sd", "se", "cv", "unit")
        }
        result.update(pk=row.id, min=row.minimum, max=row.maximum)
        result.update(
            {
                name: self.node(getattr(row, name))
                for name in ("measurement_type", "substance", "calculation_type")
            }
        )
        result["choice"] = self.node(
            self.choices.get((row.measurement_type, row.choice))
        )
        return result


def output_responses(session, rows):
    if not rows:
        return []
    vocabulary = VocabularyResponses(session, rows)
    studies = {
        row.id: {"sid": row.sid, "name": row.name}
        for row in session.scalars(
            select(Study).where(Study.id.in_({r.study_id for r in rows}))
        )
    }
    groups = {
        row.id: {"pk": row.id, "name": row.name, "count": row.count}
        for row in session.scalars(
            select(Group).where(
                Group.id.in_({r.group_id for r in rows if r.group_id is not None})
            )
        )
    }
    individuals = {
        row.id: {"pk": row.id, "name": row.name}
        for row in session.scalars(
            select(Individual).where(
                Individual.id.in_(
                    {r.individual_id for r in rows if r.individual_id is not None}
                )
            )
        )
    }
    interventions = defaultdict(list)
    for association, intervention in session.execute(
        select(MeasurementIntervention, Intervention)
        .join(Intervention, MeasurementIntervention.intervention_id == Intervention.id)
        .where(MeasurementIntervention.measurement_id.in_([r.id for r in rows]))
        .order_by(MeasurementIntervention.position)
    ):
        interventions[association.measurement_id].append(
            {"pk": intervention.id, "name": intervention.name}
        )
    return [
        OutputResponse(
            **vocabulary.science(row),
            normed=row.origin == "normalized",
            calculated=row.calculated,
            tissue=vocabulary.node(row.tissue),
            method=vocabulary.node(row.method),
            label=row.label,
            output_type="" if row.calculated else row.output_type,
            study=studies[row.study_id],
            group=groups.get(row.group_id),
            individual=individuals.get(row.individual_id),
            interventions=interventions[row.id],
            time=row.time,
            time_unit=row.time_unit,
        ).model_dump()
        for row in rows
    ]


def subject_responses(session, rows, individual=False):
    from pkdb.db.models.subjects import Characteristic
    from pkdb.schemas.responses import GroupResponse, IndividualResponse

    if not rows:
        return []
    ids = {row.group_id if individual else row.id for row in rows}
    ancestors = (
        select(Group.id, Group.parent_id)
        .where(Group.id.in_(ids))
        .cte("ancestors", recursive=True)
    )
    ancestors = ancestors.union(
        select(Group.id, Group.parent_id).join(
            ancestors, Group.id == ancestors.c.parent_id
        )
    )
    groups = {
        row.id: row
        for row in session.scalars(
            select(Group).join(ancestors, Group.id == ancestors.c.id)
        )
    }
    individual_ids = [row.id for row in rows] if individual else []
    characteristics = list(
        session.scalars(
            select(Characteristic)
            .where(
                (
                    Characteristic.group_id.in_(groups)
                    | Characteristic.individual_id.in_(individual_ids)
                ),
                Characteristic.origin == "normalized",
            )
            .order_by(Characteristic.id)
        )
    )
    vocabulary = VocabularyResponses(session, characteristics)
    by_group, by_individual = defaultdict(list), defaultdict(list)
    for row in characteristics:
        if row.group_id is not None:
            by_group[row.group_id].append(row)
        else:
            by_individual[row.individual_id].append(row)
    additive = {
        sid
        for sid, node in vocabulary.nodes.items()
        if node["name"] in {"disease", "abstinence"}
    }

    def combine(local, inherited):
        overridden = {row.measurement_type for row in local} - additive
        return sorted(
            [
                *local,
                *(row for row in inherited if row.measurement_type not in overridden),
            ],
            key=lambda row: row.id,
        )

    effective = {}

    def inherited(group_id):
        path, seen = [], set()
        current = group_id
        while current is not None and current not in effective:
            if current in seen:
                raise ValueError("Group hierarchy contains a cycle")
            seen.add(current)
            path.append(current)
            current = groups[current].parent_id
        value = effective.get(current, [])
        for key in reversed(path):
            value = combine(by_group[key], value)
            effective[key] = value
        return effective.get(group_id, [])

    studies = {
        row.id: {"sid": row.sid, "name": row.name}
        for row in session.scalars(
            select(Study).where(Study.id.in_({r.study_id for r in rows}))
        )
    }

    def group_summary(group_id):
        if group_id is None:
            return None
        group = groups[group_id]
        return {"pk": group.id, "name": group.name, "count": group.count}

    result = []
    for row in rows:
        values = (
            combine(by_individual[row.id], inherited(row.group_id))
            if individual
            else inherited(row.id)
        )
        serialized = [
            {
                **vocabulary.science(record),
                "count": record.count,
                "group_count": groups[record.group_id].count
                if record.group_id
                else None,
            }
            for record in values
        ]
        common = dict(
            pk=row.id,
            name=row.name,
            study=studies[row.study_id],
            characteristica=serialized,
        )
        result.append(
            (
                IndividualResponse.model_validate(
                    {**common, "group": group_summary(row.group_id)}
                )
                if individual
                else GroupResponse.model_validate(
                    {
                        **common,
                        "count": row.count,
                        "parent": group_summary(row.parent_id),
                    }
                )
            ).model_dump()
        )
    return result


def intervention_responses(session, rows):
    from pkdb.schemas.responses import InterventionResponse

    if not rows:
        return []
    vocabulary = VocabularyResponses(session, rows)
    studies = {
        row.id: {"sid": row.sid, "name": row.name}
        for row in session.scalars(
            select(Study).where(Study.id.in_({r.study_id for r in rows}))
        )
    }
    return [
        InterventionResponse.model_validate(
            {
                **vocabulary.science(row),
                "name": row.name,
                "normed": row.origin == "normalized",
                "route": vocabulary.node(row.route),
                "form": vocabulary.node(row.form),
                "application": vocabulary.node(row.application),
                "time": row.time_text
                if row.time_text is not None
                else (format(row.time, "g") if row.time is not None else None),
                "time_end": row.time_end,
                "time_unit": row.time_unit,
                "study": studies[row.study_id],
            }
        ).model_dump()
        for row in rows
    ]


def reference_responses(session, rows):
    from pkdb.db.models.studies import Author
    from pkdb.schemas.responses import ReferenceResponse

    if not rows:
        return []
    authors = defaultdict(list)
    for row in session.scalars(
        select(Author)
        .where(Author.reference_id.in_([r.id for r in rows]))
        .order_by(Author.position)
    ):
        authors[row.reference_id].append(
            {"pk": row.id, "first_name": row.first_name, "last_name": row.last_name}
        )
    return [
        ReferenceResponse.model_validate(
            {
                "pk": row.id,
                **{
                    key: getattr(row, key)
                    for key in (
                        "sid",
                        "name",
                        "pmid",
                        "doi",
                        "title",
                        "abstract",
                        "journal",
                    )
                },
                "date": row.date.isoformat() if row.date else None,
                "authors": authors[row.id],
            }
        ).model_dump()
        for row in rows
    ]
