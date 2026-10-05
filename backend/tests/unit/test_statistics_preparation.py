"""Derived statistics and over-determination warnings in the preparation pipeline."""

import pytest

from pkdb.domain.validation import prepare_study
from pkdb.domain.vocabulary import MeasurementRule
from pkdb.schemas.study import Measurement, Statistics
from pkdb.schemas.validation import StudyValidationError

GCV_FOR_GSD_1_3 = 0.266945


def normalized(study, key):
    return next(
        record for record in study.measurements if record.key == f"{key}:normalized"
    )


def with_statistics(valid_study, **fields):
    valid_study.measurements[0].statistics = Statistics(**fields)
    return valid_study


def warnings(prepared, code="inconsistent_statistics"):
    return [issue for issue in prepared.report.issues if issue.code == code]


def test_gsd_completes_gcv_on_group_outputs(valid_study, vocabulary):
    prepared = prepare_study(with_statistics(valid_study, gsd=1.3), vocabulary)
    statistics = normalized(prepared.study, "m1").statistics
    assert statistics.gcv == pytest.approx(GCV_FOR_GSD_1_3, rel=1e-5)
    assert statistics.gsd == 1.3
    assert (statistics.sd, statistics.se, statistics.cv) == (None, None, None)


def test_error_bar_completes_arithmetic_statistics_with_the_group_count(
    valid_study, vocabulary
):
    study = with_statistics(valid_study, mean=10.0, error_bar=12.0, error_type="sd")
    statistics = normalized(prepare_study(study, vocabulary).study, "m1").statistics
    assert statistics.sd == 2.0
    assert statistics.se == 1.0
    assert statistics.cv == 0.2
    assert statistics.count == 4


def test_digitized_gsd_error_bar_is_scaled_and_completes_gsd_and_gcv(
    valid_study, vocabulary
):
    nanograms = vocabulary.model_copy(
        update={
            "measurements": (
                MeasurementRule(
                    name="concentration", units=("ng/ml",), time_required=True
                ),
                *vocabulary.measurements[1:],
            )
        }
    )
    study = with_statistics(
        valid_study, gmean=2.0, error_bar=2.6, error_type="gsd", cv=0.1
    )
    statistics = normalized(prepare_study(study, nanograms).study, "m1").statistics
    assert statistics.gmean == pytest.approx(2000)
    assert statistics.error_bar == pytest.approx(2600)
    assert statistics.gsd == pytest.approx(1.3)
    assert statistics.gcv == pytest.approx(GCV_FOR_GSD_1_3, rel=1e-5)
    assert statistics.cv == 0.1
    assert statistics.mean is None


def test_group_characteristic_gets_the_same_completion(valid_study, vocabulary):
    valid_study.groups[0].characteristica[0].statistics = Statistics(
        gcv=GCV_FOR_GSD_1_3
    )
    result = prepare_study(valid_study, vocabulary).study
    record = next(
        record
        for record in result.groups[0].characteristica
        if record.key == "c1:normalized"
    )
    assert record.statistics.gsd == pytest.approx(1.3, rel=1e-5)


def test_inconsistent_sd_and_se_are_reported_as_a_warning(valid_study, vocabulary):
    study = with_statistics(valid_study, mean=10.0, sd=1.0, se=1.0)
    prepared = prepare_study(study, vocabulary)
    assert prepared.report.valid
    (issue,) = warnings(prepared)
    assert issue.severity == "warning"
    assert issue.category == "scientific"
    assert issue.stage == "validate"
    assert "sd" in issue.message and "se" in issue.message
    assert issue.context["arithmetic"]["se"] == pytest.approx(2.0)
    assert prepared.report.warning_count == 1
    statistics = normalized(prepared.study, "m1").statistics
    assert (statistics.sd, statistics.se) == (1.0, 1.0)


def test_consistent_sd_and_se_do_not_warn(valid_study, vocabulary):
    study = with_statistics(valid_study, mean=10.0, sd=2.0, se=1.0)
    assert not warnings(prepare_study(study, vocabulary))


def test_inconsistent_gsd_and_gcv_are_reported_as_a_warning(valid_study, vocabulary):
    study = with_statistics(valid_study, gsd=1.3, gcv=0.5)
    (issue,) = warnings(prepare_study(study, vocabulary))
    assert "gsd" in issue.message and "gcv" in issue.message


def test_one_warning_per_record_even_when_both_families_disagree(
    valid_study, vocabulary
):
    study = with_statistics(valid_study, mean=10.0, sd=1.0, se=1.0, gsd=1.3, gcv=0.5)
    assert len(warnings(prepare_study(study, vocabulary))) == 1


def test_warning_points_to_the_source_record(valid_study, vocabulary):
    from pkdb.schemas.source import SourceLocation

    study = with_statistics(valid_study, mean=10.0, sd=1.0, se=1.0)
    study.measurements[0].source = SourceLocation(file="outputs.tsv", row=7)
    (issue,) = warnings(prepare_study(study, vocabulary))
    assert issue.source.row == 7


def test_warning_points_to_the_first_disagreeing_statistic(valid_study, vocabulary):
    from pkdb.schemas.source import SourceLocation

    study = with_statistics(valid_study, mean=10.0, sd=1.0, se=1.0)
    source = SourceLocation(file="outputs.tsv", sheet="outputs", row=7)
    source._columns.update(sd="O", se="P")
    source._headers.update(sd="sd", se="se")
    study.measurements[0].source = source
    (issue,) = warnings(prepare_study(study, vocabulary))
    assert issue.field == "sd"
    assert issue.source is not None
    assert (issue.source.row, issue.source.cell, issue.source.header) == (7, "O7", "sd")


def test_warning_survives_a_failed_preparation(valid_study, vocabulary):
    study = with_statistics(valid_study, mean=10.0, sd=1.0, se=1.0)
    study.measurements.append(
        Measurement(
            key="bad",
            measurement_type="concentration",
            group="missing",
            statistics=Statistics(mean=1.0),
            unit="mg/l",
            time=0.0,
            time_unit="h",
        )
    )
    with pytest.raises(StudyValidationError) as caught:
        prepare_study(study, vocabulary)
    codes = {issue.code for issue in caught.value.report.issues}
    assert {"unknown_group", "inconsistent_statistics"} <= codes


def test_records_without_the_new_fields_behave_as_before(valid_study, vocabulary):
    study = with_statistics(valid_study, mean=10.0, se=1.0)
    prepared = prepare_study(study, vocabulary)
    statistics = normalized(prepared.study, "m1").statistics
    assert (statistics.sd, statistics.cv) == (2.0, 0.2)
    assert not prepared.report.issues


def test_statistics_of_other_calculation_types_are_not_completed_or_checked(
    valid_study, vocabulary
):
    vocabulary = vocabulary.model_copy(
        update={"calculation_types": ("sample mean", "median")}
    )
    study = with_statistics(valid_study, gsd=1.3, sd=1.0, se=1.0, mean=10.0)
    study.measurements[0].calculation_type = "median"
    prepared = prepare_study(study, vocabulary)
    statistics = normalized(prepared.study, "m1").statistics
    assert statistics.gcv is None
    assert statistics.cv is None
    assert not warnings(prepared)
