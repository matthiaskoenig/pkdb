"""Parameterized related-record text membership for public read queries."""

from sqlalchemy import exists, or_, select

from pkdb.db.models.interventions import Intervention
from pkdb.db.models.measurements import (
    Measurement,
    MeasurementIntervention,
    Scatter,
    Subset,
    SubsetDimension,
)
from pkdb.db.models.studies import Reference, Study, StudyUser
from pkdb.db.models.subjects import Group, Individual
from pkdb.db.models.users import User
from pkdb.db.models.vocabulary import VocabularyNode, VocabularyTerm
from pkdb.db.textsearch import text_match


def vocabulary_match(columns, term):
    return exists(
        select(VocabularyNode.sid).where(
            or_(*(VocabularyNode.sid == column for column in columns)),
            or_(
                text_match([VocabularyNode.sid, VocabularyNode.name], term),
                exists(
                    select(VocabularyTerm.node_sid).where(
                        VocabularyTerm.node_sid == VocabularyNode.sid,
                        VocabularyTerm.kind.in_(["label", "synonyms"]),
                        text_match([VocabularyTerm.value], term),
                    )
                ),
            ),
        )
    )


def science_match(model, term):
    vocab = [
        getattr(model, field)
        for field in (
            "measurement_type",
            "substance",
            "tissue",
            "method",
            "route",
            "form",
            "application",
        )
        if hasattr(model, field)
    ]
    parts = [
        vocabulary_match(vocab, term),
        text_match([model.choice, model.time_unit], term),
    ]
    if model is Intervention:
        parts.append(text_match([model.name], term))
    else:
        parts.extend(
            [
                exists(
                    select(Group.id).where(
                        Group.id == Measurement.group_id,
                        text_match([Group.name], term),
                    )
                ),
                exists(
                    select(Individual.id).where(
                        Individual.id == Measurement.individual_id,
                        text_match([Individual.name], term),
                    )
                ),
                exists(
                    select(MeasurementIntervention.measurement_id)
                    .join(
                        Intervention,
                        Intervention.id == MeasurementIntervention.intervention_id,
                    )
                    .where(
                        MeasurementIntervention.measurement_id == Measurement.id,
                        text_match([Intervention.name], term),
                    )
                ),
            ]
        )
    return or_(*parts)


def search_condition(entity, term):
    if entity == "info_nodes":
        return or_(
            text_match([VocabularyNode.sid, VocabularyNode.name], term),
            exists(
                select(VocabularyTerm.node_sid).where(
                    VocabularyTerm.node_sid == VocabularyNode.sid,
                    text_match([VocabularyTerm.value], term),
                )
            ),
        )
    parts = [text_match([Study.sid, Study.name], term)]
    if entity == "studies":
        parts.extend(
            [
                exists(
                    select(Reference.id).where(
                        Reference.id == Study.reference_id,
                        text_match(
                            [Reference.pmid, Reference.title, Reference.name], term
                        ),
                    )
                ),
                exists(
                    select(User.id).where(
                        or_(
                            User.id == Study.creator_id,
                            User.id.in_(
                                select(StudyUser.user_id)
                                .where(StudyUser.study_id == Study.id)
                                .correlate(Study)
                            ),
                        ),
                        text_match(
                            [User.username, User.first_name, User.last_name], term
                        ),
                    )
                ),
                exists(
                    select(Measurement.id).where(
                        Measurement.study_id == Study.id,
                        vocabulary_match([Measurement.substance], term),
                    )
                ),
                exists(
                    select(Intervention.id).where(
                        Intervention.study_id == Study.id,
                        vocabulary_match([Intervention.substance], term),
                    )
                ),
            ]
        )
    elif entity == "references":
        parts.append(
            text_match(
                [
                    Reference.sid,
                    Reference.name,
                    Reference.pmid,
                    Reference.title,
                    Reference.abstract,
                ],
                term,
            )
        )
    elif entity in {"outputs", "interventions"}:
        parts.append(
            science_match(Measurement if entity == "outputs" else Intervention, term)
        )
    elif entity in {"groups", "individuals"}:
        model = Group if entity == "groups" else Individual
        parts.append(text_match([model.name], term))
        if model is Individual:
            parts.append(
                exists(
                    select(Group.id).where(
                        Group.id == Individual.group_id,
                        text_match([Group.name], term),
                    )
                )
            )
    elif entity == "subsets":
        parts.extend(
            [
                text_match([Subset.name, Scatter.data_type], term),
                exists(
                    select(SubsetDimension.subset_id)
                    .join(Measurement, Measurement.id == SubsetDimension.measurement_id)
                    .where(
                        SubsetDimension.subset_id == Subset.id,
                        science_match(Measurement, term),
                    )
                ),
            ]
        )
    return or_(*parts)
