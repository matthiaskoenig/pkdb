"""Legacy two-axis scatter rows assembled from typed point associations."""

from collections import defaultdict

from sqlalchemy import select

from pkdb_server.db.analysis import science
from pkdb_server.db.models.measurements import Measurement, Subset, SubsetDimension
from pkdb_server.db.models.studies import Study
from pkdb_server.db.selection import selection
from pkdb_server.db.serialize import subset_responses


def collapse(values, *, keep=False):
    if all(value is None for value in values):
        return None
    if not keep and all(value == values[0] for value in values):
        return values[0]
    return tuple(values)


def rows(session, spec, principal):
    selected = selection(spec, principal)["scatters"]
    offset = 0
    while True:
        subsets = list(
            session.scalars(
                select(Subset)
                .where(Subset.id.in_(selected))
                .order_by(Subset.id)
                .offset(offset)
                .limit(100)
            )
        )
        if not subsets:
            return
        studies = {
            study.id: study
            for study in session.scalars(
                select(Study).where(
                    Study.id.in_({subset.study_id for subset in subsets})
                )
            )
        }
        points = {
            (dimension.subset_id, dimension.measurement_id): (
                dimension.point_id,
                measurement.calculated,
                measurement.output_type,
            )
            for dimension, measurement in session.execute(
                select(SubsetDimension, Measurement)
                .join(Measurement, Measurement.id == SubsetDimension.measurement_id)
                .where(SubsetDimension.subset_id.in_([subset.id for subset in subsets]))
            )
        }
        for subset, public in zip(
            subsets, subset_responses(session, subsets), strict=True
        ):
            study = studies[subset.study_id]
            record = {
                "study_sid": study.sid,
                "study_name": study.name,
                "subset_pk": subset.id,
                "subset_name": subset.name,
            }
            for axis, prefix in enumerate(("x", "y")):
                columns = defaultdict(list)
                for point in sorted(
                    (pair[axis] for pair in public["array"]),
                    key=lambda point: point["pk"],
                ):
                    values = {
                        "outputs_pk": point["pk"],
                        "intervention_pk": tuple(
                            item["pk"] for item in point["interventions"]
                        ),
                        "group_pk": point["group"].get("pk"),
                        "individual_pk": point["individual"].get("pk"),
                        "normed": point["normed"],
                        "calculated": points[subset.id, point["pk"]][1],
                        **science(point, labels=True, fields=("tissue", "method")),
                        "label": point["label"],
                        "output_type": points[subset.id, point["pk"]][2],
                        "time": point["time"],
                        "time_unit": point["time_unit"],
                        **science(
                            point,
                            labels=True,
                            fields=("measurement_type", "choice", "substance"),
                        ),
                        "dimension": axis,
                        "data_point": points[subset.id, point["pk"]][0],
                    }
                    # This spelling is part of the legacy scatter export contract.
                    values["measurement_type__label"] = values.pop(
                        "measurement_type_label"
                    )
                    for key, value in values.items():
                        columns[key].append(value)
                for key, values in columns.items():
                    record[f"{prefix}_{key}"] = collapse(
                        values, keep=key in {"time", "value", "mean", "median", "cv"}
                    )
            keys = (
                "outputs_pk",
                "intervention_pk",
                "group_pk",
                "individual_pk",
                "normed",
                "calculated",
                "tissue",
                "tissue_label",
                "method",
                "method_label",
                "label",
                "output_type",
                "time",
                "time_unit",
                "measurement_type",
                "measurement_type__label",
                "choice",
                "choice_label",
                "substance",
                "substance_label",
                "value",
                "mean",
                "median",
                "min",
                "max",
                "sd",
                "se",
                "cv",
                "unit",
                "dimension",
                "data_point",
            )
            order = [
                "study_sid",
                "study_name",
                "subset_pk",
                "subset_name",
                *(f"{axis}_{key}" for axis in ("x", "y") for key in keys),
            ]
            yield {key: record[key] for key in order}
        offset += len(subsets)
