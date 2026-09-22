"""Timecourse assembly and PK calculations with explicit source relationships."""

import hashlib
import math
from collections import defaultdict

import numpy as np
from pkpdutils import (
    AUCMethod,
    Dose,
    NCAOptions,
    Route,
    TerminalMethod,
    TerminalPhase,
    nca_single,
)
from pkpdutils import Timecourse as PKTimecourse

from pkdb.domain.units import ureg
from pkdb.schemas.study import Intervention, Measurement, Statistics, Timecourse
from pkdb.schemas.validation import fail

CONSISTENT_FIELDS = (
    "group",
    "individual",
    "substance",
    "tissue",
    "method",
    "measurement_type",
    "unit",
    "time_unit",
    "interventions",
)
DEFAULT_PK_DOSE_UNITS = ("g", "g/kg", "mol", "mol/kg")

PK_FIELDS = {
    "auc_last": "auc_end",
    "auc_inf_obs": "auc_inf",
    "cl": "clearance",
    "cl_f": "clearance",
    "cmax": "cmax",
    "lambda_z": "kel",
    "thalf": "thalf",
    "tmax": "tmax",
    "vz": "vd",
    "vz_f": "vd",
    "vss": "vd_ss",
}

EXTRAVASCULAR_ROUTES = frozenset(
    {
        "intraperitoneal-route",
        "intramuscular",
        "oral",
        "rectal",
        "inhalation",
        "buccal",
        "intradermal",
        "cutaneous",
        "transdermal",
        "vaginal",
        "topical",
        "intraduodenal",
        "subcutaneous",
        "sublingual",
    }
)


def _pk_dose(
    dose: Intervention | None, substance: str | None, time_unit: str, dose_units
) -> Dose | None:
    """Only use a scalar single dose with a known administration route.

    PK-DB's clearance and vd include apparent CL/F and Vz/F for extravascular
    routes. An unknown route cannot establish either IV or extravascular dosing.
    """
    if (
        dose is None
        or dose.application != "single dose"
        or dose.substance != substance
        or not dose.unit
        or dose.statistics.value is None
        or dose.statistics.value <= 0
        or not any(
            ureg.Unit(dose.unit).dimensionality == ureg.Unit(unit).dimensionality
            for unit in dose_units
        )
    ):
        return None
    time = 0.0
    if isinstance(dose.time, (int, float)) and dose.time_unit:
        time = float(ureg.Quantity(dose.time, dose.time_unit).to(time_unit).magnitude)
    duration = None
    if dose.route == "iv":
        route = Route.IV_BOLUS
        if dose.time_end is not None:
            if not isinstance(dose.time, (int, float)) or not dose.time_unit:
                return None
            duration = float(
                ureg.Quantity(dose.time_end - dose.time, dose.time_unit)
                .to(time_unit)
                .magnitude
            )
            if duration <= 0:
                return None
            route = Route.IV_INFUSION
    elif dose.route in EXTRAVASCULAR_ROUTES:
        route = Route.ORAL
    else:
        return None
    return Dose(
        amount=dose.statistics.value,
        unit=str(ureg.Unit(dose.unit)),
        route=route,
        time=time,
        duration=duration,
    )


def build_timecourses(points: list[Measurement]) -> list[Timecourse]:
    grouped = defaultdict(list)
    for point in points:
        if point.output_type == "timecourse":
            grouped[(point.label, point.origin)].append(point)
    courses = []
    for identity, series in grouped.items():
        first = series[0]
        if len(series) < 2 or len({point.time for point in series}) != len(series):
            fail(
                "timecourse_points",
                "Timecourses require at least two distinct times",
                first.source,
            )
        for point in series:
            if any(
                getattr(point, field) != getattr(first, field)
                for field in CONSISTENT_FIELDS
            ):
                fail(
                    "timecourse_metadata",
                    "Timecourse label combines inconsistent metadata",
                    point.source,
                )
            if point.time is None:
                fail(
                    "missing_time",
                    "Timecourse point requires a numeric time",
                    point.source,
                )
        key = hashlib.sha256(repr(identity).encode()).hexdigest()[:24]
        courses.append(
            Timecourse(
                key=f"timecourse:{key}",
                points=sorted(series, key=lambda point: point.time),
            )
        )
    return courses


def derive_pk(
    course: Timecourse,
    dose: Intervention | None = None,
    *,
    dose_units=DEFAULT_PK_DOSE_UNITS,
) -> list[Measurement]:
    points = course.points
    if not points or points[0].measurement_type != "concentration":
        return []
    first = points[0]
    if not first.time_unit or not first.unit:
        fail("pk_units", "PK requires concentration and time units", first.source)
    times: list[float] = []
    for point in points:
        if point.time is None:
            fail("timecourse_time", "PK requires numeric time points", point.source)
        times.append(point.time)
    if len(set(times)) != len(times):
        fail("timecourse_time", "PK requires unique numeric time points", first.source)
    statistic = next(
        (
            name
            for name in ("mean", "median", "value")
            if any(getattr(p.statistics, name) is not None for p in points)
        ),
        None,
    )
    if statistic is None:
        return []
    values = [getattr(point.statistics, statistic) for point in points]
    numeric = np.array([np.nan if value is None else value for value in values])
    if not np.any(numeric[np.isfinite(numeric)]):
        fail(
            "pk_zero_curve",
            "PK parameters cannot be calculated from an all-zero concentration curve",
            first.source,
        )
    calculated = nca_single(
        PKTimecourse(
            time=np.array(times, dtype=float),
            value=numeric,
            time_unit=str(ureg.Unit(first.time_unit)),
            unit=str(ureg.Unit(first.unit)),
            substance=first.substance or "substance",
            dose=_pk_dose(dose, first.substance, first.time_unit, dose_units),
        ),
        options=NCAOptions(
            # Keep PK-DB's integration and terminal-window policy explicit.
            auc_method=AUCMethod.LINEAR,
            terminal=TerminalPhase(method=TerminalMethod.ALL_AFTER_TMAX),
        ),
    )
    results = []
    for name, measurement_type in PK_FIELDS.items():
        if name not in calculated:
            continue
        parameter = calculated[name]
        value = float(parameter.item())
        if not math.isfinite(value):
            continue
        record = first.model_copy(deep=True)
        record.key = f"{course.key}:{measurement_type}"
        record.origin = "calculated"
        record.calculated = True
        record.calculation_type = None
        record.label = None
        record.series_key = None
        record.derived_from = course.key
        record.output_type = "output"
        record.measurement_type = measurement_type
        record.unit = parameter.attrs["units"]
        record.statistics = Statistics.model_validate({statistic: value})
        record.time = max(times) if name == "auc_last" else None
        record.time_unit = first.time_unit if name == "auc_last" else None
        record.time_not_reported = False
        record.time_unit_not_reported = False
        results.append(record)
    return results
