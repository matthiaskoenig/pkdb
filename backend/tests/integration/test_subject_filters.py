from sqlalchemy import select

from pkdb.db.models.studies import Study
from pkdb.db.models.subjects import Characteristic, Group, Individual
from pkdb.db.models.vocabulary import VocabularyEdge, VocabularyNode
from pkdb.schemas.queries import Predicate, QuerySpec
from pkdb.schemas.security import Principal
from pkdb.services.queries import QueryService


def test_inherited_filters_use_effective_same_characteristic(
    ingestion_context, valid_bundle, session_factory
):
    ingestion, creator = ingestion_context
    valid_bundle.study["access"] = "private"
    ingestion.replace(valid_bundle, creator)
    with session_factory.begin() as session:
        session.add_all(
            [
                VocabularyNode(sid="male-test", name="M", kind="choice"),
                VocabularyNode(sid="female-test", name="F", kind="choice"),
                VocabularyNode(sid="weight-test", name="weight", kind="measurement"),
            ]
        )
        session.flush()
        session.add_all(
            [
                VocabularyEdge(child=sid, parent="sex")
                for sid in ("male-test", "female-test")
            ]
        )
        root = session.scalar(select(Study))
        root.access = "public"  # Administrative publication in this read fixture.
        parent = session.scalar(select(Group))
        child = Group(
            study_id=root.id, key="child", name="child", count=1, parent_id=parent.id
        )
        session.add(child)
        session.flush()
        person = Individual(
            study_id=root.id, key="person", name="person", group_id=child.id
        )
        session.add(person)
        session.flush()
        session.add_all(
            [
                Characteristic(
                    study_id=root.id,
                    key="parent-sex",
                    group_id=parent.id,
                    measurement_type="sex",
                    choice="M",
                    origin="normalized",
                ),
                Characteristic(
                    study_id=root.id,
                    key="child-sex",
                    group_id=child.id,
                    measurement_type="sex",
                    choice="F",
                    origin="normalized",
                ),
                Characteristic(
                    study_id=root.id,
                    key="weight",
                    individual_id=person.id,
                    measurement_type="weight-test",
                    value=72,
                    origin="normalized",
                ),
            ]
        )
    queries = QueryService(session_factory)

    def search(entity, predicates):
        return queries.search(
            QuerySpec(
                entity=entity,
                predicates=[Predicate.model_validate(p) for p in predicates],
            ),
            Principal(),
        )

    assert [
        r["name"]
        for r in search(
            "groups", [{"field": "characteristics.choice_sid", "value": "female-test"}]
        ).items
    ] == ["child"]
    assert (
        search(
            "individuals",
            [{"field": "characteristics.choice_sid", "value": "male-test"}],
        ).count
        == 0
    )
    assert (
        search(
            "individuals",
            [{"field": "characteristics.choice_sid", "value": "female-test"}],
        ).count
        == 1
    )
    assert (
        search(
            "individuals",
            [
                {
                    "field": "characteristics.choice_sid",
                    "operator": "exclude",
                    "value": ["female-test"],
                }
            ],
        ).count
        == 0
    )
    assert (
        search(
            "individuals",
            [
                {"field": "characteristics.measurement_type", "value": "sex"},
                {"field": "characteristics.value", "operator": "gte", "value": 70},
            ],
        ).count
        == 0
    )
    assert (
        search(
            "individuals",
            [
                {"field": "characteristics.measurement_type", "value": "weight-test"},
                {"field": "characteristics.value", "operator": "gte", "value": 70},
            ],
        ).count
        == 1
    )
    assert (
        queries.search(
            QuerySpec(entity="individuals", search="female-test"), Principal()
        ).count
        == 1
    )
    assert (
        queries.search(
            QuerySpec(entity="individuals", search="male-test"), Principal()
        ).count
        == 0
    )
