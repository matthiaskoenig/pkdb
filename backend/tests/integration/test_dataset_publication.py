from copy import deepcopy

from pkdb_server.db.read import read_study


def test_scatter_survives_atomic_publication_and_readback(
    ingestion_context, valid_bundle, session_factory
):
    service, principal = ingestion_context
    base = valid_bundle.study["outputset"]["outputs"][0]
    valid_bundle.study["outputset"]["outputs"] = [
        dict(deepcopy(base), label=label, time=time, output_type="array")
        for time in (0, 1)
        for label in ("x", "y")
    ]
    valid_bundle.study["dataset"] = {
        "data": [
            {
                "name": "correlation",
                "data_type": "scatter",
                "descriptions": ["Dataset note"],
                "subsets": [
                    {
                        "name": "pairs",
                        "shared": ["time"],
                        "dimensions": ["x", "y"],
                        "descriptions": ["Subset note"],
                    }
                ],
            }
        ]
    }
    expected = service.validate(valid_bundle, principal).study
    result = service.replace(valid_bundle, principal)
    actual = read_study(result.sid, principal, session_factory)
    assert actual.scatters == expected.scatters
    assert len(actual.scatters[0].subsets[0].points) == 2
    from sqlalchemy import select

    from pkdb_server.db.dataset_arrays import dataset_cells
    from pkdb_server.db.models.measurements import Subset

    with session_factory() as session:
        cells = dataset_cells()
        dimensions = session.execute(select(cells).order_by(cells.c.position)).all()
        subset = session.scalar(select(Subset))
        assert len(subset.measurement_ids) == 4
        assert len(subset.point_ids) == 2
        assert [cell.measurement_id for cell in dimensions] == subset.measurement_ids
        assert dimensions[0].point_id == dimensions[1].point_id
        assert dimensions[2].point_id == dimensions[3].point_id
        assert dimensions[0].point_id != dimensions[2].point_id
        from pkdb.schemas.queries import Predicate, QuerySpec
        from pkdb_server.db.analysis import serialize, statement

        query, order = statement("data", QuerySpec(entity="subsets"), principal)
        page = session.execute(query.order_by(*order).offset(1).limit(2)).all()
        exported = serialize(session, "data", page, principal)
        assert [row["output_pk"] for row in exported] == subset.measurement_ids[1:3]
        assert [row["dimension"] for row in exported] == [1, 0]
        assert [row["data_point_pk"] for row in exported] == subset.point_ids
        filtered, _ = statement(
            "data",
            QuerySpec(
                entity="subsets",
                predicates=[
                    Predicate(
                        field="output_pk",
                        operator="eq",
                        value=subset.measurement_ids[2],
                    )
                ],
            ),
            principal,
        )
        assert len(session.execute(filtered).all()) == 1
    service.replace(valid_bundle, principal)
    assert (
        read_study(result.sid, principal, session_factory).scatters == expected.scatters
    )


def test_unknown_comment_author_cannot_be_silently_dropped(
    ingestion_context, valid_bundle
):
    import pytest

    from pkdb.schemas.validation import StudyValidationError

    service, principal = ingestion_context
    valid_bundle.study["groupset"]["groups"][0]["comments"] = [
        ["missing-user", "Attributed note"]
    ]
    with pytest.raises(StudyValidationError, match="unknown user"):
        service.replace(valid_bundle, principal)


def test_reported_and_normalized_outputs_share_source_identity(
    ingestion_context, valid_bundle, session_factory
):
    from sqlalchemy import func, select

    from pkdb_server.db.models.measurements import (
        Measurement,
        MeasurementIntervention,
        ObservationIntervention,
    )

    service, principal = ingestion_context
    service.replace(valid_bundle, principal)
    with session_factory() as session:
        records = list(session.scalars(select(Measurement)))
        assert len(records) == 2
        assert records[0].source_id is not None
        assert records[0].source_id == records[1].source_id

        assert (
            session.scalar(select(func.count()).select_from(ObservationIntervention))
            == 1
        )
        assert (
            session.scalar(select(func.count()).select_from(MeasurementIntervention))
            == 2
        )
        linked = session.execute(
            select(Measurement.id, MeasurementIntervention.intervention_id)
            .join(
                MeasurementIntervention,
                MeasurementIntervention.measurement_id == Measurement.id,
            )
            .order_by(Measurement.id)
        ).all()
        assert [row.id for row in linked] == [row.id for row in records]
        assert linked[0].intervention_id == linked[1].intervention_id


def test_subject_and_intervention_image_provenance_survives_publication(
    ingestion_context, valid_bundle, session_factory, tmp_path
):
    service, principal = ingestion_context
    image = tmp_path / "Example_Fig1.png"
    image.write_bytes(b"source figure")
    valid_bundle.files[image.name] = image
    valid_bundle.study["groupset"]["groups"][0]["image"] = "Fig1"
    valid_bundle.study["individualset"] = {
        "individuals": [{"name": "person", "group": "all", "image": "Fig1"}]
    }
    valid_bundle.study["interventionset"]["interventions"][0]["image"] = "Fig1"
    prepared = service.validate(valid_bundle, principal).study
    result = service.replace(valid_bundle, principal)
    restored = read_study(result.sid, principal, session_factory)
    assert restored == prepared
    assert restored.groups[0].image == image.name
    assert restored.individuals[0].image == image.name
    assert all(record.image == image.name for record in restored.interventions)
