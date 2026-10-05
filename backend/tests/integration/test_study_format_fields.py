"""Study format 2 statistics, schedules, release and review survive the database."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from pkdb.schemas.review import Review
from pkdb.schemas.study import CanonicalStudy
from pkdb_server.db import replace
from pkdb_server.db.models.interventions import Intervention
from pkdb_server.db.models.measurements import ObservationValue
from pkdb_server.db.models.studies import Study, StudyGrant
from pkdb_server.db.models.subjects import Subject
from pkdb_server.db.read import read_study

REVIEW = {
    "status": "in_review",
    "reviewers": ["curator"],
    "items": [
        {
            "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2AB",
            "kind": "uncertainty",
            "state": "resolved",
            "target": {
                "file": "timecourses_Fig2.tsv",
                "rows": {"label": "caf_plasma_D1"},
                "column": "sd",
            },
            "acknowledges": "sd_se_mismatch",
            "text": "The legend does not say whether the error bars are SD or SE.",
            "author": "curator",
            "agent": "claude-opus-5-5",
            "created": "2026-10-05T10:12:00Z",
            "thread": [
                {
                    "author": "curator",
                    "created": "2026-10-06T07:58:00Z",
                    "text": "Methods section: SD.",
                }
            ],
            "resolved_by": "curator",
            "resolved": "2026-10-06T08:00:00Z",
        },
        {
            "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2AC",
            "kind": "question",
            "text": "Is the second dose given with food?",
            "author": "curator",
            "created": "2026-10-05T10:13:00Z",
        },
    ],
}
GEOMETRIC = {
    "gmean": 1.8,
    "gsd": 1.3,
    "gcv": 0.2655,
    "error_bar": 2.5,
    "error_type": "sd",
}


CHARACTERISTIC = {
    "measurement_type": "concentration",
    "substance": "drug",
    "unit": "mg/l",
    "statistics": {"mean": 2.0},
}
CONTEXT = {
    "tissue": "plasma",
    "method": "LC-MS",
    "time": 1.5,
    "time_unit": "h",
    "image": "Example_Tab1.png",
}


def schedule(key, **fields):
    return {
        "key": key,
        "name": key,
        "measurement_type": "dosing",
        "substance": "drug",
        "statistics": {"mean": 10.0},
        "unit": "mg",
        "time_unit": "h",
        "route": "oral",
        "form": "tablet",
        "application": "single dose",
        **fields,
    }


@pytest.fixture
def format2_study(valid_study):
    data = valid_study.model_dump(mode="json")
    data["sid"] = "drug/Example"
    data["metadata"].update(
        issue=2158,
        release={"pkdb_id": "PKDB01237", "date": "2026-09-28"},
        review=REVIEW,
    )
    data["interventions"] = [
        schedule(
            "dose",
            time=0.0,
            statistics={"mean": 10.0, "gmean": 9.0, "gsd": 1.1, "gcv": 0.1},
        ),
        schedule("list", time=[0.0, 12.0, 40.0]),
        schedule("repeat", time=0.0, interval=24.0, doses=7),
        schedule("subject", time=0.0, subject="all"),
        schedule("context", tissue="plasma", method="LC-MS"),
        schedule(
            "unreported",
            time_unit=None,
            time_not_reported=True,
            time_unit_not_reported=True,
        ),
    ]
    data["measurements"][0]["statistics"].update(GEOMETRIC)
    data["groups"][0]["characteristica"].append(
        {
            "key": "c4",
            "measurement_type": "concentration",
            "substance": "drug",
            "unit": "mg/l",
            "statistics": {"gmean": 3.0, "error_bar": 1.5, "error_type": "gsd"},
        }
    )
    data["groups"][0]["characteristica"].extend(
        [
            {**CHARACTERISTIC, "key": "c5", **CONTEXT},
            {
                **CHARACTERISTIC,
                "key": "c6",
                "time_not_reported": True,
                "time_unit_not_reported": True,
            },
        ]
    )
    return CanonicalStudy.model_validate(data)


def publish(session_factory, principal, study):
    with session_factory.begin() as session:
        root = Study(
            sid=study.sid,
            name=study.metadata.name,
            access=study.metadata.access,
            licence=study.metadata.licence,
            creator_id=principal.user_id,
            source_digest=study.source_digest,
        )
        session.add(root)
        session.flush()
        session.add(
            StudyGrant(study_id=root.id, user_id=principal.user_id, role="curator")
        )
        replace.insert_graph(session, root, study)
        return root.id


def test_new_fields_round_trip_through_the_database(
    ingestion_context, session_factory, format2_study
):
    _, principal = ingestion_context
    publish(session_factory, principal, format2_study)
    assert read_study(format2_study.sid, principal, session_factory) == format2_study


def test_schedules_and_subjects_are_stored_in_their_columns(
    ingestion_context, session_factory, format2_study
):
    _, principal = ingestion_context
    study_id = publish(session_factory, principal, format2_study)
    with session_factory() as session:
        rows = {
            row.key: row
            for row in session.scalars(
                select(Intervention).where(Intervention.study_id == study_id)
            )
        }
        group = session.scalar(select(Subject.id).where(Subject.name == "all"))
        values = session.scalar(
            select(ObservationValue).where(ObservationValue.key == "m1")
        )
        root = session.get(Study, study_id)
    assert (rows["list"].time, rows["list"].time_list) == (None, [0.0, 12.0, 40.0])
    assert (rows["repeat"].time, rows["repeat"].interval, rows["repeat"].doses) == (
        0.0,
        24.0,
        7,
    )
    assert rows["subject"].subject_id == group
    assert rows["dose"].subject_id is None
    assert (rows["dose"].gmean, rows["dose"].gsd, rows["dose"].gcv) == (9.0, 1.1, 0.1)
    assert {name: getattr(values, name) for name in GEOMETRIC} == GEOMETRIC
    assert (root.pkdb_id, root.release_date.isoformat(), root.issue) == (
        "PKDB01237",
        "2026-09-28",
        2158,
    )
    assert root.review_status == "in_review"
    assert root.review == Review.model_validate(REVIEW).model_dump(
        mode="json", include={"reviewers", "items"}
    )


def test_observation_context_is_stored_in_its_columns(
    ingestion_context, session_factory, format2_study
):
    from pkdb_server.db.models.subjects import Characteristic

    _, principal = ingestion_context
    study_id = publish(session_factory, principal, format2_study)
    with session_factory() as session:
        interventions = {
            row.key: row
            for row in session.scalars(
                select(Intervention).where(Intervention.study_id == study_id)
            )
        }
        characteristics = {
            row.key: row
            for row in session.scalars(
                select(Characteristic).where(Characteristic.study_id == study_id)
            )
        }
    context = interventions["context"]
    assert (context.tissue, context.method) == ("plasma", "LC-MS")
    assert not (context.time_not_reported or context.time_unit_not_reported)
    unreported = interventions["unreported"]
    assert (unreported.time, unreported.time_unit) == (None, None)
    assert unreported.time_not_reported and unreported.time_unit_not_reported
    timed = characteristics["c5"]
    assert {name: getattr(timed, name) for name in CONTEXT} == CONTEXT
    assert characteristics["c6"].time_not_reported
    assert characteristics["c6"].time_unit_not_reported


def test_studies_without_release_or_review_store_nothing(
    ingestion_context, session_factory, valid_study
):
    _, principal = ingestion_context
    study_id = publish(session_factory, principal, valid_study)
    with session_factory() as session:
        root = session.get(Study, study_id)
        assert (
            root.pkdb_id,
            root.release_date,
            root.issue,
            root.review_status,
            root.review,
        ) == (None, None, None, None, None)
    assert read_study(valid_study.sid, principal, session_factory) == valid_study


def test_new_record_fields_round_trip_through_ingestion(
    ingestion_context, valid_bundle, session_factory
):
    ingestion, principal = ingestion_context
    intervention = valid_bundle.study["interventionset"]["interventions"][0]
    intervention.update(subject="all", gmean=9.0, gsd=1.2)
    valid_bundle.study["interventionset"]["interventions"].append(
        dict(intervention, name="repeat", time=0.0, interval=24.0, doses=3)
    )
    valid_bundle.study["outputset"]["outputs"][0].update(GEOMETRIC)
    prepared = ingestion.validate(valid_bundle, principal)
    result = ingestion.replace(valid_bundle, principal)
    study = read_study(result.sid, principal, session_factory)
    assert study == prepared.study
    interventions = {record.name: record for record in study.interventions}
    assert interventions["dose"].subject == "all"
    assert interventions["dose"].statistics.gsd == 1.2
    assert (interventions["repeat"].interval, interventions["repeat"].doses) == (
        24.0,
        3,
    )
    for record in study.measurements:
        assert record.statistics.model_dump(include=set(GEOMETRIC)) == GEOMETRIC


@pytest.mark.parametrize(
    ("table", "assignment"),
    [
        ("studies", "pkdb_id = 'PKDB1'"),
        ("studies", "pkdb_id = 'XKDB00001', release_date = '2026-01-01'"),
        ("studies", "issue = 0"),
        ("studies", "review_status = 'done', review = '{}'"),
        ("studies", "pkdb_id = NULL"),
        ("studies", "release_date = NULL"),
        ("studies", "review_status = NULL"),
        ("studies", "review = NULL"),
        ("interventions", "doses = 0"),
        ("interventions", "error_type = 'cv'"),
        ("interventions", "time = NULL, time_list = '{1}'"),
        ("interventions", "time = 1, time_list = '{1, 2}'"),
        ("observation_values", "error_type = 'range'"),
    ],
)
def test_database_rejects_invalid_values(
    ingestion_context, session_factory, format2_study, table, assignment
):
    _, principal = ingestion_context
    publish(session_factory, principal, format2_study)
    with session_factory() as session, pytest.raises(IntegrityError):
        session.execute(
            text(
                f"UPDATE {table} SET {assignment} WHERE id = (SELECT min(id) FROM {table})"
            )
        )
        session.flush()


def test_pkdb_identifiers_are_unique(ingestion_context, session_factory, format2_study):
    _, principal = ingestion_context
    publish(session_factory, principal, format2_study)
    other = format2_study.model_copy(
        update={
            "sid": "drug/Other",
            "reference": format2_study.reference.model_copy(update={"sid": "REF2"}),
        },
        deep=True,
    )
    with pytest.raises(IntegrityError):
        publish(session_factory, principal, other)


def test_unspecified_summary_is_stored_in_mean(
    ingestion_context, valid_bundle, session_factory
):
    from pkdb_server.db.models.vocabulary import VocabularyNode

    ingestion, principal = ingestion_context
    with session_factory.begin() as session:
        session.add(
            VocabularyNode(
                sid="unspecified-summary",
                name="unspecified summary",
                kind="calculation_type",
                definition={},
            )
        )
    valid_bundle.study["outputset"]["outputs"][0].update(
        calculation_type="unspecified summary"
    )
    published = ingestion.replace(valid_bundle, principal)
    study = read_study(published.sid, principal, session_factory)
    assert {
        (record.origin, record.calculation_type, record.statistics.mean)
        for record in study.measurements
    } == {
        ("reported", "unspecified summary", 2.0),
        ("normalized", "unspecified summary", 2.0),
    }
