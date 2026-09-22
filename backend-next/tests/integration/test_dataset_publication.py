from copy import deepcopy

from pkdb.db.read import read_study


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

    from pkdb.db.models.measurements import SubsetDimension

    with session_factory() as session:
        dimensions = list(
            session.scalars(select(SubsetDimension).order_by(SubsetDimension.position))
        )
        assert dimensions[0].point_id == dimensions[1].point_id
        assert dimensions[2].point_id == dimensions[3].point_id
        assert dimensions[0].point_id != dimensions[2].point_id
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
    from sqlalchemy import select

    from pkdb.db.models.measurements import Measurement

    service, principal = ingestion_context
    service.replace(valid_bundle, principal)
    with session_factory() as session:
        records = list(session.scalars(select(Measurement)))
        assert len(records) == 2
        assert records[0].source_id is not None
        assert records[0].source_id == records[1].source_id


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
