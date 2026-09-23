from sqlalchemy import select

from pkdb.schemas.queries import Predicate, QuerySpec
from pkdb_server.db.models.measurements import Measurement


def test_concise_selection_uses_matching_normalized_outputs(
    ingestion_context, valid_bundle, session_factory
):
    from pkdb.schemas.filters import FilterSpec
    from pkdb_server.db.selection import selection

    ingestion, creator = ingestion_context
    ingestion.replace(valid_bundle, creator)
    spec = FilterSpec(queries={"outputs": QuerySpec(entity="outputs")})
    selected = selection(spec, creator)
    with session_factory() as session:
        assert len(list(session.scalars(selected["studies"]))) == 1
        outputs = list(session.scalars(selected["outputs"]))
        assert len(outputs) == 1
        assert (
            session.scalar(
                select(Measurement.origin).where(Measurement.id == outputs[0])
            )
            == "normalized"
        )
        assert len(list(session.scalars(selected["groups"]))) == 1
        assert len(list(session.scalars(selected["interventions"]))) == 1
        assert list(session.scalars(selected["individuals"])) == []
        assert list(session.scalars(selected["timecourses"])) == []
    missing = QuerySpec(
        entity="outputs", predicates=[Predicate(field="substance", value="missing")]
    )
    for concise in (True, False):
        selected = selection(
            FilterSpec(queries={"outputs": missing}, concise=concise), creator
        )
        with session_factory() as session:
            assert list(session.scalars(selected["studies"])) == []


def test_selection_subject_filters_compile_together(
    ingestion_context, valid_bundle, session_factory
):
    from pkdb.schemas.filters import FilterSpec
    from pkdb_server.db.selection import selection

    ingestion, creator = ingestion_context
    ingestion.replace(valid_bundle, creator)
    spec = FilterSpec(
        queries={
            entity: QuerySpec(
                entity=entity,
                predicates=[
                    Predicate(field="characteristics.measurement_type", value="sex")
                ],
            )
            for entity in ("groups", "individuals")
        }
    )
    with session_factory() as session:
        assert len(list(session.scalars(selection(spec, creator)["outputs"]))) == 1
