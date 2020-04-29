"""
Helper functions for calculation of error measures from other errors.

    sd is standard deviation
    se is standard error (standard deviation of the mean) sd/sqrt(n)
    cv is coefficient of variation. sd/mean
"""
import numpy as np
import warnings


def calculate_sd(se, count, cv, mean):
    """Calculates standard deviation from other error measurements."""
    sd = None
    is_se = sd is not None
    is_count = count is not None
    is_mean = mean is not None
    is_cv = cv is not None

    if isinstance(se, list):
        se = list(map(float, se))
    if isinstance(mean, list):
        mean = list(map(float, mean))
    if isinstance(cv, list):
        cv = list(map(float, cv))

    if is_se and is_count:
        sd = np.multiply(se, np.sqrt(count))
    elif is_cv and is_mean:
        sd = np.multiply(cv, mean)
    return sd


def calculate_se(sd, count, cv, mean):
    """Calculates SE from given fields."""
    if isinstance(sd, list):
        sd = list(map(float, sd))
    if isinstance(mean, list):
        mean = list(map(float, mean))
    if isinstance(cv, list):
        cv = list(map(float, cv))

    se = None
    is_sd = sd is not None
    is_count = count is not None
    is_mean = mean is not None
    is_cv = cv is not None

    if is_sd and is_count:
        se = np.true_divide(sd, np.sqrt(count))
    elif is_count and is_mean and is_cv:
        se = np.true_divide((np.multiply(cv, mean)), np.sqrt(count))
    return se


def calculate_cv(sd, count, se, mean):
    """Calculates CV from given fields"""
    if isinstance(sd, list):
        sd = list(map(float, sd))
    if isinstance(mean, list):
        mean = list(map(float, mean))
    if isinstance(se, list):
        se = list(map(float, se))

    cv = None
    is_sd = sd is not None
    is_count = count is not None
    is_mean = mean is not None
    is_se = se is not None

    # mean can be zero, CV not calculatable, resulting in -inf/inf
    # mean data must be cleaned before calculation
    mean_clean = np.copy(mean)
    mean_clean[mean_clean == 0.0] = np.nan

    if is_sd and is_mean:
        cv = np.true_divide(sd, mean_clean)
    elif is_se and is_count and is_mean:
        cv = np.true_divide(np.multiply(se, np.sqrt(count)), mean_clean)

    return cv
