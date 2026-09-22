"""A saved selection can filter inherited groups and individuals together."""

from sqlalchemy import func, select

from pkdb.db.subject_filters import effective_characteristics


def test_inherited_subject_queries_can_share_one_statement(db_session):
    groups = effective_characteristics("groups")
    individuals = effective_characteristics("individuals")
    statement = select(
        select(func.count()).select_from(groups).scalar_subquery(),
        select(func.count()).select_from(individuals).scalar_subquery(),
    )
    assert db_session.execute(statement).one() == (0, 0)
