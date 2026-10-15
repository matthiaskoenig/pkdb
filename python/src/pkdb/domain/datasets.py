"""Resolve dataset labels into explicit, unambiguous normalized point references."""

from collections import defaultdict
from collections.abc import Mapping, Sequence

from pkdb.domain.pharmacokinetics import build_timecourses
from pkdb.schemas.source import SourceLocation
from pkdb.schemas.study import CanonicalStudy, Measurement, Subset
from pkdb.schemas.validation import fail

SHARED_FIELDS = {
    "group",
    "individual",
    "time",
    "time_unit",
    "substance",
    "measurement_type",
    "calculation_type",
    "choice",
    "tissue",
    "method",
    "unit",
    "output_type",
}
STATISTICS_FIELDS = {
    "mean",
    "median",
    "min",
    "max",
    "sd",
    "se",
    "cv",
    "gmean",
    "gsd",
    "gcv",
    "count",
}
# The table row of an output: the outputs of one row of a format 1 sheet or of a
# format 2 scatters table are one point, so a subject can have several points.
ROW = "row"


def compile_datasets(study: CanonicalStudy) -> None:
    by_label = defaultdict(list)
    for record in study.measurements:
        if record.origin == "normalized" and record.label:
            by_label[record.label].append(record)
    existing_courses = {
        frozenset(point.key for point in course.points) for course in study.timecourses
    }
    dataset_names = set()
    for dataset in study.scatters:
        if dataset.name in dataset_names:
            fail("duplicate_dataset", "Duplicate dataset name", dataset.source)
        dataset_names.add(dataset.name)
        if dataset.data_type not in {"scatter", "timecourse"}:
            fail(
                "dataset_type", "Dataset must be scatter or timecourse", dataset.source
            )
        names = set()
        for index, subset in enumerate(dataset.subsets):
            if subset.name in names:
                fail("duplicate_subset", "Duplicate subset name", dataset.source)
            names.add(subset.name)
            labels = [dimension.output for dimension in subset.dimensions]
            expected = 2 if dataset.data_type == "scatter" else 1
            if [dimension.dimension for dimension in subset.dimensions] != [
                str(axis) for axis in range(expected)
            ]:
                fail(
                    "dataset_dimensions",
                    "Dataset dimension indices must be ordered from zero",
                    dataset.source,
                )
            if len(labels) != expected or len(set(labels)) != expected:
                fail(
                    "dataset_dimensions",
                    f"Expected {expected} distinct dimensions",
                    dataset.source,
                )
            if any(label not in by_label for label in labels):
                fail(
                    "dataset_label",
                    "Dataset refers to an absent output label",
                    dataset.source,
                )
            if dataset.data_type == "timecourse":
                selected = by_label[labels[0]]
                if len(selected) < 2 or len({p.time for p in selected}) != len(
                    selected
                ):
                    fail(
                        "timecourse_points",
                        "Timecourses require at least two distinct times",
                        dataset.source,
                    )
                clones = [
                    point.model_copy(
                        update={
                            "output_type": "timecourse",
                            "series_key": f"{dataset.key}:{index}",
                        }
                    )
                    for point in selected
                ]
                course = build_timecourses(clones)[0]
                originals = {point.key: point for point in selected}
                course.points = [originals[point.key] for point in course.points]
                subset.points = [[point.key] for point in course.points]
                identity = frozenset(originals)
                if identity not in existing_courses:
                    study.timecourses.append(course)
                    existing_courses.add(identity)
                continue
            subset.points = [
                [record.key for record in point]
                for point in scatter_points(subset, by_label, dataset.source)
            ]


def _shared(record: Measurement, field: str) -> object:
    """The value of a shared field of an output; `row` is the table row it is read from."""
    if field == ROW:
        source = record.source
        if source is None or source.row is None:
            return None
        return source.file, source.sheet, source.row
    return getattr(record.statistics if field in STATISTICS_FIELDS else record, field)


def scatter_points(
    subset: Subset,
    by_label: Mapping[str, Sequence[Measurement]],
    source: SourceLocation | None = None,
) -> list[list[Measurement]]:
    """The points of a scatter subset, one output of each dimension per point.

    The outputs of one point have the same values of the shared fields, so these
    must select exactly one output of each dimension.
    """
    if not subset.shared or set(subset.shared) - SHARED_FIELDS - STATISTICS_FIELDS - {
        ROW
    }:
        fail("scatter_shared", "Scatter requires recognized shared fields", source)
    labels = [dimension.output for dimension in subset.dimensions]
    grouped: dict[tuple, list[list[Measurement]]] = defaultdict(
        lambda: [[] for _ in labels]
    )
    for dimension, label in enumerate(labels):
        for record in by_label.get(label, ()):
            shared = tuple(_shared(record, field) for field in subset.shared)
            if any(value is None for value in shared):
                fail(
                    "scatter_shared",
                    "Scatter shared fields cannot be missing",
                    record.source,
                )
            grouped[shared][dimension].append(record)
    points = []
    for values in grouped.values():
        if any(len(items) != 1 for items in values):
            fail(
                "scatter_pairing",
                "Shared values must select exactly one output per dimension",
                source,
            )
        points.append([items[0] for items in values])
    return points


def add_generated_timecourses(study: CanonicalStudy) -> None:
    from pkdb.schemas.study import DataRecord, Dimension, Subset

    courses = [
        course
        for course in study.timecourses
        if course.points and course.points[0].origin == "normalized"
    ]
    if courses:
        study.scatters.append(
            DataRecord(
                key="dataset:auto",
                name="AutoGenerate",
                data_type="timecourse",
                subsets=[
                    Subset(
                        name=course.points[0].label or course.key,
                        dimensions=[
                            Dimension(
                                dimension="0", output=course.points[0].label or ""
                            )
                        ],
                    )
                    for course in courses
                ],
            )
        )
