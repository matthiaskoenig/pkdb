from pkdb.schemas.queries import QuerySpec
from pkdb.schemas.security import Principal
from sqlalchemy import select

from pkdb_server.db.models.studies import Study
from pkdb_server.db.models.subjects import Characteristic, Group, Individual
from pkdb_server.db.models.vocabulary import VocabularyNode
from pkdb_server.services.queries import QueryService


def test_individual_inherits_group_characteristics_with_local_override(
    ingestion_context, valid_bundle, session_factory
):
    service, creator = ingestion_context
    valid_bundle.study["access"] = "private"
    service.replace(valid_bundle, creator)
    with session_factory.begin() as session:
        session.add(
            VocabularyNode(sid="bodyweight", name="bodyweight", kind="measurement")
        )
        session.flush()
        root = session.scalar(select(Study))
        root.access = "public"  # Administrative publication in this read fixture.
        parent = session.scalar(select(Group).where(Group.study_id == root.id))
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
                    key="person-weight",
                    individual_id=person.id,
                    measurement_type="bodyweight",
                    value=72,
                    unit="kg",
                    origin="normalized",
                ),
            ]
        )
    page = QueryService(session_factory).search(
        QuerySpec(entity="individuals"), Principal()
    )
    assert page.count == 1
    record = page.items[0]
    assert record["name"] == "person"
    assert record["group"]["name"] == "child"
    characteristics = {
        row["measurement_type"]["name"]: row for row in record["characteristica"]
    }
    assert characteristics["bodyweight"]["value"] == 72
    assert "species" in characteristics
    assert (
        len(
            [
                row
                for row in record["characteristica"]
                if row["measurement_type"]["name"] == "sex"
            ]
        )
        == 1
    )
