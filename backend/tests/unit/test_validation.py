"""Scientific and graph validation run identically without any web/database framework."""

import pytest

from pkdb.domain.validation import prepare_study
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


def test_group_output_rejects_individual_value(valid_study, vocabulary):
    valid_study.measurements[0].statistics.value = 2
    with pytest.raises(StudyValidationError) as error:
        prepare_study(valid_study, vocabulary)
    assert "group_value" in codes(error)


@pytest.mark.parametrize("field", ["mean", "median", "min", "sd", "se", "cv"])
def test_individual_output_rejects_population_statistics(
    valid_study, vocabulary, field
):
    from pkdb.schemas.study import Individual, Statistics

    valid_study.individuals.append(Individual(key="i1", name="person", group="all"))
    output = valid_study.measurements[0]
    output.group = None
    output.individual = "person"
    output.statistics = Statistics(value=2, **{field: 1})
    with pytest.raises(StudyValidationError) as error:
        prepare_study(valid_study, vocabulary)
    assert "individual_statistics" in codes(error)


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
