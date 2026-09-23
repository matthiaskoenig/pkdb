"""Database constraints independently protect complete study ownership."""

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from pkdb_server.db.models.studies import Study
from pkdb_server.db.models.subjects import Group, Individual
from pkdb_server.db.models.users import User
from pkdb_server.db.models.vocabulary import VocabularyNode


def test_duplicate_sid_is_rejected(db_session, schema_seed):
    db_session.add(Study(sid="S1", name="duplicate", access="public", licence="open"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_cross_study_parent_is_rejected(db_session, schema_seed):
    first, second, group_id = schema_seed
    db_session.add(
        Group(study_id=second, key="bad", name="bad", count=1, parent_id=group_id)
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_cross_study_individual_group_is_rejected(db_session, schema_seed):
    first, second, group_id = schema_seed
    db_session.add(
        Individual(study_id=second, key="bad", name="bad", group_id=group_id)
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_delete_study_preserves_shared_entities_and_other_graph(
    db_session, schema_seed
):
    first, second, group_id = schema_seed
    db_session.execute(delete(Study).where(Study.id == first))
    assert db_session.get(Group, group_id) is None
    assert db_session.scalar(select(Study.id).where(Study.id == second)) == second
    assert db_session.scalar(select(User.username)) == "curator"
    assert db_session.scalar(select(VocabularyNode.sid)) == "concentration"


def test_dangling_group_is_rejected(db_session, schema_seed):
    first, _, _ = schema_seed
    db_session.add(Individual(study_id=first, key="bad", name="bad", group_id=999999))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_reference_cannot_be_assigned_to_two_studies(db_session, schema_seed):
    from pkdb_server.db.models.studies import Reference

    first, second, _ = schema_seed
    reference = Reference(sid="R1", name="reference")
    db_session.add(reference)
    db_session.flush()
    db_session.get(Study, first).reference_id = reference.id
    db_session.get(Study, second).reference_id = reference.id
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_duplicate_timecourse_position_is_rejected(db_session, schema_seed):
    from pkdb_server.db.models.measurements import (
        Measurement,
        Timecourse,
        TimecoursePoint,
    )

    first, _, group = schema_seed
    course = Timecourse(study_id=first, key="curve")
    points = [
        Measurement(
            study_id=first,
            key=f"m{i}",
            group_id=group,
            measurement_type="concentration",
            mean=i,
        )
        for i in range(2)
    ]
    db_session.add_all([course, *points])
    db_session.flush()
    db_session.add_all(
        [
            TimecoursePoint(
                study_id=first,
                timecourse_id=course.id,
                measurement_id=point.id,
                position=0,
            )
            for point in points
        ]
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_cross_study_timecourse_point_is_rejected(db_session, schema_seed):
    from pkdb_server.db.models.measurements import (
        Measurement,
        Timecourse,
        TimecoursePoint,
    )

    first, second, group = schema_seed
    course = Timecourse(study_id=second, key="curve")
    point = Measurement(
        study_id=first, key="m1", group_id=group, measurement_type="concentration"
    )
    db_session.add_all([course, point])
    db_session.flush()
    db_session.add(
        TimecoursePoint(
            study_id=second,
            timecourse_id=course.id,
            measurement_id=point.id,
            position=0,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
