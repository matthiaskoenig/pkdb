"""Layer 5: vocabulary terms, choices, signs, required times and units."""

from collections.abc import Iterator
from difflib import get_close_matches

from pkdb.domain.vocabulary import MeasurementRule, Vocabulary
from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.columns import Column
from pkdb.studyformat.issues import row_issue
from pkdb.studyformat.load import LoadedStudy, LoadedTable, Row

RETIRED_CALCULATION = "geometric mean"
UNSPECIFIED = "unspecified summary"
DOSING = frozenset({"dosing", "medication"})
CHOICE_TYPES = frozenset({"categorical", "boolean", "numeric_categorical"})
REQUIRED_CHOICE_TYPES = frozenset({"categorical", "boolean"})
TIMED_KINDS = frozenset({"characteristica", "outputs", "timecourses", "scatters"})
VALUES = ("mean", "gmean", "median", "min", "max", "error_bar")
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


def check_terms(study: LoadedStudy, vocabulary: Vocabulary) -> list[ValidationIssue]:
    terms = vocabulary_terms(vocabulary)
    rules = vocabulary.measurement_map()
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
            for column in columns:
                issues.extend(_term(table, row, column, terms))
            for prefix in prefixes:
                rule = rules.get(row.cells[f"{prefix}measurement"])
                if rule is not None:
                    issues.extend(_measurement(table, row, rule, prefix))
            if table.kind == "interventions" and row.cells["measurement"] in DOSING:
                for name in ("substance", "route"):
                    if not row.cells[name]:
                        issues.append(
                            row_issue(
                                table,
                                row,
                                "missing_dosing_field",
                                f"{name} is required for dosing",
                                name,
                            )
                        )
    return issues


def _term(
    table: LoadedTable, row: Row, column: Column, terms: dict[str, frozenset[str]]
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
            candidates=get_close_matches(
                value, sorted(terms[column.vocabulary]), n=10, cutoff=0.6
            ),
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
