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
