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
    assert len(prepared.study.scatters) == 1
    dataset = prepared.study.scatters[0]
    assert dataset.name == "AutoGenerate"
    assert dataset.data_type == "timecourse"
    assert dataset.subsets[0].name == "curve"
    assert len(dataset.subsets[0].points) == 7
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


def test_same_label_across_source_templates_forms_one_course(exponential_course):
    for index, point in enumerate(exponential_course.points):
        point.series_key = f"template:{index % 2}"
    assert len(build_timecourses(exponential_course.points)) == 1


def test_single_point_cannot_form_a_timecourse(exponential_course):
    with pytest.raises(StudyValidationError):
        build_timecourses(exponential_course.points[:1])


@pytest.mark.parametrize(
    "unit,statistics", [("ml", {"value": 40.0}), ("mg", {"mean": 40.0})]
)
def test_unsupported_or_non_scalar_dose_preserves_dose_independent_pk(
    exponential_course, unit, statistics
):
    from pkdb.schemas.study import Intervention

    dose = Intervention(
        key="dose",
        name="dose",
        measurement_type="dosing",
        substance="drug",
        application="single dose",
        statistics=Statistics(**statistics),
        unit=unit,
        time=0,
        time_unit="h",
    )
    expected = derive_pk(exponential_course)
    actual = derive_pk(exponential_course, dose)
    assert actual == expected
    assert not {"clearance", "vd", "vd_ss"} & {
        record.measurement_type for record in actual
    }


def test_all_zero_curve_is_a_source_located_validation_error(exponential_course):
    from pkdb.schemas.source import SourceLocation

    for point in exponential_course.points:
        point.statistics.mean = 0
        point.source = SourceLocation(file="curve.tsv", row=2)
    with pytest.raises(StudyValidationError) as error:
        derive_pk(exponential_course)
    assert error.value.report.issues[0].code == "pk_zero_curve"
    source = error.value.report.issues[0].source
    assert source is not None and source.file == "curve.tsv"
    assert all(point.statistics.mean == 0 for point in exponential_course.points)
