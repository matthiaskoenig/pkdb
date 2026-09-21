"""Analytical PK values verify numerical integration without a database."""

import math

import pytest

from pkdb.domain.pharmacokinetics import build_timecourses, derive_pk
from pkdb.schemas.study import Measurement, Statistics, Timecourse
from pkdb.schemas.validation import StudyValidationError


@pytest.fixture
def exponential_course():
    return Timecourse(
        key="curve",
        points=[
            Measurement(
                key=f"p{i}",
                measurement_type="concentration",
                substance="drug",
                group="all",
                statistics=Statistics(mean=8.0 * math.exp(-0.5 * t)),
                unit="mg/l",
                time=float(t),
                time_unit="h",
                output_type="timecourse",
                label="curve",
                origin="normalized",
            )
            for i, t in enumerate([0, 1, 2, 3, 4, 6, 8])
        ],
    )


def test_terminal_half_life_and_zero_tmax_are_preserved(exponential_course):
    outputs = {
        record.measurement_type: record for record in derive_pk(exponential_course)
    }
    assert outputs["thalf"].statistics.mean == pytest.approx(
        math.log(2) / 0.5, rel=1e-6
    )
    assert outputs["cmax"].statistics.mean == 8
    assert outputs["tmax"].statistics.mean == 0
    assert all(record.origin == "calculated" for record in outputs.values())
    assert outputs["auc_end"].derived_from == "curve"


def test_course_builder_sorts_time_without_mutating_input(exponential_course):
    points = list(reversed(exponential_course.points))
    courses = build_timecourses(points)
    assert [p.time for p in courses[0].points] == [0, 1, 2, 3, 4, 6, 8]
    assert points[0].time == 8


def test_inconsistent_label_metadata_is_rejected(exponential_course):
    exponential_course.points[0].group = "other"
    with pytest.raises(StudyValidationError):
        build_timecourses(exponential_course.points)


def test_duplicate_times_do_not_silently_change_pk(exponential_course):
    exponential_course.points[1].time = 0
    with pytest.raises(StudyValidationError):
        derive_pk(exponential_course)


def test_preparation_derives_validated_pk_outputs(
    valid_study, vocabulary, exponential_course
):
    from pkdb.domain.validation import prepare_study
    from pkdb.domain.vocabulary import MeasurementRule

    rules = tuple(
        MeasurementRule(name=name, units=(unit,), time_required=name == "auc_end")
        for name, unit in [
            ("auc_end", "mg*h/l"),
            ("auc_inf", "mg*h/l"),
            ("cmax", "mg/l"),
            ("kel", "1/h"),
            ("thalf", "h"),
            ("tmax", "h"),
            ("clearance", "l/h"),
            ("vd", "l"),
            ("vd_ss", "l"),
        ]
    )
    vocabulary = vocabulary.model_copy(
        update={"measurements": vocabulary.measurements + rules}
    )
    valid_study.measurements = [
        point.model_copy(update={"origin": "reported"})
        for point in exponential_course.points
    ]
    prepared = prepare_study(valid_study, vocabulary)
    assert len(prepared.study.timecourses) == 2
    calculated = [p for p in prepared.study.measurements if p.origin == "calculated"]
    assert any(p.measurement_type == "thalf" for p in calculated)


def test_calculated_outputs_also_have_normalized_copies(
    valid_study, vocabulary, exponential_course
):
    from pkdb.domain.validation import prepare_study
    from pkdb.domain.vocabulary import MeasurementRule

    rules = tuple(
        MeasurementRule(name=name, units=(unit,))
        for name, unit in [
            ("auc_end", "mg*h/l"),
            ("auc_inf", "mg*h/l"),
            ("cmax", "mg/l"),
            ("kel", "1/h"),
            ("thalf", "h"),
            ("tmax", "h"),
        ]
    )
    vocabulary = vocabulary.model_copy(
        update={"measurements": vocabulary.measurements + rules}
    )
    valid_study.measurements = [
        point.model_copy(update={"origin": "reported"})
        for point in exponential_course.points
    ]
    prepared = prepare_study(valid_study, vocabulary)
    raw = next(
        record
        for record in prepared.study.measurements
        if record.origin == "calculated" and record.measurement_type == "thalf"
    )
    normalized = next(
        record
        for record in prepared.study.measurements
        if record.derived_from == raw.key
    )
    assert normalized.origin == "normalized"
    assert normalized.calculated
