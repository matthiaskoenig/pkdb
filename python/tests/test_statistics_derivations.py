"""Derived statistics checked against hand-calculated values."""

import math

import pytest

from pkdb.domain.normalization import SCALED_FIELDS, normalize_record
from pkdb.domain.statistics import complete_statistics, inconsistent_statistics
from pkdb.domain.vocabulary import MeasurementRule
from pkdb.schemas.study import Measurement, Statistics

# Hand calculation for gsd 1.3: ln(1.3) = 0.262364, its square 0.068835, exp(...) - 1 = 0.071262.
GCV_FOR_GSD_1_3 = 0.266945


def test_geometric_cv_is_derived_from_gsd():
    completed = complete_statistics(Statistics(gsd=1.3))
    assert completed.gcv == pytest.approx(GCV_FOR_GSD_1_3, rel=1e-5)
    assert completed.gsd == 1.3


def test_gsd_is_derived_from_geometric_cv_and_round_trips():
    completed = complete_statistics(Statistics(gcv=GCV_FOR_GSD_1_3))
    assert completed.gsd == pytest.approx(1.3, rel=1e-5)
    back = complete_statistics(Statistics(gsd=completed.gsd))
    assert back.gcv == pytest.approx(GCV_FOR_GSD_1_3, rel=1e-5)


def test_geometric_values_are_not_derived_without_a_valid_input():
    assert complete_statistics(Statistics(gmean=2.0)).gcv is None
    assert complete_statistics(Statistics(gmean=2.0)).gsd is None
    # A geometric standard deviation is a factor of at least one.
    assert complete_statistics(Statistics(gsd=0.5)).gcv is None
    assert complete_statistics(Statistics(gcv=-0.1)).gsd is None


def test_reported_geometric_values_are_never_overwritten():
    completed = complete_statistics(Statistics(gsd=1.3, gcv=0.5))
    assert (completed.gsd, completed.gcv) == (1.3, 0.5)


def test_geometric_statistics_never_feed_arithmetic_ones():
    completed = complete_statistics(
        Statistics(gmean=10.0, gsd=1.3, gcv=0.27, count=4), count=4
    )
    assert (completed.mean, completed.sd, completed.se, completed.cv) == (
        None,
        None,
        None,
        None,
    )


def test_arithmetic_statistics_never_feed_geometric_ones():
    completed = complete_statistics(Statistics(mean=10.0, sd=2.0, cv=0.2, count=4))
    assert (completed.gmean, completed.gsd, completed.gcv) == (None, None, None)


def test_arithmetic_statistics_complete_each_other_as_before():
    completed = complete_statistics(Statistics(mean=10.0, sd=2.0), count=4)
    assert completed.se == 1.0
    assert completed.cv == 0.2


@pytest.mark.parametrize("error_type", ["sd", "se"])
def test_error_bar_gives_the_arithmetic_field_of_its_type(error_type):
    completed = complete_statistics(
        Statistics(mean=10.0, error_bar=12.5, error_type=error_type)
    )
    assert getattr(completed, error_type) == 2.5


def test_error_bar_below_the_mean_uses_the_absolute_distance():
    completed = complete_statistics(
        Statistics(mean=10.0, error_bar=7.5, error_type="sd")
    )
    assert completed.sd == 2.5


def test_error_bar_sd_completes_the_other_arithmetic_fields():
    completed = complete_statistics(
        Statistics(mean=10.0, count=4, error_bar=12.0, error_type="sd")
    )
    assert completed.sd == 2.0
    assert completed.se == 1.0
    assert completed.cv == 0.2


def test_error_bar_se_completes_the_other_arithmetic_fields():
    completed = complete_statistics(
        Statistics(mean=10.0, count=4, error_bar=11.0, error_type="se")
    )
    assert completed.se == 1.0
    assert completed.sd == 2.0
    assert completed.cv == 0.2


def test_reported_sd_is_kept_when_the_error_bar_gives_another_value():
    completed = complete_statistics(
        Statistics(mean=10.0, sd=3.0, count=4, error_bar=12.0, error_type="sd")
    )
    assert completed.sd == 3.0
    assert completed.se == 1.5


def test_reported_zero_is_kept_against_the_error_bar():
    completed = complete_statistics(
        Statistics(mean=10.0, sd=0.0, error_bar=12.0, error_type="sd")
    )
    assert completed.sd == 0.0


def test_error_bar_gsd_above_the_geometric_mean_gives_the_ratio():
    completed = complete_statistics(
        Statistics(gmean=10.0, error_bar=13.0, error_type="gsd")
    )
    assert completed.gsd == pytest.approx(1.3)
    assert completed.gcv == pytest.approx(GCV_FOR_GSD_1_3, rel=1e-5)


def test_error_bar_gsd_below_the_geometric_mean_uses_the_inverse_ratio():
    completed = complete_statistics(
        Statistics(gmean=13.0, error_bar=10.0, error_type="gsd")
    )
    assert completed.gsd == pytest.approx(1.3)


@pytest.mark.parametrize(
    ("gmean", "error_bar"), [(0.0, 5.0), (5.0, 0.0), (-2.0, 5.0), (5.0, -2.0)]
)
def test_error_bar_gsd_needs_positive_values(gmean, error_bar):
    completed = complete_statistics(
        Statistics(gmean=gmean, error_bar=error_bar, error_type="gsd")
    )
    assert completed.gsd is None
    assert completed.gcv is None


def test_error_bar_gsd_is_kept_when_gsd_is_reported():
    completed = complete_statistics(
        Statistics(gmean=10.0, gsd=1.5, error_bar=13.0, error_type="gsd")
    )
    assert completed.gsd == 1.5


def test_error_bar_gsd_does_not_derive_arithmetic_fields():
    completed = complete_statistics(
        Statistics(mean=10.0, gmean=10.0, error_bar=13.0, error_type="gsd", count=4)
    )
    assert (completed.sd, completed.se, completed.cv) == (None, None, None)


def test_sd_error_bar_does_not_use_the_geometric_mean():
    completed = complete_statistics(
        Statistics(gmean=10.0, error_bar=12.0, error_type="sd")
    )
    assert completed.sd is None


@pytest.mark.parametrize(
    "statistics",
    [
        Statistics(mean=10.0, error_bar=12.0),
        Statistics(mean=10.0, error_type="sd"),
        Statistics(gmean=10.0, error_bar=13.0),
        Statistics(gmean=10.0, error_type="gsd"),
    ],
)
def test_incomplete_error_bar_information_is_ignored(statistics):
    assert complete_statistics(statistics, count=4) == statistics


def test_error_bar_without_the_matching_mean_is_ignored():
    completed = complete_statistics(Statistics(error_bar=12.0, error_type="sd"))
    assert completed.sd is None
    completed = complete_statistics(
        Statistics(mean=10.0, error_bar=12.0, error_type="gsd")
    )
    assert completed.gsd is None


def test_statistics_without_new_fields_complete_exactly_as_before():
    completed = complete_statistics(Statistics(mean=10.0, se=1.0), count=4)
    assert completed == Statistics(mean=10.0, se=1.0, sd=2.0, cv=0.2, count=None)


# Over-determination


def test_sd_and_se_that_disagree_are_inconsistent():
    result = inconsistent_statistics(Statistics(mean=10.0, sd=1.0, se=1.0, count=4))
    assert result is not None
    # Reported values and the implied standard deviations are kept apart.
    assert result.context == {
        "reported": {"sd": 1.0, "se": 1.0},
        "implied_sd": {"sd": 1.0, "se": 2.0},
        "implied_sigma_log": {},
        "disagreeing": [["sd", "se"]],
    }
    assert result.message == "sd is 1, but se 1 implies sd 2"
    assert result.field == "sd"


def test_sd_and_se_that_agree_are_consistent():
    assert inconsistent_statistics(Statistics(sd=2.0, se=1.0, count=4)) is None


def test_effective_count_argument_is_used_when_the_record_has_none():
    assert inconsistent_statistics(Statistics(sd=1.0, se=1.0), count=4)
    assert not inconsistent_statistics(Statistics(sd=2.0, se=1.0), count=4)


def test_cv_is_checked_against_sd_and_se():
    assert inconsistent_statistics(Statistics(mean=10.0, sd=2.0, cv=0.5, count=4))
    assert inconsistent_statistics(Statistics(mean=10.0, se=1.0, cv=0.5, count=4))
    assert not inconsistent_statistics(
        Statistics(mean=10.0, sd=2.0, se=1.0, cv=0.2, count=4)
    )


def test_message_names_only_the_disagreeing_pairs():
    # sd and cv agree; se disagrees with both.
    result = inconsistent_statistics(
        Statistics(mean=2.5, sd=0.5, se=1.0, cv=0.2, count=2)
    )
    assert result is not None
    assert result.disagreeing == [("sd", "se"), ("se", "cv")]
    assert result.message == (
        "sd is 0.5, but se 1 implies sd 1.414; "
        "se 1 implies sd 1.414, but cv 20% implies sd 0.5"
    )
    assert result.reported == {"sd": 0.5, "se": 1.0, "cv": 0.2}


def test_warning_is_placed_at_the_outlier_field():
    # se disagrees with sd and cv, which agree with each other.
    result = inconsistent_statistics(
        Statistics(mean=2.5, sd=0.5, se=1.0, cv=0.2, count=2)
    )
    assert result is not None and result.field == "se"
    # cv disagrees with sd and se.
    result = inconsistent_statistics(
        Statistics(mean=10.0, sd=2.0, se=1.0, cv=0.5, count=4)
    )
    assert result is not None and result.field == "cv"


def test_tie_prefers_the_error_bar_then_the_field_order():
    result = inconsistent_statistics(
        Statistics(mean=10.0, error_bar=12.0, error_type="sd", se=0.1, count=4)
    )
    assert result is not None and result.field == "error_bar"
    result = inconsistent_statistics(Statistics(se=1.0, cv=0.5, mean=10.0, count=4))
    assert result is not None and result.field == "se"


def test_negative_mean_converts_cv_with_its_magnitude():
    statistics = Statistics(mean=-10.0, sd=2.0, cv=0.2, count=4)
    assert inconsistent_statistics(statistics) is None
    assert complete_statistics(Statistics(mean=-10.0, cv=0.2), count=4).sd == 2.0
    assert complete_statistics(Statistics(mean=-10.0, sd=2.0), count=4).cv == 0.2


def test_error_bar_is_checked_against_reported_spreads():
    result = inconsistent_statistics(
        Statistics(mean=10.0, error_bar=12.0, error_type="sd", se=0.1, count=4)
    )
    assert result is not None
    assert result.message == "se 0.1 implies sd 0.2, but error_bar 12 (sd) implies sd 2"
    assert result.context == {
        "reported": {"se": 0.1, "error_bar": 12.0},
        "implied_sd": {"se": 0.2, "error_bar": 2.0},
        "implied_sigma_log": {},
        "disagreeing": [["se", "error_bar"]],
    }
    # A reported value is still checked against the error bar of its own type.
    result = inconsistent_statistics(
        Statistics(mean=10.0, sd=2.0, error_bar=40.0, error_type="sd", count=4)
    )
    assert result is not None
    assert result.message == "sd is 2, but error_bar 40 (sd) implies sd 30"
    # An se error bar implies the standard deviation with the count.
    assert not inconsistent_statistics(
        Statistics(mean=10.0, sd=2.0, error_bar=11.0, error_type="se", count=4)
    )


def test_error_bar_check_keeps_the_reported_value():
    statistics = Statistics(mean=10.0, sd=2.0, error_bar=40.0, error_type="sd")
    assert complete_statistics(statistics, count=4).sd == 2.0


def test_a_single_reported_arithmetic_field_cannot_be_inconsistent():
    assert not inconsistent_statistics(Statistics(mean=10.0, sd=2.0, count=4))
    assert not inconsistent_statistics(
        Statistics(mean=10.0, error_bar=12.0, error_type="sd", count=4)
    )


def test_arithmetic_check_needs_the_inputs_of_each_conversion():
    # se needs the count, cv needs the mean.
    assert not inconsistent_statistics(Statistics(sd=1.0, se=1.0))
    assert not inconsistent_statistics(Statistics(sd=1.0, cv=0.5, count=4))
    assert not inconsistent_statistics(Statistics(mean=0.0, sd=1.0, cv=0.5, count=4))
    assert not inconsistent_statistics(Statistics(sd=1.0, se=1.0, count=0))
    assert not inconsistent_statistics(
        Statistics(mean=10.0, sd=1.0, error_bar=40.0, error_type="se")
    )


def test_arithmetic_check_tolerates_two_percent_relative_difference():
    assert not inconsistent_statistics(Statistics(sd=2.0, se=1.01, count=4))
    assert not inconsistent_statistics(Statistics(sd=2.0, se=0.99, count=4))
    assert inconsistent_statistics(Statistics(sd=2.0, se=1.05, count=4))
    assert inconsistent_statistics(Statistics(sd=2.0, se=0.95, count=4))
    # Precise values: 2.04 implied sd against 2 differs by just under 2 percent.
    assert not inconsistent_statistics(Statistics(sd=2.0, se=1.02, count=4))
    assert inconsistent_statistics(Statistics(sd=2.0001, se=1.0215, count=4))


def test_rounding_of_the_reported_digits_is_tolerated():
    # se 0.3 means 0.25 to 0.35: sd 0.9 with a relative uncertainty of 0.05 / 0.3.
    assert not inconsistent_statistics(Statistics(sd=0.95, se=0.3, count=9))
    assert not inconsistent_statistics(Statistics(sd=1.05, se=0.3, count=9))
    # Just outside: 1.06 - 0.9 exceeds 0.15 + 0.005.
    result = inconsistent_statistics(Statistics(sd=1.06, se=0.3, count=9))
    assert result is not None
    assert result.message == "sd is 1.06, but se 0.3 implies sd 0.9"
    # More reported digits leave less room.
    assert inconsistent_statistics(Statistics(sd=0.95, se=0.300, count=9)) is None
    assert inconsistent_statistics(Statistics(sd=0.95, se=0.301, count=9))


def test_rounding_uncertainty_of_cv_includes_the_mean():
    # cv 7 % (6.5 to 7.5) of mean 3.0 (2.95 to 3.05) implies sd 0.21 with the
    # uncertainty 0.005 * 3 + 0.07 * 0.05 = 0.0185; sd 0.228 adds 0.0005.
    assert not inconsistent_statistics(Statistics(mean=3.0, cv=0.07, sd=0.228))
    assert inconsistent_statistics(Statistics(mean=3.0, cv=0.07, sd=0.231))
    # The percent conversion leaves floating noise that is not a reported digit.
    noisy = 7.0 / 100 / 100
    assert repr(noisy) != "0.0007"
    assert not inconsistent_statistics(Statistics(mean=300.0, cv=noisy, sd=0.215))


def test_zero_spread_reported_twice_is_consistent():
    assert not inconsistent_statistics(Statistics(sd=0.0, se=0.0, count=4))
    assert inconsistent_statistics(Statistics(sd=0.0, se=0.5, count=4))


def test_gsd_and_gcv_that_disagree_are_inconsistent():
    result = inconsistent_statistics(Statistics(gsd=1.3, gcv=0.5))
    assert result is not None
    # The geometric family compares the standard deviation of the logarithms,
    # sigma_log = ln(gsd); the message names the geometric SD.
    assert result.reported == {"gsd": 1.3, "gcv": 0.5}
    assert result.implied_sd == {}
    assert result.implied_sigma_log["gsd"] == pytest.approx(math.log(1.3))
    assert result.implied_sigma_log["gcv"] == pytest.approx(math.sqrt(math.log1p(0.25)))
    assert result.context["implied_sigma_log"] == result.implied_sigma_log
    assert result.message == "gsd is 1.3, but gcv 50% implies gsd 1.604"
    assert result.field == "gsd"


def test_geometric_family_compares_the_logarithmic_spread():
    # gsd 1.104 and gcv 11.55 % (gsd 1.122) differ by 1.6 percent as factors,
    # but by 14 percent in sigma_log; the reported digits leave little room.
    result = inconsistent_statistics(Statistics(gsd=1.104, gcv=0.1155))
    assert result is not None
    assert result.message == "gsd is 1.104, but gcv 11.55% implies gsd 1.122"
    # gsd 1.1 means 1.05 to 1.15 (sigma_log 0.049 to 0.14), which gcv 11.5 %
    # (sigma_log 0.115) meets.
    assert inconsistent_statistics(Statistics(gsd=1.1, gcv=0.115)) is None
    # A geometric error bar in log space: ln(2.6 / 2) is ln(1.3).
    assert (
        inconsistent_statistics(
            Statistics(gmean=2.0, error_bar=2.6, error_type="gsd", gsd=1.3)
        )
        is None
    )


def test_gsd_and_gcv_that_agree_are_consistent():
    assert not inconsistent_statistics(Statistics(gsd=1.3, gcv=0.267))
    assert not inconsistent_statistics(Statistics(gsd=1.3))
    assert not inconsistent_statistics(Statistics(gcv=0.3))


def test_geometric_error_bar_is_checked_against_gsd_and_gcv():
    # error_bar 2.6 around gmean 2 implies gsd 1.3, which gcv 26.7 % agrees with.
    statistics = Statistics(gmean=2.0, error_bar=2.6, error_type="gsd", gcv=0.267)
    assert inconsistent_statistics(statistics) is None
    result = inconsistent_statistics(
        Statistics(gmean=2.0, error_bar=2.6, error_type="gsd", gsd=1.6, gcv=0.267)
    )
    assert result is not None
    assert result.disagreeing == [("gsd", "gcv"), ("gsd", "error_bar")]
    assert result.field == "gsd"
    assert result.message == (
        "gsd is 1.6, but gcv 26.7% implies gsd 1.3; "
        "gsd is 1.6, but error_bar 2.6 (gsd) implies gsd 1.3"
    )


def test_geometric_and_arithmetic_families_are_reported_together():
    result = inconsistent_statistics(
        Statistics(mean=10.0, sd=1.0, se=1.0, gsd=1.3, gcv=0.5, count=4)
    )
    assert result is not None
    assert result.disagreeing == [("sd", "se"), ("gsd", "gcv")]


def test_arithmetic_and_geometric_values_are_not_compared_with_each_other():
    assert not inconsistent_statistics(Statistics(mean=10.0, sd=2.0, gsd=2.0, count=4))


# Unit scaling during normalization


def test_scaled_fields_cover_gmean_and_error_bar_but_not_dimensionless_ones():
    assert {"gmean", "error_bar"} <= set(SCALED_FIELDS)
    assert not {"gsd", "gcv", "cv"} & set(SCALED_FIELDS)


def test_normalization_scales_gmean_and_error_bar_but_not_gsd_or_gcv():
    raw = Measurement(
        key="m",
        measurement_type="concentration",
        statistics=Statistics(
            gmean=2.0, gsd=1.3, gcv=0.27, cv=0.25, error_bar=2.6, error_type="gsd"
        ),
        unit="mg/l",
    )
    normalized = normalize_record(
        raw, MeasurementRule(name="concentration", units=("ng/ml",))
    )
    assert normalized.statistics.gmean == pytest.approx(2000)
    assert normalized.statistics.error_bar == pytest.approx(2600)
    assert normalized.statistics.gsd == 1.3
    assert normalized.statistics.gcv == 0.27
    assert normalized.statistics.cv == 0.25
    assert normalized.statistics.error_type == "gsd"
    assert raw.statistics.gmean == 2.0
    assert raw.statistics.error_bar == 2.6


def test_gsd_derived_from_a_scaled_error_bar_is_unit_independent():
    raw = Measurement(
        key="m",
        measurement_type="concentration",
        statistics=Statistics(gmean=2.0, error_bar=2.6, error_type="gsd"),
        unit="mg/l",
    )
    normalized = normalize_record(
        raw, MeasurementRule(name="concentration", units=("ng/ml",))
    )
    completed = complete_statistics(normalized.statistics)
    assert completed.gsd == pytest.approx(1.3)
    assert completed.gcv == pytest.approx(GCV_FOR_GSD_1_3, rel=1e-5)
