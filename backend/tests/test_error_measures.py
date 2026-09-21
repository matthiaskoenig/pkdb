"""Test the calculation of error measures."""

import numpy as np
import pytest

from pkdb_app.error_measures import calculate_cv, calculate_sd, calculate_se


def test_sd_from_se_and_count() -> None:
    """The standard deviation is se * sqrt(n)."""
    sd = calculate_sd(se=np.array([1.0]), count=np.array([4]), cv=None, mean=None)
    assert sd == pytest.approx([2.0])


def test_sd_from_cv_and_mean() -> None:
    """The standard deviation is cv * mean."""
    sd = calculate_sd(se=None, count=None, cv=np.array([0.5]), mean=np.array([10.0]))
    assert sd == pytest.approx([5.0])


def test_sd_missing_information() -> None:
    """Without se and count or cv and mean there is no standard deviation."""
    assert calculate_sd(se=np.array([1.0]), count=None, cv=None, mean=None) is None


def test_se_from_sd_and_count() -> None:
    """The standard error is sd / sqrt(n)."""
    se = calculate_se(sd=np.array([2.0]), count=np.array([4]), cv=None, mean=None)
    assert se == pytest.approx([1.0])


def test_se_from_cv_mean_and_count() -> None:
    """The standard error is cv * mean / sqrt(n)."""
    se = calculate_se(
        sd=None, count=np.array([4]), cv=np.array([0.5]), mean=np.array([10.0])
    )
    assert se == pytest.approx([2.5])


def test_cv_from_sd_and_mean() -> None:
    """The coefficient of variation is sd / mean."""
    cv = calculate_cv(sd=np.array([5.0]), count=None, se=None, mean=np.array([10.0]))
    assert cv == pytest.approx([0.5])


def test_cv_mean_zero_is_nan() -> None:
    """A mean of zero gives nan and not inf."""
    cv = calculate_cv(
        sd=np.array([5.0, 5.0]), count=None, se=None, mean=np.array([0.0, 10.0])
    )
    assert np.isnan(cv[0])
    assert cv[1] == pytest.approx(0.5)


def test_cv_does_not_change_mean() -> None:
    """The cleaning of the mean works on a copy."""
    mean = np.array([0.0, 10.0])
    calculate_cv(sd=np.array([5.0, 5.0]), count=None, se=None, mean=mean)
    assert mean[0] == 0.0
