"""Coverage aggregation must preserve permissions and avoid representation inflation."""

from datetime import date

from pkdb.schemas.security import Principal
from pkdb_server.db.models.measurements import Measurement, Timecourse
from pkdb_server.db.models.studies import Study, StudyGrant
from pkdb_server.db.models.subjects import Group
from pkdb_server.db.models.users import User
from pkdb_server.db.models.vocabulary import VocabularyEdge, VocabularyNode
from pkdb_server.services.queries import QueryService


def test_coverage_dates_distinct_substances_pk_hierarchy_and_permissions(
    session_factory,
):
    with session_factory.begin() as session:
        user = User(username="curator", role="curator", active=True)
        session.add(user)
        session.add_all(
            [
                VocabularyNode(sid=sid, name=sid, kind=kind)
                for sid, kind in [
                    ("pharmacokinetic-measurement", "measurement"),
                    ("auc-measurement", "measurement"),
                    ("auc", "measurement"),
                    ("concentration", "measurement"),
                    ("A", "substance"),
                    ("B", "substance"),
                    ("secret", "substance"),
                ]
            ]
        )
        session.flush()
        actor = Principal(user_id=user.id, username=user.username, role=user.role)
        session.add_all(
            [
                VocabularyEdge(
                    child="auc-measurement", parent="pharmacokinetic-measurement"
                ),
                VocabularyEdge(child="auc", parent="auc-measurement"),
            ]
        )
        for index, (year, substance, access) in enumerate(
            [
                (2020, "A", "public"),
                (2022, "A", "public"),
                (2022, "B", "public"),
                (None, "B", "public"),
                (2019, "secret", "private"),
            ]
        ):
            study = Study(
                sid=f"S{index}",
                name=f"S{index}",
                date=date(year, 4, 1) if year else None,
                access=access,
                licence="open",
                creator_id=user.id,
            )
            session.add(study)
            session.flush()
            session.add(StudyGrant(study_id=study.id, user_id=user.id, role="curator"))
            group = Group(study_id=study.id, key="g", name="all", count=2)
            session.add(group)
            session.flush()
            points = []
            for key, mtype, origin, calculated in [
                ("c1", "concentration", "normalized", False),
                ("c2", "concentration", "normalized", False),
                ("raw", "concentration", "reported", False),
                ("pk", "auc", "normalized", False),
                ("pkcalc", "auc", "normalized", True),
                ("pkraw", "auc", "reported", False),
            ]:
                value = Measurement(
                    study_id=study.id,
                    key=key,
                    group_id=group.id,
                    measurement_type=mtype,
                    substance=substance,
                    value=1,
                    origin=origin,
                    calculated=calculated,
                )
                session.add(value)
                session.flush()
                if mtype == "concentration":
                    points.append(value.id)
            session.add(
                Timecourse(study_id=study.id, key="course", measurement_ids=points)
            )
    service = QueryService(session_factory)
    public = service.statistics_overview(Principal())
    assert public.counts["study_count"] == 4
    assert public.counts["timecourse_count"] == 4
    assert public.counts["substance_count"] == 2
    assert public.counts["pk_count"] == 8
    assert public.counts["pk_calculated_count"] == 4
    assert [
        (r.year, r.study_count, r.cumulative_study_count) for r in public.years
    ] == [(2020, 1, 1), (2021, 0, 1), (2022, 2, 3)]
    assert [r.cumulative_substance_count for r in public.years] == [1, 1, 2]
    assert [r.substance_count for r in public.years] == [1, 0, 2]
    assert public.undated.study_count == 1
    assert public.undated.pk_count == 2
    assert [(s.sid, s.timecourse_count) for s in public.substances] == [
        ("A", 2),
        ("B", 2),
    ]
    assert {p.sid for p in public.parameters} == {"auc"}
    assert sum(p.reported for p in public.parameters) == 4
    private = service.statistics_overview(actor)
    assert private.counts["study_count"] == 5
    assert private.counts["substance_count"] == 3
    assert private.years[0].year == 2019


def test_empty_statistics(session_factory):
    result = QueryService(session_factory).statistics_overview(Principal())
    assert result.years == result.substances == result.parameters == []
    assert all(value == 0 for value in result.counts.values())
    assert result.undated.study_count == 0
