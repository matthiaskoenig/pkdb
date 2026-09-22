"""Consistent PostgreSQL reads with permissions applied before count and paging."""

from sqlalchemy import func, select

from pkdb.db.models.interventions import Intervention
from pkdb.db.models.measurements import (
    Measurement,
    Scatter,
    Subset,
    Timecourse,
    TimecoursePoint,
)
from pkdb.db.models.studies import Reference, Study
from pkdb.db.models.subjects import Group, Individual
from pkdb.db.models.vocabulary import VocabularyNode
from pkdb.db.queries import MODELS, conditions, ordering, visibility
from pkdb.db.serialize import (
    intervention_responses,
    output_responses,
    reference_responses,
    subject_responses,
    subset_responses,
)
from pkdb.db.study_responses import study_responses
from pkdb.db.vocabulary_responses import vocabulary_responses
from pkdb.schemas.queries import Page, QuerySpec
from pkdb.schemas.security import Principal


class QueryService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def search(
        self, query: QuerySpec, principal: Principal, *, filter_spec=None
    ) -> Page:
        where, order = conditions(query), ordering(query)
        model = MODELS[query.entity]
        statement = select(model)
        if model is Reference:
            statement = statement.join(Study, Study.reference_id == Reference.id)
        elif model is not Study and model is not VocabularyNode:
            statement = statement.join(Study, model.study_id == Study.id)
        if model is Subset:
            statement = statement.join(Scatter, Subset.scatter_id == Scatter.id)
        if filter_spec is not None:
            from pkdb.db.selection import constraint

            statement = statement.where(
                constraint(query.entity, filter_spec, principal)
            )
        statement = statement.where(where)
        if model is not VocabularyNode:
            statement = statement.where(visibility(principal))
        with self.session_factory() as session:
            session.connection(execution_options={"isolation_level": "REPEATABLE READ"})
            count = session.scalar(
                select(func.count()).select_from(statement.subquery())
            )
            rows = list(
                session.scalars(
                    statement.order_by(*order)
                    .offset((query.page - 1) * query.page_size)
                    .limit(query.page_size)
                )
            )
            if model is VocabularyNode:
                items = vocabulary_responses(session, rows)
            elif model is Study:
                items = study_responses(session, rows, principal)
            elif model is Measurement:
                items = output_responses(session, rows)
            elif model is Subset:
                items = subset_responses(session, rows)
            elif model is Reference:
                items = reference_responses(session, rows)
            elif model is Intervention:
                items = intervention_responses(session, rows)
            else:
                items = subject_responses(session, rows, individual=model is Individual)
            return Page(
                items=items,
                count=count,
                next=query.page + 1 if query.page * query.page_size < count else None,
                previous=query.page - 1 if query.page > 1 else None,
            )

    def statistics(self, principal: Principal) -> dict[str, int]:
        visible = select(Study.id).where(visibility(principal))

        def owned(model, *extra):
            return (
                select(func.count())
                .select_from(model)
                .where(model.study_id.in_(visible), *extra)
                .scalar_subquery()
            )

        statement = select(
            select(func.count())
            .select_from(Study)
            .where(visibility(principal))
            .scalar_subquery()
            .label("study_count"),
            select(func.count(Study.reference_id))
            .where(visibility(principal))
            .scalar_subquery()
            .label("reference_count"),
            owned(Group).label("group_count"),
            owned(Individual).label("individual_count"),
            owned(Intervention, Intervention.origin == "normalized").label(
                "intervention_count"
            ),
            owned(Measurement, Measurement.origin == "normalized").label(
                "output_count"
            ),
            owned(
                Measurement,
                Measurement.origin == "normalized",
                Measurement.calculated.is_(True),
            ).label("output_calculated_count"),
            owned(
                Timecourse,
                select(TimecoursePoint.timecourse_id)
                .join(Measurement, Measurement.id == TimecoursePoint.measurement_id)
                .where(
                    TimecoursePoint.timecourse_id == Timecourse.id,
                    Measurement.origin == "normalized",
                )
                .exists(),
            ).label("timecourse_count"),
            owned(
                Subset,
                Subset.scatter_id.in_(
                    select(Scatter.id).where(Scatter.data_type == "scatter")
                ),
            ).label("scatter_count"),
        )
        with self.session_factory() as session:
            return dict(session.execute(statement).mappings().one())
