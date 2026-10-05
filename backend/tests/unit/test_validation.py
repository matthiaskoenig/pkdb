"""Scientific and graph validation run identically without any web/database framework."""

import pytest

from pkdb.domain.validation import prepare_study
from pkdb.domain.vocabulary import MeasurementRule
from pkdb.schemas.validation import StudyValidationError


def codes(error):
    return {issue.code for issue in error.value.report.issues}


def test_prepare_preserves_source_and_links_normalized_records(valid_study, vocabulary):
    before = valid_study.model_dump()
    prepared = prepare_study(valid_study, vocabulary)
    assert prepared.report.valid
    assert valid_study.model_dump() == before
    normalized = [m for m in prepared.study.measurements if m.origin == "normalized"]
    assert len(normalized) == 1
    assert normalized[0].derived_from == "m1"


def test_unknown_group_is_rejected(valid_study, vocabulary):
    valid_study.measurements[0].group = "missing"
    with pytest.raises(StudyValidationError) as error:
        prepare_study(valid_study, vocabulary)
    assert "unknown_group" in codes(error)


def test_unknown_intervention_subject_is_rejected(valid_study, vocabulary):
    valid_study.interventions[0].subject = "missing"
    with pytest.raises(StudyValidationError) as error:
        prepare_study(valid_study, vocabulary)
    issue = next(
        issue for issue in error.value.report.issues if issue.code == "unknown_subject"
    )
    assert (issue.field, issue.actual) == ("subject", "missing")
    assert issue.expected == {"defined_identifiers": ["all"]}


def test_intervention_subject_may_name_a_group(valid_study, vocabulary):
    valid_study.interventions[0].subject = "all"
    assert prepare_study(valid_study, vocabulary).report.valid


def test_cycles_are_rejected(valid_study, vocabulary):
    valid_study.groups[0].parent = "all"
    with pytest.raises(StudyValidationError) as error:
        prepare_study(valid_study, vocabulary)
    assert "group_cycle" in codes(error)


def test_unknown_vocabulary_and_negative_values_are_reported(valid_study, vocabulary):
    valid_study.measurements[0].statistics.mean = -1
    valid_study.measurements[0].substance = "absent"
    with pytest.raises(StudyValidationError) as error:
        prepare_study(valid_study, vocabulary)
    assert {"negative_value", "unknown_substance"} <= codes(error)


def test_unreported_time_is_allowed_but_missing_time_is_not(valid_study, vocabulary):
    valid_study.measurements[0].time = None
    with pytest.raises(StudyValidationError):
        prepare_study(valid_study, vocabulary)
    valid_study.measurements[0].time_not_reported = True
    assert prepare_study(valid_study, vocabulary).report.valid


def test_invalid_choice_is_rejected(valid_study, vocabulary):
    valid_study.groups[0].characteristica[0].choice = "unknown"
    with pytest.raises(StudyValidationError) as error:
        prepare_study(valid_study, vocabulary)
    assert "invalid_choice" in codes(error)


def test_dimension_mismatch_is_rejected(valid_study, vocabulary):
    valid_study.measurements[0].unit = "kg"
    with pytest.raises(StudyValidationError) as error:
        prepare_study(valid_study, vocabulary)
    assert "unit_dimension" in codes(error)


def test_error_limit_reports_truncation(valid_study, vocabulary):
    valid_study.measurements[0].group = "missing"
    valid_study.measurements[0].substance = "absent"
    with pytest.raises(StudyValidationError) as error:
        prepare_study(valid_study, vocabulary, max_issues=1)
    assert len(error.value.report.issues) == 1
    assert error.value.report.truncated


def test_warning_cap_cannot_hide_a_later_error(valid_study, vocabulary):
    valid_study.groups[0].characteristica[0].statistics.min = 2
    valid_study.groups[0].characteristica[0].statistics.max = 1
    valid_study.groups[0].characteristica[1].choice = "INVALID"
    with pytest.raises(StudyValidationError) as error:
        prepare_study(valid_study, vocabulary, max_issues=1)
    assert error.value.report.truncated
    assert not error.value.report.valid


def test_processing_version_is_nine():
    from pkdb.domain.validation import PROCESSING_VERSION

    assert PROCESSING_VERSION == "9"


def individual_output(valid_study):
    from pkdb.schemas.study import Individual

    valid_study.individuals.append(Individual(key="i1", name="person", group="all"))
    output = valid_study.measurements[0]
    output.group = None
    output.individual = "person"
    return output


def test_individual_output_carries_its_value_in_mean(valid_study, vocabulary):
    from pkdb.schemas.study import Statistics

    individual_output(valid_study).statistics = Statistics(mean=2)
    prepared = prepare_study(valid_study, vocabulary)
    assert prepared.report.valid
    assert [m.statistics.mean for m in prepared.study.measurements] == [2, 2]


@pytest.mark.parametrize(
    "statistics",
    [
        {"median": 1},
        {"min": 1},
        {"sd": 1},
        {"se": 1},
        {"cv": 1},
        {"gmean": 1},
        {"gsd": 1.2},
        {"gcv": 0.1},
        {"error_bar": 3},
        {"error_type": "sd"},
    ],
)
def test_individual_output_rejects_population_statistics(
    valid_study, vocabulary, statistics
):
    from pkdb.schemas.study import Statistics

    output = individual_output(valid_study)
    output.statistics = Statistics.model_validate({"mean": 2, **statistics})
    with pytest.raises(StudyValidationError) as error:
        prepare_study(valid_study, vocabulary)
    assert "individual_statistics" in codes(error)


def test_individual_output_rejects_calculation_type(valid_study, vocabulary):
    vocabulary = vocabulary.model_copy(update={"calculation_types": ("sample mean",)})
    individual_output(valid_study).calculation_type = "sample mean"
    with pytest.raises(StudyValidationError) as error:
        prepare_study(valid_study, vocabulary)
    assert "individual_statistics" in codes(error)


def test_dose_is_required_in_mean(valid_study, vocabulary):
    from pkdb.schemas.study import Statistics

    valid_study.interventions[0].statistics = Statistics(median=10)
    with pytest.raises(StudyValidationError) as error:
        prepare_study(valid_study, vocabulary)
    assert "missing_dose" in codes(error)


def test_individual_detection_limit_is_allowed(valid_study, vocabulary):
    from pkdb.schemas.study import Individual, Statistics

    valid_study.individuals.append(Individual(key="i1", name="person", group="all"))
    output = valid_study.measurements[0]
    output.group = None
    output.individual = "person"
    output.statistics = Statistics(max=2)
    assert prepare_study(valid_study, vocabulary).report.valid


def test_intervention_normalization_is_retained(valid_study, vocabulary):
    prepared = prepare_study(valid_study, vocabulary)
    normalized = [i for i in prepared.study.interventions if i.origin == "normalized"]
    assert len(normalized) == 1
    assert normalized[0].derived_from == valid_study.interventions[0].key


def test_group_statistics_and_default_calculation_match_legacy(valid_study, vocabulary):
    valid_study.measurements[0].statistics.sd = 1.0
    vocabulary = vocabulary.model_copy(update={"calculation_types": ("sample mean",)})
    prepared = prepare_study(valid_study, vocabulary)
    reported = prepared.study.measurements[0]
    assert reported.statistics.se is None
    assert reported.statistics.cv is None
    normalized = next(
        record
        for record in prepared.study.measurements
        if record.origin == "normalized"
    )
    assert normalized.statistics.se == 0.5
    assert normalized.statistics.cv == 0.5
    assert reported.calculation_type == "sample mean"
    assert valid_study.measurements[0].statistics.se is None


def test_explicit_zero_error_is_preserved(valid_study, vocabulary):
    valid_study.measurements[0].statistics.sd = 1.0
    valid_study.measurements[0].statistics.se = 0.0
    assert (
        prepare_study(valid_study, vocabulary).study.measurements[0].statistics.se == 0
    )


def test_unspecified_summary_is_explicit_and_has_no_statistical_completion(
    valid_study, vocabulary
):
    from pkdb.schemas.study import Statistics

    vocabulary = vocabulary.model_copy(
        update={"calculation_types": ("unspecified summary",)}
    )
    record = valid_study.measurements[0]
    record.statistics = Statistics(mean=2, sd=1)
    record.calculation_type = "unspecified summary"
    with pytest.raises(StudyValidationError) as error:
        prepare_study(valid_study, vocabulary)
    assert "unspecified_summary_statistics" in codes(error)
    record.statistics = Statistics(mean=2)
    prepared = prepare_study(valid_study, vocabulary)
    assert prepared.report.valid
    assert all(
        m.statistics.mean == 2 and m.statistics.sd is None and m.statistics.se is None
        for m in prepared.study.measurements
    )


@pytest.mark.parametrize(
    "statistics",
    [
        {"median": 1},
        {"min": 1},
        {"max": 3},
        {"se": 1},
        {"cv": 1},
        {"gmean": 1},
        {"gsd": 1.2},
        {"gcv": 0.1},
        {"error_bar": 3},
    ],
)
def test_unspecified_summary_has_only_a_mean(valid_study, vocabulary, statistics):
    from pkdb.schemas.study import Statistics

    record = valid_study.measurements[0]
    record.statistics = Statistics.model_validate({"mean": 2, **statistics})
    record.calculation_type = "unspecified summary"
    with pytest.raises(StudyValidationError) as error:
        prepare_study(valid_study, vocabulary)
    assert "unspecified_summary_statistics" in codes(error)


def test_unspecified_summary_characteristic_has_only_a_mean(valid_study, vocabulary):
    from pkdb.schemas.study import Observation, Statistics

    vocabulary = vocabulary.model_copy(
        update={
            "measurements": (
                *vocabulary.measurements,
                MeasurementRule(name="weight", units=("kg",)),
            )
        }
    )
    characteristic = Observation(
        key="weight",
        measurement_type="weight",
        unit="kg",
        calculation_type="unspecified summary",
        statistics=Statistics(mean=70, sd=5),
    )
    valid_study.groups[0].characteristica.append(characteristic)
    with pytest.raises(StudyValidationError) as error:
        prepare_study(valid_study, vocabulary)
    assert "unspecified_summary_statistics" in codes(error)
    characteristic.statistics = Statistics(mean=70)
    assert prepare_study(valid_study, vocabulary).report.valid


def test_unspecified_summary_is_accepted_without_a_vocabulary_term(
    valid_study, vocabulary
):
    from pkdb.schemas.study import Statistics

    assert "unspecified summary" not in vocabulary.calculation_types
    record = valid_study.measurements[0]
    record.statistics = Statistics(mean=2)
    record.calculation_type = "unspecified summary"
    prepared = prepare_study(valid_study, vocabulary)
    assert prepared.report.valid
    assert prepared.study.measurements[0].calculation_type == "unspecified summary"


def test_unspecified_summary_does_not_generate_pk(valid_study):
    from pkdb.domain.pharmacokinetics import derive_pk
    from pkdb.schemas.study import Statistics, Timecourse

    record = valid_study.measurements[0]
    record.statistics = Statistics(mean=2)
    record.calculation_type = "unspecified summary"
    course = Timecourse(key="opaque", points=[record])
    assert derive_pk(course) == []
