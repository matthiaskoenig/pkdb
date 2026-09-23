"""Consistent flat analysis reads over typed PostgreSQL relations."""

from sqlalchemy import func, select

from pkdb.schemas.queries import Page
from pkdb_server.db import analysis


class AnalysisService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def search(self, entity, query, principal, *, filter_spec=None):
        statement, order = analysis.statement(entity, query, principal)
        if filter_spec is not None:
            from pkdb_server.db.selection import constraint

            statement = statement.where(constraint(entity, filter_spec, principal))
        with self.session_factory() as session:
            session.connection(execution_options={"isolation_level": "REPEATABLE READ"})
            count = session.scalar(
                select(func.count()).select_from(statement.subquery())
            )
            rows = session.execute(
                statement.order_by(*order)
                .offset((query.page - 1) * query.page_size)
                .limit(query.page_size)
            ).all()
            return Page(
                items=analysis.serialize(session, entity, rows, principal),
                count=count,
                next=query.page + 1 if query.page * query.page_size < count else None,
                previous=query.page - 1 if query.page > 1 else None,
            )

    def iter_rows(self, session, entity, query, principal, *, filter_spec=None):
        statement, order = analysis.statement(entity, query, principal)
        if filter_spec is not None:
            from pkdb_server.db.selection import constraint

            statement = statement.where(constraint(entity, filter_spec, principal))
        offset = 0
        while True:
            rows = session.execute(
                statement.order_by(*order).offset(offset).limit(500)
            ).all()
            if not rows:
                return
            yield from analysis.serialize(session, entity, rows, principal)
            offset += len(rows)
