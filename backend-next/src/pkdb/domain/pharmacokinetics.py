"""Timecourse assembly and PK calculations with explicit source relationships."""

import hashlib
import math
from collections import defaultdict

import numpy as np

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
PK_FIELDS = {
    "auc": "auc_end",
    "aucinf": "auc_inf",
    "cl": "clearance",
    "cmax": "cmax",
    "kel": "kel",
    "thalf": "thalf",
    "tmax": "tmax",
    "vd": "vd",
    "vdss": "vd_ss",
}


def build_timecourses(points: list[Measurement]) -> list[Timecourse]:
    grouped = defaultdict(list)
    for point in points:
        if point.output_type == "timecourse":
            grouped[(point.series_key, point.label, point.origin)].append(point)
    courses = []
    for identity, series in grouped.items():
        first = series[0]
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
    course: Timecourse, dose: Intervention | None = None
) -> list[Measurement]:
    from pkdb_analysis.pk import pharmacokinetics

    points = course.points
    if not points or points[0].measurement_type != "concentration":
        return []
    first = points[0]
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
    time = ureg.Quantity(np.array(times, dtype=float), first.time_unit)
    concentration = ureg.Quantity(numeric, first.unit)
    substance = first.substance or "substance"
    if dose and dose.application == "single dose" and dose.substance == first.substance:
        magnitude = dose.statistics.value
        if magnitude is None or not dose.unit:
            fail(
                "missing_dose",
                "Single-dose PK requires a numeric dose and unit",
                dose.source,
            )
        dose_quantity = ureg.Quantity(magnitude, dose.unit)
        if isinstance(dose.time, (int, float)) and dose.time_unit:
            calculated = pharmacokinetics.TimecoursePK(
                time=time,
                concentration=concentration,
                substance=substance,
                ureg=ureg,
                dose=dose_quantity,
                intervention_time=ureg.Quantity(dose.time, dose.time_unit),
            ).pk
        else:
            calculated = pharmacokinetics.TimecoursePK(
                time=time,
                concentration=concentration,
                substance=substance,
                ureg=ureg,
                dose=dose_quantity,
            ).pk
    else:
        calculated = pharmacokinetics.TimecoursePKNoDosing(
            time=time,
            concentration=concentration,
            substance=substance,
            ureg=ureg,
        ).pk
    results = []
    for name, measurement_type in PK_FIELDS.items():
        quantity = getattr(calculated, name, None)
        if quantity is None or not math.isfinite(float(quantity.magnitude)):
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
        record.unit = str(quantity.units)
        record.statistics = Statistics.model_validate(
            {statistic: float(quantity.magnitude)}
        )
        record.time = max(times) if name == "auc" else None
        record.time_unit = first.time_unit if name == "auc" else None
        record.time_not_reported = False
        record.time_unit_not_reported = False
        results.append(record)
    return results
