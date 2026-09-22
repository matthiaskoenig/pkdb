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


def scalar_dose(**updates):
    from pkdb.schemas.study import Intervention

    return Intervention(
        key="dose",
        name="dose",
        measurement_type="dosing",
        substance="drug",
        application="single dose",
        statistics=Statistics(value=40),
        unit="mg",
        time=0,
        time_unit="h",
        route="oral",
    ).model_copy(update=updates)


def test_linear_auc_and_observed_terminal_extrapolation(exponential_course):
    import numpy as np

    outputs = {p.measurement_type: p for p in derive_pk(exponential_course)}
    points = exponential_course.points
    expected = np.trapezoid(
        [p.statistics.mean for p in points], [p.time for p in points]
    )
    assert outputs["auc_end"].statistics.mean == pytest.approx(expected)
    assert outputs["auc_inf"].statistics.mean == pytest.approx(
        expected + points[-1].statistics.mean / 0.5
    )
    assert outputs["auc_end"].time == 8


@pytest.mark.parametrize("route", ["oral", "subcutaneous", "iv"])
def test_route_specific_clearance_and_volume(exponential_course, route):
    outputs = {
        p.measurement_type: p
        for p in derive_pk(exponential_course, scalar_dose(route=route))
    }
    auc = outputs["auc_inf"].statistics.mean
    assert auc is not None
    clearance = 40 / auc
    assert outputs["clearance"].statistics.mean == pytest.approx(clearance)
    assert outputs["vd"].statistics.mean == pytest.approx(clearance / 0.5)
    assert ("vd_ss" in outputs) == (route == "iv")
    if route == "iv":
        import numpy as np

        times = np.array([p.time for p in exponential_course.points])
        values = np.array([p.statistics.mean for p in exponential_course.points])
        aumc = np.trapezoid(times * values, times) + values[-1] * (
            times[-1] / 0.5 + 1 / 0.5**2
        )
        assert outputs["vd_ss"].statistics.mean == pytest.approx(clearance * aumc / auc)


@pytest.mark.parametrize(
    "updates",
    [
        {"route": None},
        {"route": "nr-route"},
        {"route": "intraarterial"},
        {"application": "multiple doses"},
        {"substance": "other"},
        {"statistics": Statistics(value=0)},
    ],
)
def test_unestablished_dosing_keeps_dose_independent_outputs(
    exponential_course, updates
):
    assert derive_pk(exponential_course, scalar_dose(**updates)) == derive_pk(
        exponential_course
    )


def test_dose_time_units_and_infusion_duration(exponential_course):
    for point in exponential_course.points:
        point.time += 2
    outputs = {
        p.measurement_type: p
        for p in derive_pk(
            exponential_course,
            scalar_dose(route="iv", time=120, time_end=150, time_unit="min"),
        )
    }
    assert outputs["tmax"].statistics.mean == 0
    assert outputs["auc_end"].time == 10
    bolus = {
        p.measurement_type: p
        for p in derive_pk(exponential_course, scalar_dose(route="iv", time=2))
    }
    bolus_volume = bolus["vd_ss"].statistics.mean
    clearance = outputs["clearance"].statistics.mean
    assert bolus_volume is not None and clearance is not None
    assert outputs["vd_ss"].statistics.mean == pytest.approx(
        bolus_volume - clearance * 0.25
    )


def test_missing_statistic_and_short_terminal_curve_never_emit_nonfinite_values(
    exponential_course,
):
    exponential_course.points[2].statistics.mean = None
    outputs = derive_pk(exponential_course)
    assert outputs
    assert all(
        p.statistics.mean is not None and math.isfinite(p.statistics.mean)
        for p in outputs
    )
    exponential_course.points = exponential_course.points[:2]
    outputs = {p.measurement_type: p for p in derive_pk(exponential_course)}
    assert set(outputs) == {"auc_end", "cmax", "tmax"}


def test_bodyweight_normalized_dose_preserves_clearance_dimensions(exponential_course):
    from pkdb.domain.units import ureg

    outputs = {
        p.measurement_type: p
        for p in derive_pk(exponential_course, scalar_dose(unit="mg/kg"))
    }
    clearance = outputs["clearance"]
    volume = outputs["vd"]
    assert clearance.unit is not None and volume.unit is not None
    assert (
        ureg.Unit(clearance.unit).dimensionality == ureg.Unit("l/h/kg").dimensionality
    )
    assert ureg.Unit(volume.unit).dimensionality == ureg.Unit("l/kg").dimensionality


def test_terminal_regression_uses_all_post_peak_points(exponential_course):
    import numpy as np

    concentrations = [8, 5, 4, 2, 1.5, 0.4, 0.1]
    for point, value in zip(exponential_course.points, concentrations, strict=True):
        point.statistics.mean = value
    outputs = {p.measurement_type: p for p in derive_pk(exponential_course)}
    slope, _ = np.polyfit([1, 2, 3, 4, 6, 8], np.log(concentrations[1:]), 1)
    assert outputs["kel"].statistics.mean == pytest.approx(-slope)
