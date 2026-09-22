"""Explicit simple-dictionary vectors shared by queries and expression indexes."""

from sqlalchemy import func, literal_column
from sqlalchemy.sql.expression import Grouping


def vector(columns):
    document = func.coalesce(columns[0], "")
    for column in columns[1:]:
        # Explicit binary operators preserve PostgreSQL's reflected grouping.
        document = Grouping(document.op("||")(literal_column("' '"))).op("||")(
            func.coalesce(column, "")
        )
    return func.to_tsvector(literal_column("'simple'"), document)


def text_match(columns, term):
    return vector(columns).bool_op("@@")(
        func.plainto_tsquery(literal_column("'simple'"), term)
    )
