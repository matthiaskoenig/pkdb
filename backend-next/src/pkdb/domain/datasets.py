"""Resolve dataset labels into explicit, unambiguous normalized point references."""

from collections import defaultdict

from pkdb.domain.pharmacokinetics import build_timecourses
from pkdb.schemas.study import CanonicalStudy
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
STATISTICS_FIELDS = {"value", "mean", "median", "min", "max", "sd", "se", "cv", "count"}


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
            if (
                not subset.shared
                or set(subset.shared) - SHARED_FIELDS - STATISTICS_FIELDS
            ):
                fail(
                    "scatter_shared",
                    "Scatter requires recognized shared fields",
                    dataset.source,
                )
            grouped = defaultdict(lambda: [[], []])
            for dimension, label in enumerate(labels):
                for record in by_label[label]:
                    shared = tuple(
                        getattr(
                            record.statistics if field in STATISTICS_FIELDS else record,
                            field,
                        )
                        for field in subset.shared
                    )
                    if any(value is None for value in shared):
                        fail(
                            "scatter_shared",
                            "Scatter shared fields cannot be missing",
                            record.source,
                        )
                    grouped[shared][dimension].append(record.key)
            subset.points = []
            for values in grouped.values():
                if any(len(items) != 1 for items in values):
                    fail(
                        "scatter_pairing",
                        "Shared values must select exactly one output per dimension",
                        dataset.source,
                    )
                subset.points.append([items[0] for items in values])


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
