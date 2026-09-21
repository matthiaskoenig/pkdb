"""Unit and statistical regressions derived independently of the implementation."""

import numpy as np
import pytest

from pkdb.domain.normalization import normalize_record
from pkdb.domain.statistics import calculate_cv, calculate_sd, calculate_se
from pkdb.domain.units import convert_value, ureg
from pkdb.domain.vocabulary import MeasurementRule
from pkdb.schemas.study import Measurement, Statistics


def test_standard_deviation_from_standard_error():
    assert calculate_sd(
        se=np.array([1.0]), count=np.array([4]), cv=None, mean=None
    ) == pytest.approx([2.0])


def test_standard_error_from_standard_deviation():
    assert calculate_se(
        sd=np.array([2.0]), count=np.array([4]), cv=None, mean=None
    ) == pytest.approx([1.0])


def test_coefficient_of_variation_preserves_source_and_zero_semantics():
    means = np.array([0.0, 10.0])
    cv = calculate_cv(sd=np.array([5.0, 5.0]), count=None, se=None, mean=means)
    assert np.isnan(cv[0])
    assert cv[1] == pytest.approx(0.5)
    assert means.tolist() == [0.0, 10.0]


def test_missing_error_information_is_not_fabricated():
    assert calculate_sd(se=np.array([1.0]), count=None, cv=None, mean=None) is None


def test_mass_and_concentration_conversion():
    assert convert_value(1, "mg", "ug") == pytest.approx(1000)
    assert convert_value(1, "mg/l", "ug/ml") == pytest.approx(1)


@pytest.mark.parametrize("unit", ["cups", "beverages", "none"])
def test_custom_count_units(unit):
    assert convert_value(2, unit, "count") == pytest.approx(2)


def test_percent_and_distinct_activity_dimension():
    assert convert_value(50, "percent", "count") == pytest.approx(0.5)
    assert not ureg.Quantity(1, "IU").dimensionless


def test_normalization_preserves_raw_values_and_dimensionless_cv():
    raw = Measurement(
        key="m",
        measurement_type="concentration",
        statistics=Statistics(mean=2.0, sd=0.5, cv=0.25),
        unit="mg/l",
    )
    rule = MeasurementRule(name="concentration", units=("ng/ml",))
    norm = normalize_record(raw, rule)
    assert norm.statistics.mean == pytest.approx(2000)
    assert norm.statistics.sd == pytest.approx(500)
    assert norm.statistics.cv == 0.25
    assert norm.derived_from == "m"
    assert norm.origin == "normalized"
    assert raw.statistics.mean == 2.0
    assert raw.unit == "mg/l"


def test_molar_normalization_uses_explicit_substance_mass():
    raw = Measurement(
        key="m",
        measurement_type="concentration",
        substance="drug",
        statistics=Statistics(mean=1.0),
        unit="umol/l",
    )
    norm = normalize_record(
        raw, MeasurementRule(name="concentration", units=("mg/l",)), molar_mass=500.0
    )
    assert norm.statistics.mean == pytest.approx(0.5)


def test_scaled_body_surface_unit_normalizes_to_unscaled_units():
    raw = Measurement(
        key="gfr",
        measurement_type="gfr",
        statistics=Statistics(mean=80.7),
        unit="ml/min/(1.73*m^2)",
    )
    normalized = normalize_record(
        raw, MeasurementRule(name="gfr", units=("ml/min/(1.73*m^2)",))
    )
    assert normalized.statistics.mean == pytest.approx(80.7 / 1.73)
    assert normalized.statistics.mean is not None
    assert ureg.Quantity(normalized.statistics.mean, normalized.unit).to(
        "ml/min/m^2"
    ).magnitude == pytest.approx(80.7 / 1.73)


def test_normalization_overflow_is_a_validation_error():
    from pkdb.schemas.validation import StudyValidationError

    raw = Measurement(
        key="m", measurement_type="amount", statistics=Statistics(mean=1e308), unit="kg"
    )
    with pytest.raises(StudyValidationError):
        normalize_record(raw, MeasurementRule(name="amount", units=("ng",)))
