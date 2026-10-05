"""Layer 3: required cells, statistics, times, schedules and units of single rows."""

import ast
import re
from collections.abc import Iterator
from functools import lru_cache
from typing import cast

from pkdb.domain.units import ureg
from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.cells import NOT_REPORTED
from pkdb.studyformat.issues import row_issue
from pkdb.studyformat.load import LoadedStudy, LoadedTable, Row

UNIT_PATTERN = re.compile(r"[\/^_*.() µα-ωΑ-Ωa-zA-Z0-9]*")
UNSPECIFIED = "unspecified summary"
SPREAD = ("sd", "se", "cv", "gmean", "gsd", "gcv", "median", "min", "max")
NUMERIC = (
    "mean",
    "sd",
    "se",
    "cv",
    "gmean",
    "gsd",
    "gcv",
    "median",
    "min",
    "max",
    "error_bar",
)
Issues = Iterator[ValidationIssue]


def _is_plain_number(text: str) -> bool:
    """True for text that is arithmetic on numbers only, such as `5`, `1.73` or `10^9`."""
    try:
        tree = ast.parse(text.replace("^", "**"), mode="eval")
    except Exception:
        return False
    return not any(isinstance(node, ast.Name) for node in ast.walk(tree))


@lru_cache(maxsize=4096)
def _parse_unit(unit: str):
    """The pint quantity of a unit text, or None when the text is no unit.

    Like the rest of the codebase this parses with `ureg(unit)`, so a numeric
    factor is part of a unit (`ml/min/(1.73*m^2)`, `10^9/l`, `1/h`). Pint also
    parses a bare number such as `5` as a dimensionless quantity, but that names
    no unit. Cell text is untrusted, and besides its own errors pint leaks those
    of its tokenizer and arithmetic (unbalanced parentheses, `1/0`, `*)`), so any
    exception means that the text is no unit.
    """
    if _is_plain_number(unit):
        return None
    try:
        quantity = ureg(unit)
    except Exception:
        return None
    return quantity if isinstance(quantity, ureg.Quantity) else None


@lru_cache(maxsize=1024)
def time_unit_status(unit: str) -> str:
    """`ok`, `dimension` (parses but is no time) or `invalid`; cached for large tables."""
    quantity = _parse_unit(unit)
    if quantity is None:
        return "invalid"
    return "ok" if quantity.check("[time]") else "dimension"


@lru_cache(maxsize=4096)
def unit_known(unit: str) -> bool:
    return _parse_unit(unit) is not None


def valid_unit(unit: str) -> bool:
    """Whether a unit text has supported characters and is a known unit."""
    return bool(UNIT_PATTERN.fullmatch(unit)) and unit_known(unit)


def subject_counts(study: LoadedStudy) -> dict[str, int | None]:
    return {
        row.cells["name"]: cast(int | None, row.values["count"])
        for _, row in study.rows("subjects")
        if row.cells["name"]
    }


def check_rows(study: LoadedStudy) -> list[ValidationIssue]:
    counts = subject_counts(study)
    issues: list[ValidationIssue] = []
    for table in study.tables:
        for row in table.rows:
            issues.extend(_required(table, row))
            if table.kind == "subjects":
                issues.extend(_subject(table, row))
            elif table.kind == "scatters":
                for prefix in ("x", "y"):
                    issues.extend(
                        _times(table, row, f"{prefix}_time", f"{prefix}_time_unit")
                    )
                    issues.extend(_unit(table, row, f"{prefix}_unit"))
            else:
                issues.extend(_statistics(table, row, counts))
                issues.extend(_error_bar(table, row))
                issues.extend(_ranges(table, row))
                issues.extend(_times(table, row, "time", "time_unit"))
                issues.extend(_unit(table, row, "unit"))
                if table.kind == "interventions":
                    issues.extend(_schedule(table, row))
    return issues


def _required(table: LoadedTable, row: Row) -> Issues:
    for name in sorted(table.spec.required_columns):
        if not row.cells[name]:
            yield row_issue(
                table,
                row,
                "missing_required",
                f"{name} is required in {table.kind} rows",
                name,
            )


def _subject(table: LoadedTable, row: Row) -> Issues:
    count = row.values["count"]
    if isinstance(count, int) and count < 1:
        yield row_issue(
            table, row, "invalid_count", "A subject count is at least 1", "count"
        )


def _statistics(table: LoadedTable, row: Row, counts: dict[str, int | None]) -> Issues:
    values = row.values
    count = values["count"]
    if count is None and isinstance(values["subjects"], str):
        count = counts.get(values["subjects"])
    if values["choice"] is not None:
        for name in NUMERIC:
            if values[name] is not None:
                yield row_issue(
                    table,
                    row,
                    "choice_statistics",
                    "A choice row has no numeric statistics; count holds the number of subjects with the choice",
                    name,
                )
    elif count == 1:
        for name in SPREAD:
            if values[name] is not None:
                yield row_issue(
                    table,
                    row,
                    "individual_statistics",
                    "A single subject has one value; enter it in mean",
                    name,
                )
    if values["calculation"] == UNSPECIFIED:
        for name in (*SPREAD, "error_bar"):
            if values[name] is not None:
                yield row_issue(
                    table,
                    row,
                    "unspecified_summary_statistics",
                    "An unspecified summary has only a mean",
                    name,
                )


def _error_bar(table: LoadedTable, row: Row) -> Issues:
    has_bar, has_type = bool(row.cells["error_bar"]), bool(row.cells["error_type"])
    if has_bar != has_type:
        missing = "error_bar" if has_type else "error_type"
        yield row_issue(
            table,
            row,
            "incomplete_error_bar",
            "error_bar and error_type are entered together",
            missing,
        )
        return
    kind = row.values["error_type"]
    if not isinstance(kind, str):
        return
    center = "gmean" if kind == "gsd" else "mean"
    if row.values[center] is None:
        yield row_issue(
            table,
            row,
            "incomplete_error_bar",
            f"An error bar of type {kind} needs {center}",
            center,
        )
    if row.values[kind] is not None:
        yield row_issue(
            table,
            row,
            "error_bar_conflict",
            f"{kind} is reported and also derived from error_bar; keep one",
            kind,
        )


def _ranges(table: LoadedTable, row: Row) -> Issues:
    values = row.values
    low, high = values["min"], values["max"]
    if isinstance(low, float) and isinstance(high, float):
        if low > high:
            yield row_issue(
                table, row, "reversed_range", f"min {low:g} exceeds max {high:g}", "min"
            )
        else:
            for name in ("mean", "median"):
                value = values[name]
                if isinstance(value, float) and not low <= value <= high:
                    yield row_issue(
                        table,
                        row,
                        "outside_range",
                        f"{name} lies outside [min, max]",
                        name,
                    )
    for name in ("sd", "se", "cv", "gcv"):
        value = values[name]
        if isinstance(value, float) and value < 0:
            yield row_issue(
                table, row, "invalid_statistic", f"{name} cannot be negative", name
            )
    gsd, gmean = values["gsd"], values["gmean"]
    if isinstance(gsd, float) and gsd < 1:
        yield row_issue(
            table, row, "invalid_statistic", "gsd is a factor of at least 1", "gsd"
        )
    if isinstance(gmean, float) and gmean <= 0:
        yield row_issue(
            table, row, "invalid_statistic", "gmean must be positive", "gmean"
        )


def _times(table: LoadedTable, row: Row, time: str, unit_column: str) -> Issues:
    values = row.values
    if table.kind == "timecourses" and values[time] == NOT_REPORTED:
        yield row_issue(
            table, row, "invalid_time", "Timecourse points need a numeric time", time
        )
    timed = [
        name
        for name in (time, "time_end", "interval")
        if name in values and values[name] not in (None, NOT_REPORTED)
    ]
    unit = row.cells[unit_column]
    if timed and not unit:
        yield row_issue(
            table,
            row,
            "missing_time_unit",
            f"{timed[0]} needs {unit_column}",
            unit_column,
        )
    if unit and unit != NOT_REPORTED:
        status = time_unit_status(unit)
        if status == "invalid":
            yield row_issue(
                table,
                row,
                "invalid_time_unit",
                f"Unknown time unit {unit!r}",
                unit_column,
            )
        elif status == "dimension":
            yield row_issue(
                table,
                row,
                "time_dimension",
                f"{unit} is not a unit of time",
                unit_column,
            )


def _unit(table: LoadedTable, row: Row, column: str) -> Issues:
    unit = row.cells[column]
    if not unit:
        return
    if not UNIT_PATTERN.fullmatch(unit):
        yield row_issue(
            table,
            row,
            "invalid_unit",
            f"Unit {unit!r} contains unsupported characters",
            column,
        )
    elif not unit_known(unit):
        yield row_issue(table, row, "invalid_unit", f"Unknown unit {unit!r}", column)


def _schedule(table: LoadedTable, row: Row) -> Issues:
    values = row.values
    times = values["time"]
    if isinstance(times, tuple) and len(times) > 1:
        for name in ("interval", "doses"):
            if values[name] is not None:
                yield row_issue(
                    table,
                    row,
                    "schedule_conflict",
                    "A ;-separated time list replaces interval and doses",
                    name,
                )
        return
    interval, doses, end = values["interval"], values["doses"], values["time_end"]
    if isinstance(interval, float):
        if interval <= 0:
            yield row_issue(
                table, row, "invalid_schedule", "interval must be positive", "interval"
            )
        if doses is None:
            yield row_issue(
                table,
                row,
                "invalid_schedule",
                "interval needs doses, the number of administrations",
                "doses",
            )
    if isinstance(doses, int):
        if doses < 1:
            yield row_issue(
                table, row, "invalid_schedule", "doses is at least 1", "doses"
            )
        elif doses > 1 and interval is None:
            yield row_issue(
                table,
                row,
                "invalid_schedule",
                "More than one dose needs an interval or a ;-separated time list",
                "interval",
            )
    if isinstance(end, float) and isinstance(times, tuple) and end < times[0]:
        yield row_issue(
            table, row, "invalid_schedule", "time_end lies before time", "time_end"
        )
