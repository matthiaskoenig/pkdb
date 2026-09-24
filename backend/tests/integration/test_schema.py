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


@pytest.mark.parametrize("failure", ["duplicate", "cross_study", "dangling", "deleted"])
def test_array_membership_integrity(db_session, schema_seed, failure):
    from sqlalchemy import text

    from pkdb_server.db.models.measurements import (
        Measurement,
        ObservationValue,
        Timecourse,
    )

    first, second, group = schema_seed
    observation = Measurement(
        study_id=first,
        key="m1",
        group_id=group,
        measurement_type="concentration",
        mean=1.0,
    )
    db_session.add(observation)
    db_session.flush()
    member_ids = [observation.id]
    if failure == "duplicate":
        member_ids.append(observation.id)
    elif failure == "dangling":
        member_ids = [999999]
    course = Timecourse(
        study_id=second if failure == "cross_study" else first,
        key="curve",
        measurement_ids=member_ids,
    )
    db_session.add(course)
    db_session.flush()
    if failure == "deleted":
        db_session.execute(
            delete(ObservationValue).where(ObservationValue.id == observation.id)
        )
    with pytest.raises(IntegrityError):
        db_session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_array_membership_accepts_atomic_replacement(db_session, schema_seed):
    from sqlalchemy import text

    from pkdb_server.db.models.measurements import (
        Measurement,
        ObservationValue,
        Timecourse,
    )

    first, _, group = schema_seed
    observation = Measurement(
        study_id=first, key="m1", group_id=group, measurement_type="concentration"
    )
    db_session.add(observation)
    db_session.flush()
    course = Timecourse(study_id=first, key="curve", measurement_ids=[observation.id])
    db_session.add(course)
    db_session.flush()
    db_session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    db_session.execute(text("SET CONSTRAINTS ALL DEFERRED"))
    db_session.execute(
        delete(ObservationValue).where(ObservationValue.id == observation.id)
    )
    course.measurement_ids = []
    db_session.flush()
    db_session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_individual_count_is_one(db_session, schema_seed):
    first, _, _ = schema_seed
    db_session.add(Individual(study_id=first, key="bad", name="bad", count=2))
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize(
    "failure",
    ["width", "row_count", "multidimensional", "null", "characteristic", "course_kind"],
)
def test_dataset_shape_and_observation_kinds(db_session, schema_seed, failure):
    from sqlalchemy import text

    from pkdb_server.db.models.measurements import (
        Characteristic,
        Measurement,
        Scatter,
        Subset,
    )

    first, _, group = schema_seed
    model = Characteristic if failure == "characteristic" else Measurement
    observation = model(
        study_id=first, key="m1", group_id=group, measurement_type="concentration"
    )
    parent = Scatter(study_id=first, key="scatter", name="scatter", data_type="scatter")
    db_session.add_all([observation, parent])
    db_session.flush()
    series = Subset(
        study_id=first,
        key="series",
        name="series",
        scatter_id=parent.id,
        position=0,
        dimension_labels=[{"dimension": "x", "output": "m1"}],
        measurement_ids=[observation.id],
        point_ids=[1],
    )
    if failure == "width":
        series.dimension_labels = []
    elif failure == "row_count":
        series.point_ids = []
    elif failure == "multidimensional":
        series.measurement_ids = [[observation.id]]  # ty: ignore[invalid-assignment]
    elif failure == "null":
        series.measurement_ids = [None]  # ty: ignore[invalid-assignment]
    elif failure == "course_kind":
        observation.derived_from_course_id = parent.id
    db_session.add(series)
    db_session.flush()
    with pytest.raises(IntegrityError):
        db_session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


@pytest.fixture
def committed_array_observation(session_factory):
    from pkdb_server.db.models.measurements import Measurement

    with session_factory.begin() as session:
        study = Study(
            sid="CONCURRENT", name="Concurrent", access="public", licence="open"
        )
        session.add_all(
            [
                study,
                VocabularyNode(
                    sid="concentration", name="Concentration", kind="measurement"
                ),
            ]
        )
        session.flush()
        group = Group(study_id=study.id, key="g", name="group", count=1)
        session.add(group)
        session.flush()
        observation = Measurement(
            study_id=study.id,
            key="m",
            group_id=group.id,
            measurement_type="concentration",
        )
        session.add(observation)
        session.flush()
        return study.id, observation.id


@pytest.mark.parametrize("first_action", ["membership", "delete"])
def test_concurrent_membership_and_delete_serialize(
    session_factory, committed_array_observation, first_action
):
    """Array membership takes the same member lock as a native foreign key."""
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    study_id, observation_id = committed_array_observation
    insert_membership = text(
        "INSERT INTO datasets (study_id, key, kind, measurement_ids) VALUES (:study, 'course', 'course', ARRAY[:member]::bigint[])"
    )
    delete_member = text("DELETE FROM observation_values WHERE id = :member")
    parameters = {"study": study_id, "member": observation_id}
    engine = session_factory.kw["bind"]
    with engine.connect() as first, engine.connect() as second:
        first.begin()
        second.begin()
        first.execute(text("SET LOCAL statement_timeout = '3s'"))
        second.execute(text("SET LOCAL statement_timeout = '3s'"))
        second.execute(text("SET LOCAL lock_timeout = '200ms'"))
        if first_action == "membership":
            first.execute(insert_membership, parameters)
            first.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            with pytest.raises(OperationalError, match="lock timeout"):
                second.execute(delete_member, parameters)
        else:
            first.execute(delete_member, parameters)
            second.execute(insert_membership, parameters)
            with pytest.raises(OperationalError, match="lock timeout"):
                second.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        second.rollback()
        first.commit()
        with pytest.raises(IntegrityError):
            second.execute(
                delete_member if first_action == "membership" else insert_membership,
                parameters,
            )
            second.commit()
        second.rollback()


@pytest.mark.parametrize("isolation", ["REPEATABLE READ", "SERIALIZABLE"])
@pytest.mark.parametrize("action", ["membership", "delete"])
def test_array_writes_require_read_committed(
    session_factory, committed_array_observation, isolation, action
):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    study_id, observation_id = committed_array_observation
    with (
        session_factory.kw["bind"]
        .connect()
        .execution_options(isolation_level=isolation) as connection
    ):
        connection.begin()
        # Repeatable-read queries remain valid; only scientific membership writes
        # are restricted because SQL triggers lack native RI snapshot cross-checks.
        assert connection.scalar(text("SELECT count(*) FROM observation_values")) == 1
        statement = (
            "INSERT INTO datasets (study_id, key, kind, measurement_ids) VALUES (:study, 'course', 'course', ARRAY[:member]::bigint[])"
            if action == "membership"
            else "DELETE FROM observation_values WHERE id = :member"
        )
        connection.execute(
            text(statement), {"study": study_id, "member": observation_id}
        )
        with pytest.raises(DBAPIError, match="require READ COMMITTED"):
            connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        connection.rollback()


@pytest.mark.parametrize("table", ["subjects", "observations", "datasets"])
def test_scientific_kind_is_immutable(
    session_factory, committed_array_observation, table
):
    from sqlalchemy import text

    study_id, _ = committed_array_observation
    with session_factory.begin() as session:
        if table == "datasets":
            session.execute(
                text(
                    "INSERT INTO datasets (study_id, key, kind) VALUES (:study, 'course', 'course')"
                ),
                {"study": study_id},
            )
    kind = {
        "subjects": "individual",
        "observations": "characteristic",
        "datasets": "dataset",
    }[table]
    with pytest.raises(IntegrityError, match="kind is immutable"):
        with session_factory.begin() as session:
            session.execute(text(f"UPDATE {table} SET kind = :kind"), {"kind": kind})
