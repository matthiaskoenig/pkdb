"""Public, artificial study shared by browser and API contract tests."""

from pkdb.schemas.source import SourceBundle


def frontend_search_bundle(*, related=False, sid="FRONTEND_SCOPE"):
    outputs = [
        dict(
            group="all",
            interventions=["oral-A"],
            measurement_type="concentration",
            substance="drug",
            mean=0.0,
            unit="mg/l",
            time=0.0,
            time_unit="h",
            tissue="plasma",
        ),
        dict(
            group="all",
            interventions=["iv-B"],
            measurement_type="concentration",
            substance="drug-b",
            mean=2.125,
            unit="mg/l",
            time=1.0,
            time_unit="h",
            tissue="plasma",
        ),
    ]
    if related:
        outputs.append(dict(outputs[1], interventions=["oral-A", "iv-B"], mean=3.25))
    return SourceBundle(
        study={
            "sid": sid,
            "name": "Frontend scientific scope fixture",
            "creator": "curator",
            "curators": [{"user": "curator"}],
            "reference": "FRONTEND_REF",
            "access": "private",
            "licence": "open",
            "groupset": {
                "groups": [
                    {
                        "name": "all",
                        "count": 4,
                        "characteristica": [
                            {"measurement_type": "species", "choice": "Homo sapiens"},
                            {"measurement_type": "sex", "choice": "NR"},
                            {"measurement_type": "healthy", "choice": "Y"},
                        ],
                    }
                ]
            },
            "interventionset": {
                "interventions": [
                    dict(
                        name=name,
                        measurement_type="dosing",
                        substance=substance,
                        value=10.0,
                        unit="mg",
                        time=0.0,
                        time_unit="h",
                        route=route,
                        form="tablet",
                        application="single dose",
                    )
                    for name, substance, route in [
                        ("oral-A", "drug", "oral"),
                        ("iv-B", "drug-b", "iv"),
                    ]
                ]
            },
            "outputset": {"outputs": outputs},
        },
        reference={
            "sid": "FRONTEND_REF",
            "name": "Artificial frontend verification reference",
        },
    )


def add_frontend_vocabulary(session):
    from pkdb_server.db.models.vocabulary import VocabularyNode

    for sid, kind, definition in [
        ("drug-b", "substance", {"mass": 500.0}),
        ("drug", "substance", {"mass": 500.0}),
        ("iv", "route", {}),
    ]:
        if session.get(VocabularyNode, sid) is None:
            session.add(
                VocabularyNode(sid=sid, name=sid, kind=kind, definition=definition)
            )


def publish_frontend_fixture(session):
    from sqlalchemy import update

    from pkdb_server.db.models.studies import Study

    session.execute(
        update(Study).where(Study.sid == "FRONTEND_SCOPE").values(access="public")
    )


def add_frontend_plot_context(session):
    """Relate both existing normalized points; one may be outside a selection."""
    from sqlalchemy import select

    from pkdb_server.db.models.measurements import (
        Measurement,
        Scatter,
        Subset,
        SubsetDimension,
        SubsetPoint,
    )
    from pkdb_server.db.models.studies import Study

    study = session.scalar(select(Study).where(Study.sid == "FRONTEND_SCOPE"))
    points = list(
        session.scalars(
            select(Measurement)
            .where(Measurement.study_id == study.id, Measurement.origin == "normalized")
            .order_by(Measurement.time)
        )
    )
    for kind, width in [("timecourse", 1), ("scatter", 2)]:
        chart = Scatter(
            study_id=study.id,
            key=f"chart-{kind}",
            name=f"Fixture {kind}",
            data_type=kind,
        )
        session.add(chart)
        session.flush()
        subset = Subset(
            study_id=study.id,
            key=f"subset-{kind}",
            scatter_id=chart.id,
            name=f"Fixture {kind}",
            position=0,
            dimension_labels=["Y"] if width == 1 else ["X", "Y"],
        )
        session.add(subset)
        session.flush()
        for offset in range(0, len(points), width):
            point = SubsetPoint(
                study_id=study.id,
                key=f"point-{kind}-{offset}",
                subset_id=subset.id,
                position=offset // width,
            )
            session.add(point)
            session.flush()
            for dimension, measurement in enumerate(points[offset : offset + width]):
                session.add(
                    SubsetDimension(
                        study_id=study.id,
                        subset_id=subset.id,
                        position=offset + dimension,
                        dimension="Y" if width == 1 else ["X", "Y"][dimension],
                        point_id=point.id,
                        measurement_id=measurement.id,
                    )
                )
