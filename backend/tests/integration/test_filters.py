import pytest
from pydantic import ValidationError

from pkdb.db.models.measurements import Measurement
from pkdb.db.models.studies import Study
from pkdb.db.models.subjects import Group
from pkdb.db.models.users import User
from pkdb.db.models.vocabulary import VocabularyNode
from pkdb.schemas.queries import Predicate, QuerySpec
from pkdb.schemas.security import Principal
from pkdb.services.queries import QueryService


@pytest.fixture
def crossed_measurements(session_factory):
    with session_factory.begin() as session:
        user = User(username="owner", role="curator", active=True)
        session.add(user)
        session.add_all(
            [
                VocabularyNode(sid=s, name=s, kind=k)
                for s, k in [
                    ("concentration", "measurement"),
                    ("A", "substance"),
                    ("B", "substance"),
                ]
            ]
        )
        session.flush()
        principal = Principal(user_id=user.id, username=user.username, role=user.role)
        for sid, access, records in [
            ("X", "public", [("A", 1), ("B", 10)]),
            ("Y", "public", [("A", 10)]),
            ("Z", "private", [("A", 10)]),
        ]:
            study = Study(
                sid=sid, name=sid, access=access, licence="open", creator_id=user.id
            )
            session.add(study)
            session.flush()
            group = Group(study_id=study.id, key="g", name="all", count=2)
            session.add(group)
            session.flush()
            for i, (substance, value) in enumerate(records):
                session.add(
                    Measurement(
                        study_id=study.id,
                        key=str(i),
                        group_id=group.id,
                        measurement_type="concentration",
                        substance=substance,
                        value=value,
                        origin="normalized",
                    )
                )
    return QueryService(session_factory), principal


def test_predicates_bind_to_same_measurement(crossed_measurements):
    queries, _ = crossed_measurements
    query = QuerySpec(
        entity="studies",
        predicates=[
            Predicate(field="outputs.substance", operator="eq", value="A"),
            Predicate(field="outputs.value", operator="gte", value=10),
        ],
    )
    page = queries.search(query, Principal())
    assert [item["sid"] for item in page.items] == ["Y"]
    assert page.count == 1


def test_private_counts_and_pages(crossed_measurements):
    queries, creator = crossed_measurements
    page = queries.search(QuerySpec(entity="studies", page_size=1, page=2), Principal())
    assert page.count == 2
    assert [row["sid"] for row in page.items] == ["Y"]
    assert page.previous == 1
    assert page.next is None
    assert queries.search(QuerySpec(entity="studies"), creator).count == 3
    assert queries.statistics(Principal())["output_count"] == 3
    assert queries.statistics(creator)["output_count"] == 4


def test_parameterized_values_and_rejected_fields(crossed_measurements):
    queries, creator = crossed_measurements
    assert (
        queries.search(
            QuerySpec(
                entity="studies",
                predicates=[Predicate(field="sid", operator="eq", value="' OR 1=1 --")],
            ),
            creator,
        ).count
        == 0
    )
    with pytest.raises(ValueError):
        queries.search(
            QuerySpec(entity="studies", sort="sid;DROP TABLE studies"), creator
        )
    with pytest.raises(ValueError):
        queries.search(
            QuerySpec(
                entity="studies",
                predicates=[
                    Predicate(field="private_internal", operator="eq", value="x")
                ],
            ),
            creator,
        )
    with pytest.raises(ValidationError):
        QuerySpec(entity="studies", page=-1)


def test_multiple_matching_children_do_not_duplicate_study(crossed_measurements):
    queries, _ = crossed_measurements
    page = queries.search(
        QuerySpec(
            entity="studies",
            predicates=[Predicate(field="outputs.value", operator="gte", value=1)],
        ),
        Principal(),
    )
    assert [row["sid"] for row in page.items] == ["X", "Y"]
    assert page.count == 2


def test_public_output_contains_complete_scientific_fields(crossed_measurements):
    queries, _ = crossed_measurements
    page = queries.search(QuerySpec(entity="outputs"), Principal())
    assert page.count == 3
    record = page.items[0]
    assert record["measurement_type"] == {
        "sid": "concentration",
        "name": "concentration",
        "label": "concentration",
    }
    assert record["group"]["name"] == "all"
    assert record["study"] == {"sid": "X", "name": "X"}
    assert set(record) == {
        "pk",
        "normed",
        "calculated",
        "tissue",
        "method",
        "label",
        "output_type",
        "study",
        "group",
        "individual",
        "interventions",
        "measurement_type",
        "calculation_type",
        "choice",
        "substance",
        "value",
        "mean",
        "median",
        "min",
        "max",
        "sd",
        "se",
        "cv",
        "unit",
        "time",
        "time_unit",
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("outputs.value", "invalid"),
        ("outputs.value", float("nan")),
        ("outputs.count", True),
    ],
)
def test_typed_filters_reject_invalid_values(crossed_measurements, field, value):
    queries, creator = crossed_measurements
    with pytest.raises(ValueError):
        queries.search(
            QuerySpec(
                entity="studies", predicates=[Predicate(field=field, value=value)]
            ),
            creator,
        )
