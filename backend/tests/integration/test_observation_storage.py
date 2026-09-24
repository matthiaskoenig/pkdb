"""Shared observation contexts preserve lossless numerical representations."""

from sqlalchemy import func, inspect, select

from pkdb_server.db.models.measurements import (
    Dataset,
    ObservationContext,
    ObservationValue,
)
from pkdb_server.db.models.subjects import Subject
from pkdb_server.db.read import read_study


def test_contexts_are_shared_and_point_tables_are_absent(
    ingestion_context, valid_bundle, session_factory
):
    ingestion, principal = ingestion_context
    expected = ingestion.validate(valid_bundle, principal).study
    ingestion.replace(valid_bundle, principal)
    assert read_study(expected.sid, principal, session_factory) == expected
    with session_factory() as session:
        names = set(inspect(session.connection()).get_table_names())
        assert not names & {
            "groups",
            "individuals",
            "characteristics",
            "measurements",
            "timecourse_points",
            "subset_points",
            "subset_dimensions",
            "timecourses",
            "scatters",
            "subsets",
        }
        contexts = session.scalar(select(func.count()).select_from(ObservationContext))
        representations = session.scalar(
            select(func.count()).select_from(ObservationValue)
        )
        assert contexts > 0 and representations == contexts * 2
        kinds = set(session.scalars(select(ObservationContext.kind)))
        assert kinds == {"characteristic", "output"}
        assert session.scalar(select(func.count()).select_from(Subject)) == len(
            expected.groups
        ) + len(expected.individuals)
        courses = list(session.scalars(select(Dataset).where(Dataset.kind == "course")))
        assert all(isinstance(course.measurement_ids, list) for course in courses)
