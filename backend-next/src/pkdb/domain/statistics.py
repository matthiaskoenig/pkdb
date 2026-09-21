"""Helper functions for calculation of error measures from other errors.

sd is standard deviation
se is standard error (standard deviation of the mean) sd/sqrt(n)
cv is coefficient of variation. sd/mean
"""

import numpy as np


def _is(value):
    return value is not None and value is not np.nan


def calculate_sd(se, count, cv, mean):
    """Calculates standard deviation from other error measurements."""
    sd = None
    is_se = _is(se)
    is_count = _is(count)
    is_mean = _is(mean)
    is_cv = _is(cv)

    if is_se and is_count:
        sd = np.multiply(se, np.sqrt(count))
    elif is_cv and is_mean:
        sd = np.multiply(cv, mean)
    return sd


def calculate_se(sd, count, cv, mean):
    """Calculates SE from given fields."""
    se = None
    is_sd = _is(sd)
    is_count = _is(count)
    is_mean = _is(mean)
    is_cv = _is(cv)

    if is_sd and is_count:
        se = np.true_divide(sd, np.sqrt(count))
    elif is_count and is_mean and is_cv:
        se = np.true_divide((np.multiply(cv, mean)), np.sqrt(count))
    return se


def calculate_cv(sd, count, se, mean):
    """Calculates CV from given fields."""
    cv = None
    is_sd = _is(sd)
    is_count = _is(count)
    is_mean = _is(mean)
    is_se = _is(se)

    # mean can be zero, CV not calculatable, resulting in -inf/inf
    # mean data must be cleaned before calculation
    mean_clean = np.array(mean, dtype=float, copy=True)
    mean_clean[mean_clean == 0.0] = np.nan

    if is_sd and is_mean:
        cv = np.true_divide(sd, mean_clean)
    elif is_se and is_count and is_mean:
        cv = np.true_divide(np.multiply(se, np.sqrt(count)), mean_clean)

    return cv


def complete_statistics(statistics, count=None):
    """Fill missing error statistics while retaining reported values, including zero."""
    from pkdb.schemas.study import Statistics

    values = statistics.model_dump()
    effective_count = statistics.count if statistics.count is not None else count
    if effective_count is not None and effective_count <= 0:
        effective_count = None
    calculations = {
        "sd": lambda: calculate_sd(
            statistics.se, effective_count, statistics.cv, statistics.mean
        ),
        "se": lambda: calculate_se(
            statistics.sd, effective_count, statistics.cv, statistics.mean
        ),
        "cv": lambda: calculate_cv(
            statistics.sd, effective_count, statistics.se, statistics.mean
        ),
    }
    for field, calculate in calculations.items():
        if values[field] is None:
            result = calculate()
            if result is not None and np.isfinite(result):
                values[field] = float(result)
    return Statistics.model_validate(values)
