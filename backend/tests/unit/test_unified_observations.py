"""Characteristics and outputs share subject/statistical semantics."""

from pkdb.domain.validation import prepare_study
from pkdb.domain.vocabulary import MeasurementRule
from pkdb.schemas.study import Individual, Measurement, Observation, Statistics


def test_group_characteristic_and_output_complete_statistics_identically(
    valid_study, vocabulary
):
    vocabulary = vocabulary.model_copy(
        update={
            "measurements": (
                *vocabulary.measurements,
                MeasurementRule(name="weight", units=("kg",)),
            )
        }
    )
    characteristic = Observation(
        key="weight-characteristic",
        measurement_type="weight",
        unit="kg",
        statistics=Statistics(mean=80.0, sd=8.0),
    )
    valid_study.groups[0].characteristica.append(characteristic)
    valid_study.measurements.append(
        Measurement(
            **characteristic.model_dump(exclude={"key"}),
            key="weight-output",
            group="all",
        )
    )
    result = prepare_study(valid_study, vocabulary).study
    left = next(
        record
        for record in result.groups[0].characteristica
        if record.key == "weight-characteristic:normalized"
    )
    right = next(
        record
        for record in result.measurements
        if record.key == "weight-output:normalized"
    )
    assert left.statistics == right.statistics
    assert left.statistics.count == 4
    assert left.statistics.se == 4.0
    assert left.statistics.cv == 0.1


def test_individual_observations_keep_value_and_count_one(valid_study, vocabulary):
    vocabulary = vocabulary.model_copy(
        update={
            "measurements": (
                *vocabulary.measurements,
                MeasurementRule(name="weight", units=("kg",)),
            )
        }
    )
    record = Observation(
        key="individual-weight",
        measurement_type="weight",
        unit="kg",
        statistics=Statistics(value=80.0),
    )
    valid_study.individuals.append(
        Individual(key="person", name="person", group="all", characteristica=[record])
    )
    valid_study.measurements.append(
        Measurement(
            **record.model_dump(exclude={"key"}),
            key="individual-output",
            individual="person",
        )
    )
    result = prepare_study(valid_study, vocabulary).study
    left = result.individuals[0].characteristica[0]
    right = next(
        record for record in result.measurements if record.key == "individual-output"
    )
    assert left.statistics == right.statistics == Statistics(value=80.0, count=1)
    assert left.calculation_type is None and right.calculation_type is None


def test_observation_keys_cannot_collide_across_roles(valid_study, vocabulary):
    import pytest

    from pkdb.schemas.validation import StudyValidationError

    valid_study.measurements[0].key = valid_study.groups[0].characteristica[0].key
    with pytest.raises(StudyValidationError) as caught:
        prepare_study(valid_study, vocabulary)
    assert any(
        issue.code == "duplicate_identifier" and "observation" in issue.message
        for issue in caught.value.report.issues
    )
