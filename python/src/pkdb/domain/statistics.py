"""Helper functions for calculation of error measures from other errors.

sd is standard deviation
se is standard error (standard deviation of the mean) sd/sqrt(n)
cv is coefficient of variation. sd/abs(mean)
gsd is the geometric standard deviation, a dimensionless factor of at least one
gcv is the geometric coefficient of variation as a fraction, sqrt(exp(ln(gsd)^2) - 1)

Arithmetic and geometric statistics are derived only from members of their own
family. A digitized error bar (error_bar with error_type) completes the missing
field of its type.
"""

import math
from dataclasses import dataclass
from decimal import Decimal
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
        sd = np.multiply(cv, np.abs(mean))
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
        se = np.true_divide((np.multiply(cv, np.abs(mean))), np.sqrt(count))
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
    mean_clean = np.array(np.abs(np.array(mean, dtype=float)), dtype=float)
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


def _from_error_bar(values) -> float | None:
    """The value of the field named by error_type that a digitized error bar gives."""
    error_bar, error_type = values["error_bar"], values["error_type"]
    if error_bar is None or error_type is None:
        return None
    if error_type == "gsd":
        gmean = values["gmean"]
        if gmean is None or not gmean > 0 or not error_bar > 0:
            return None
        result = max(error_bar / gmean, gmean / error_bar)
    elif values["mean"] is not None:
        result = abs(error_bar - values["mean"])
    else:
        return None
    return float(result) if math.isfinite(result) else None


def _complete_from_error_bar(values):
    """Fill the field named by error_type from a digitized error bar, never overwriting."""
    error_type = values["error_type"]
    if error_type is not None and values[error_type] is None:
        values[error_type] = _from_error_bar(values)


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


# The fields that imply a spread, in the order that breaks ties of the outlier
# after the error bar.
_ORDER = ("sd", "se", "cv", "gsd", "gcv", "error_bar")
# The fields given in percent in study format 2 and as fractions in the model.
_PERCENT = frozenset({"cv", "gcv"})


def _half_unit(value: float) -> float:
    """Half a unit of the last decimal place of a reported value.

    The place comes from the shortest decimal representation (repr) of the
    value, rounded to 15 significant digits first, so that the noise of a
    conversion such as percent to fraction does not count as a reported digit.
    """
    exponent = Decimal(repr(float(f"{value:.15g}"))).as_tuple().exponent
    return 0.5 * 10.0 ** int(exponent)


def _text(value: float, digits: int = 15) -> str:
    return f"{float(f'{value:.{digits}g}'):.15g}"


@dataclass(frozen=True)
class _Implied:
    """The spread one reported field implies, with its rounding uncertainty."""

    family: str
    value: float
    uncertainty: float
    reported: float
    label: str


def _gsd_uncertainty(gcv: float, gsd: float) -> float:
    # d gsd / d gcv of gsd = exp(sqrt(ln(1 + gcv^2))); it tends to gsd for gcv -> 0.
    if gcv == 0:
        return gsd
    return gsd * gcv / ((1 + gcv**2) * math.sqrt(math.log1p(gcv**2)))


def _implied_spreads(statistics: Statistics, count: int | None) -> dict[str, _Implied]:
    # The standard deviation implied by each reported arithmetic field, or the
    # geometric standard deviation implied by each geometric field.
    implied: dict[str, _Implied] = {}
    sd, se, cv, mean = statistics.sd, statistics.se, statistics.cv, statistics.mean
    gsd, gcv, gmean = statistics.gsd, statistics.gcv, statistics.gmean

    def add(field, family, value, uncertainty, reported, label=None):
        if math.isfinite(value) and math.isfinite(uncertainty):
            shown = (
                _text(reported * 100) + "%" if field in _PERCENT else _text(reported)
            )
            implied[field] = _Implied(
                family, value, uncertainty, reported, label or f"{field} {shown}"
            )

    if sd is not None:
        add("sd", "arithmetic", sd, _half_unit(sd), sd)
    if se is not None and count is not None:
        root = math.sqrt(count)
        add("se", "arithmetic", se * root, _half_unit(se) * root, se)
    if cv is not None and mean:
        add(
            "cv",
            "arithmetic",
            cv * abs(mean),
            _half_unit(cv) * abs(mean) + abs(cv) * _half_unit(mean),
            cv,
        )
    if gsd is not None and gsd >= 1:
        add("gsd", "geometric", gsd, _half_unit(gsd), gsd)
    if gcv is not None and (value := calculate_gsd(gcv)) is not None:
        add(
            "gcv",
            "geometric",
            value,
            _gsd_uncertainty(gcv, value) * _half_unit(gcv),
            gcv,
        )
    error_type, error_bar = statistics.error_type, statistics.error_bar
    derived = _from_error_bar(statistics.model_dump())
    if derived is None or error_type is None or error_bar is None:
        return implied
    label = f"error_bar {_text(error_bar)} ({error_type})"
    if error_type == "gsd" and gmean is not None:
        relative = _half_unit(error_bar) / error_bar + _half_unit(gmean) / gmean
        add("error_bar", "geometric", derived, derived * relative, error_bar, label)
    elif mean is not None and (error_type == "sd" or count is not None):
        root = math.sqrt(count) if error_type == "se" and count is not None else 1.0
        uncertainty = (_half_unit(error_bar) + _half_unit(mean)) * root
        add("error_bar", "arithmetic", derived * root, uncertainty, error_bar, label)
    return implied


def _disagree(left: _Implied, right: _Implied) -> bool:
    # Rounding of the reported digits can explain a difference up to the sum
    # of the propagated uncertainties.
    difference = abs(left.value - right.value)
    larger = max(abs(left.value), abs(right.value))
    return difference > max(
        RELATIVE_TOLERANCE * larger, left.uncertainty + right.uncertainty
    )


@dataclass(frozen=True)
class Inconsistency:
    """Reported statistics of a record that contradict each other."""

    # The reported value of each field that implies a spread.
    reported: dict[str, float]
    # The standard deviation each field implies, or the geometric standard
    # deviation for gsd, gcv and an error bar of type gsd.
    implied_sd: dict[str, float]
    # The pairs of fields whose implied spreads disagree.
    disagreeing: list[tuple[str, str]]
    # The field that disagrees with the most others, where the warning is placed.
    field: str
    message: str

    @property
    def context(self) -> dict:
        return {
            "reported": self.reported,
            "implied_sd": self.implied_sd,
            "disagreeing": [list(pair) for pair in self.disagreeing],
        }


def inconsistent_statistics(
    statistics: Statistics, count: int | None = None
) -> Inconsistency | None:
    """Reported statistics of a record that contradict each other, or None.

    Each reported sd, se (needs the count), cv (needs a nonzero mean) and
    error bar of type sd or se implies a standard deviation; each gsd, gcv and
    error bar of type gsd implies a geometric standard deviation. Two implied
    values of a family disagree when they differ by more than 2 percent of the
    larger one and by more than the sum of their rounding uncertainties: half a
    unit of the last decimal place of each reported value, propagated through
    the conversion. The families are never compared with each other.
    """
    implied = _implied_spreads(statistics, _effective_count(statistics, count))
    fields = sorted(implied, key=_ORDER.index)
    pairs = [
        (left, right)
        for left, right in combinations(fields, 2)
        if implied[left].family == implied[right].family
        and _disagree(implied[left], implied[right])
    ]
    if not pairs:
        return None
    disagreements = {field: sum(field in pair for pair in pairs) for field in fields}
    most = max(disagreements.values())
    tied = [field for field in fields if disagreements[field] == most]
    outlier = "error_bar" if "error_bar" in tied else tied[0]

    def claim(field: str) -> str:
        spread = "gsd" if implied[field].family == "geometric" else "sd"
        if field == spread:
            return f"{spread} is {_text(implied[field].reported)}"
        return (
            f"{implied[field].label} implies {spread} {_text(implied[field].value, 4)}"
        )

    return Inconsistency(
        reported={field: implied[field].reported for field in fields},
        implied_sd={field: implied[field].value for field in fields},
        disagreeing=pairs,
        field=outlier,
        message="; ".join(
            f"{claim(left)}, but {claim(right)}" for left, right in pairs
        ),
    )
