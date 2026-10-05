"""Helper functions for calculation of error measures from other errors.

sd is standard deviation
se is standard error (standard deviation of the mean) sd/sqrt(n)
cv is coefficient of variation. sd/mean
gsd is the geometric standard deviation, a dimensionless factor of at least one
gcv is the geometric coefficient of variation as a fraction, sqrt(exp(ln(gsd)^2) - 1)

Arithmetic and geometric statistics are derived only from members of their own
family. A digitized error bar (error_bar with error_type) completes the missing
field of its type.
"""

import math
from itertools import combinations
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from pkdb.schemas.study import Statistics

# Reported statistics of one family agree when they differ by at most this share.
RELATIVE_TOLERANCE = 0.02


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


def calculate_gcv(gsd):
    """Geometric coefficient of variation (fraction) from the geometric standard deviation."""
    if gsd is None or not gsd >= 1:
        return None
    try:
        result = math.sqrt(math.expm1(math.log(gsd) ** 2))
    except OverflowError:
        return None
    return result if math.isfinite(result) else None


def calculate_gsd(gcv):
    """Geometric standard deviation from the geometric coefficient of variation (fraction)."""
    if gcv is None or not gcv >= 0:
        return None
    try:
        result = math.exp(math.sqrt(math.log1p(gcv**2)))
    except OverflowError:
        return None
    return result if math.isfinite(result) else None


def _effective_count(statistics, count):
    effective = statistics.count if statistics.count is not None else count
    return effective if effective is not None and effective > 0 else None


def _complete_from_error_bar(values):
    """Fill the field named by error_type from a digitized error bar, never overwriting."""
    error_bar, error_type = values["error_bar"], values["error_type"]
    if error_bar is None or error_type is None or values[error_type] is not None:
        return
    if error_type == "gsd":
        gmean = values["gmean"]
        if gmean is not None and gmean > 0 and error_bar > 0:
            result = max(error_bar / gmean, gmean / error_bar)
        else:
            return
    elif values["mean"] is not None:
        result = abs(error_bar - values["mean"])
    else:
        return
    if math.isfinite(result):
        values[error_type] = float(result)


def complete_statistics(statistics: Statistics, count: int | None = None) -> Statistics:
    """Fill missing error statistics while retaining reported values, including zero."""
    from pkdb.schemas.study import Statistics

    values = statistics.model_dump()
    effective_count = _effective_count(statistics, count)
    _complete_from_error_bar(values)
    known = dict(values)
    calculations = {
        "sd": lambda: calculate_sd(
            known["se"], effective_count, known["cv"], known["mean"]
        ),
        "se": lambda: calculate_se(
            known["sd"], effective_count, known["cv"], known["mean"]
        ),
        "cv": lambda: calculate_cv(
            known["sd"], effective_count, known["se"], known["mean"]
        ),
    }
    for field, calculate in calculations.items():
        if values[field] is None:
            result = calculate()
            if result is not None and np.isfinite(result):
                values[field] = float(result)
    if values["gcv"] is None:
        values["gcv"] = calculate_gcv(values["gsd"])
    elif values["gsd"] is None:
        values["gsd"] = calculate_gsd(values["gcv"])
    return Statistics.model_validate(values)


def _agree(left: float, right: float) -> bool:
    return abs(left - right) <= RELATIVE_TOLERANCE * max(abs(left), abs(right))


def inconsistent_statistics(
    statistics: Statistics, count: int | None = None
) -> dict[str, dict[str, float]]:
    """Reported statistics of one family that contradict each other.

    Over-determined records are compared in a common measure: the standard deviation
    implied by each reported sd, se (needs the count) and cv (needs a nonzero mean),
    and the geometric coefficient of variation implied by gsd against a reported gcv.
    The result maps each disagreeing family ("arithmetic", "geometric") to the implied
    value of every field that took part; it is empty when the record is consistent.
    """
    result = {}
    effective_count = _effective_count(statistics, count)
    implied = {}
    if statistics.sd is not None:
        implied["sd"] = statistics.sd
    if statistics.se is not None and effective_count is not None:
        implied["se"] = statistics.se * math.sqrt(effective_count)
    if statistics.cv is not None and statistics.mean:
        implied["cv"] = statistics.cv * statistics.mean
    if any(
        not _agree(left, right) for left, right in combinations(implied.values(), 2)
    ):
        result["arithmetic"] = implied
    gcv = calculate_gcv(statistics.gsd)
    if (
        gcv is not None
        and statistics.gcv is not None
        and not _agree(gcv, statistics.gcv)
    ):
        result["geometric"] = {"gsd": gcv, "gcv": statistics.gcv}
    return result
