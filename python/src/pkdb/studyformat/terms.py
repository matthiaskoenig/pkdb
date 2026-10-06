"""Layer 5: vocabulary terms, choices, signs, required times and units."""

from collections.abc import Callable, Iterator
from difflib import get_close_matches
from functools import cache, lru_cache

from pkdb.domain.normalization import UnitDimensionError, conversion
from pkdb.domain.vocabulary import MeasurementRule, Vocabulary
from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.columns import Column
from pkdb.studyformat.issues import row_issue
from pkdb.studyformat.load import LoadedStudy, LoadedTable, Row
from pkdb.studyformat.rows import valid_unit

RETIRED_CALCULATION = "geometric mean"
UNSPECIFIED = "unspecified summary"
NO_UNIT = "NO_UNIT"
DOSING = frozenset({"dosing", "medication"})
DOSING_APPLICATIONS = ("single dose", "multiple dose", "constant infusion")
# Columns a dose needs, in template order; dosing needs all, medication some.
DOSING_FIELDS = {
    "dosing": (
        "substance",
        "route",
        "form",
        "application",
        "time",
        "time_unit",
        "unit",
    ),
    "medication": ("substance", "route", "unit"),
}
CHOICE_TYPES = frozenset({"categorical", "boolean", "numeric_categorical"})
REQUIRED_CHOICE_TYPES = frozenset({"categorical", "boolean"})
TIMED_KINDS = frozenset({"characteristica", "outputs", "timecourses", "scatters"})
OBSERVATION_KINDS = frozenset({"characteristica", "outputs", "timecourses"})
VALUE_TYPES = frozenset({"numeric", "numeric_categorical"})
CENTRAL = ("mean", "gmean", "median", "min", "max")
VALUES = (*CENTRAL, "error_bar")
CODES = {
    "measurements": "unknown_measurement",
    "substances": "unknown_substance",
    "tissues": "unknown_tissue",
    "methods": "unknown_method",
    "routes": "unknown_route",
    "forms": "unknown_form",
    "applications": "unknown_application",
    "calculation_types": "unknown_calculation",
}
Issues = Iterator[ValidationIssue]


def vocabulary_terms(vocabulary: Vocabulary) -> dict[str, frozenset[str]]:
    """Names of the allowed terms of every vocabulary kind.

    The retired calculation type is not allowed and `unspecified summary` is.
    """
    return {
        "measurements": frozenset(rule.name for rule in vocabulary.measurements),
        "substances": frozenset(substance.name for substance in vocabulary.substances),
        "tissues": frozenset(vocabulary.tissues),
        "methods": frozenset(vocabulary.methods),
        "routes": frozenset(vocabulary.routes),
        "forms": frozenset(vocabulary.forms),
        "applications": frozenset(vocabulary.applications),
        "calculation_types": (
            frozenset(vocabulary.calculation_types) - {RETIRED_CALCULATION}
        )
        | {UNSPECIFIED},
    }


@lru_cache(maxsize=4096)
def converts(unit: str, units: tuple[str, ...], molar_mass: float | None) -> bool:
    """Whether a unit converts to one of a rule's units; cached for large tables."""
    try:
        conversion(unit, units, molar_mass)
    except UnitDimensionError:
        return False
    except Exception:
        # Not a readable unit; layer 3 reports it as invalid_unit.
        return True
    return True


def check_terms(study: LoadedStudy, vocabulary: Vocabulary) -> list[ValidationIssue]:
    """Check the vocabulary terms, measurement rules, units and values of every row."""
    terms = vocabulary_terms(vocabulary)
    rules = vocabulary.measurement_map()
    masses = {substance.name: substance.mass for substance in vocabulary.substances}
    ordered = {kind: sorted(values) for kind, values in terms.items()}

    @cache
    def suggest(value: str, kind: str) -> tuple[str, ...]:
        # A misspelled term often repeats in many rows; match it once.
        return tuple(get_close_matches(value, ordered[kind], n=10, cutoff=0.6))

    issues: list[ValidationIssue] = []
    for table in study.tables:
        columns = [column for column in table.spec.columns if column.vocabulary]
        prefixes: tuple[str, ...] = (
            ("x_", "y_")
            if table.kind == "scatters"
            else ()
            if table.kind == "subjects"
            else ("",)
        )
        for row in table.rows:
            found: list[ValidationIssue] = []
            for column in columns:
                found.extend(_term(table, row, column, terms, suggest))
            for prefix in prefixes:
                rule = rules.get(row.cells[f"{prefix}measurement"])
                if rule is not None:
                    found.extend(_measurement(table, row, rule, prefix))
                    found.extend(_unit_dimension(table, row, rule, prefix, masses))
            found.extend(_value(table, row, rules))
            if table.kind == "interventions":
                found.extend(_dosing(table, row, terms, found))
            issues.extend(found)
    return issues


def _unit_dimension(
    table: LoadedTable,
    row: Row,
    rule: MeasurementRule,
    prefix: str,
    masses: dict[str, float | None],
) -> Issues:
    column = f"{prefix}unit"
    unit = row.cells[column]
    if not unit or not rule.units or NO_UNIT in rule.units or not valid_unit(unit):
        return
    if not converts(unit, rule.units, masses.get(row.cells[f"{prefix}substance"])):
        yield row_issue(
            table,
            row,
            "unit_dimension",
            f"{unit} cannot be converted to a unit of {rule.name}",
            column,
            actual=unit,
            hint=f"Units of {rule.name}; amounts of a substance convert with its molar mass.",
            candidates=list(rule.units),
        )


def _dosing(
    table: LoadedTable,
    row: Row,
    terms: dict[str, frozenset[str]],
    found: list[ValidationIssue],
) -> Issues:
    """The fields of doses and medications, as in study format 1."""
    measurement = row.cells["measurement"]
    if measurement not in DOSING:
        return
    for name in DOSING_FIELDS[measurement]:
        if row.cells[name]:
            continue
        if name == "unit" and any(issue.code == "missing_unit" for issue in found):
            continue
        yield row_issue(
            table,
            row,
            "missing_dosing_field",
            f"{name} is required for {measurement}",
            name,
        )
    application = row.cells["application"]
    if (
        measurement == "dosing"
        and application in terms["applications"]
        and application not in DOSING_APPLICATIONS
    ):
        yield row_issue(
            table,
            row,
            "invalid_application",
            f"Dosing supports application {', '.join(DOSING_APPLICATIONS)}, not {application}",
            "application",
            actual=application,
            candidates=DOSING_APPLICATIONS,
        )


def _value(table: LoadedTable, row: Row, rules: dict[str, MeasurementRule]) -> Issues:
    """A value where the measurement has one: numeric observations and doses."""
    if table.kind not in OBSERVATION_KINDS and table.kind != "interventions":
        return
    if any(row.cells[name] and row.values[name] is None for name in CENTRAL):
        return  # The value cell that cannot be read is already reported.
    measurement = row.cells["measurement"]
    if table.kind == "interventions":
        # As in study format 1, only doses need a value; other interventions,
        # such as qualitative dosing or fasting, are described by their terms.
        if measurement in DOSING and row.values["mean"] is None:
            yield row_issue(
                table,
                row,
                "missing_value",
                f"Enter the dose of {measurement} in mean",
                "mean",
            )
        return
    rule = rules.get(measurement)
    if (
        rule is not None
        and rule.dtype in VALUE_TYPES
        and not row.cells["choice"]
        and all(row.values[name] is None for name in CENTRAL)
    ):
        yield row_issue(
            table,
            row,
            "missing_value",
            f"{rule.name} needs a value: mean, gmean, median, min or max",
        )


def _term(
    table: LoadedTable,
    row: Row,
    column: Column,
    terms: dict[str, frozenset[str]],
    suggest: Callable[[str, str], tuple[str, ...]],
) -> Issues:
    value = row.cells[column.name]
    if not value or column.vocabulary is None:
        return
    if column.vocabulary == "calculation_types" and value == RETIRED_CALCULATION:
        yield row_issue(
            table,
            row,
            "retired_calculation",
            "Enter geometric statistics in gmean, gsd and gcv instead of calculation 'geometric mean'",
            column.name,
        )
    elif value not in terms[column.vocabulary]:
        yield row_issue(
            table,
            row,
            CODES[column.vocabulary],
            f"Unknown {column.name.removeprefix('x_').removeprefix('y_')}: {value}",
            column.name,
            actual=value,
            hint="Candidates are spelling suggestions, not equivalent terms.",
            candidates=suggest(value, column.vocabulary),
        )


def _measurement(
    table: LoadedTable, row: Row, rule: MeasurementRule, prefix: str
) -> Issues:
    if rule.deprecated:
        yield row_issue(
            table,
            row,
            "deprecated_measurement",
            f"{rule.name} is deprecated",
            f"{prefix}measurement",
        )
    if not prefix:
        choice = row.cells["choice"]
        if choice:
            if rule.dtype not in CHOICE_TYPES or choice not in rule.choices:
                yield row_issue(
                    table,
                    row,
                    "invalid_choice",
                    f"{choice!r} is not a choice of {rule.name}",
                    "choice",
                    candidates=list(rule.choices),
                )
        elif rule.dtype in REQUIRED_CHOICE_TYPES and rule.choices:
            yield row_issue(
                table,
                row,
                "missing_choice",
                f"{rule.name} needs a choice",
                "choice",
                candidates=list(rule.choices),
            )
    values = (f"{prefix}mean",) if prefix else VALUES
    if not rule.can_negative:
        for name in values:
            value = row.values.get(name)
            if isinstance(value, float) and value < 0:
                yield row_issue(
                    table,
                    row,
                    "negative_value",
                    f"{name} cannot be negative for {rule.name}",
                    name,
                    actual=value,
                )
    if (
        rule.time_required
        and table.kind in TIMED_KINDS
        and not row.cells[f"{prefix}time"]
    ):
        yield row_issue(
            table,
            row,
            "missing_time",
            f"{rule.name} needs a time; use NR when the publication does not report it",
            f"{prefix}time",
        )
    has_value = any(
        isinstance(row.values.get(name), float)
        for name in values
        if name != "error_bar"
    )
    if (
        has_value
        and rule.units
        and "NO_UNIT" not in rule.units
        and not row.cells[f"{prefix}unit"]
    ):
        yield row_issue(
            table,
            row,
            "missing_unit",
            f"{rule.name} needs a unit",
            f"{prefix}unit",
            candidates=list(rule.units),
        )
