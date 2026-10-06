"""Validation issues of study format 2, located by file, sheet, row and column."""

from collections import Counter
from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING, Literal

from pkdb.schemas.source import SourceLocation
from pkdb.schemas.validation import Suggestion, ValidationIssue

if TYPE_CHECKING:
    from pkdb.studyformat.load import LoadedTable, Row

WARNINGS = frozenset(
    {
        "outside_range",
        "duplicate_observation",
        "unused_intervention",
        "unused_subject",
        "review_target_unmatched",
        "deprecated_measurement",
        "workbook_base_missing",
        "workbook_base_invalid",
        "formula_value",
        "workbook_open",
    }
)
_GROUPS = {
    "layout": (
        "reserved_name",
        "unknown_directory",
        "symlink",
        "unknown_file",
        "legacy_file",
        "missing_file",
        "missing_image",
        "table_name_too_long",
        "duplicate_table_name",
    ),
    "format": (
        "invalid_encoding",
        "merge_conflict",
        "missing_header",
        "unknown_column",
        "duplicate_column",
        "extra_cells",
        "too_many_columns",
        "stray_text",
        "invalid_json",
        "duplicate_key",
        "not_formatted",
    ),
    "schema": (
        "invalid_study_json",
        "invalid_review_json",
        "invalid_reference_json",
        "invalid_number",
        "invalid_integer",
        "invalid_time",
        "invalid_name",
        "invalid_enum",
        "invalid_source",
        "missing_required",
        "invalid_count",
    ),
    "scientific": (
        "missing_value",
        "choice_statistics",
        "individual_statistics",
        "unspecified_summary_statistics",
        "incomplete_error_bar",
        "error_bar_conflict",
        "reversed_range",
        "outside_range",
        "invalid_statistic",
        "missing_time_unit",
        "invalid_time_unit",
        "time_dimension",
        "invalid_unit",
        "schedule_conflict",
        "invalid_schedule",
    ),
    "reference": (
        "unknown_reference",
        "duplicate_reference",
        "duplicate_name",
        "duplicate_label",
        "missing_root",
        "root_parent",
        "missing_parent",
        "parent_not_group",
        "subject_cycle",
        "subject_count_exceeds_parent",
        "inconsistent_series",
        "duplicate_time",
        "mixed_scatter_subjects",
        "duplicate_row",
        "duplicate_observation",
        "unused_intervention",
        "unused_subject",
        "reference_mismatch",
        "public_requires_release",
    ),
    "workbook": (
        "workbook_unreadable",
        "workbook_newer",
        "workbook_base_invalid",
        "workbook_base_missing",
        "cell_too_long",
        "illegal_character",
        "unknown_sheet",
        "missing_sheet",
        "value_outside_table",
        "cell_line_break",
        "cell_date",
        "cell_percent",
        "cell_error",
        "formula_without_value",
        "formula_value",
        "workbook_open",
        "sync_conflict",
        "sync_write_failed",
    ),
    "review": (
        "approved_with_open_items",
        "unknown_review_target",
        "review_target_unmatched",
    ),
    "vocabulary": (
        "unknown_measurement",
        "unknown_substance",
        "unknown_tissue",
        "unknown_method",
        "unknown_route",
        "unknown_form",
        "unknown_application",
        "unknown_calculation",
        "retired_calculation",
        "invalid_choice",
        "missing_choice",
        "negative_value",
        "deprecated_measurement",
        "missing_time",
        "missing_unit",
        "missing_dosing_field",
        "invalid_application",
        "unit_dimension",
    ),
}
CATEGORIES = {code: category for category, codes in _GROUPS.items() for code in codes}
_PARSE = frozenset({"layout", "format", "schema", "workbook"})


# A single line, cell or JSON file reports at most this many issues of one
# code; one more issue states how many there are in all.
REPEATED_ISSUES = 10
# The end of the message of such a summary issue.
LISTED = f"the first {REPEATED_ISSUES} are listed"


class IssueCap:
    """Admits the first REPEATED_ISSUES issues of each code and counts all."""

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()

    def admit(self, code: str) -> bool:
        self.counts[code] += 1
        return self.counts[code] <= REPEATED_ISSUES

    def beyond(self) -> Iterator[tuple[str, int]]:
        """The codes with more issues than were admitted, and their totals."""
        for code, total in self.counts.items():
            if total > REPEATED_ISSUES:
                yield code, total


def column_letter(index: int) -> str:
    """Spreadsheet letter of a 0-based column index: 0 is A, 26 is AA."""
    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def make_issue(
    code: str,
    message: str,
    *,
    file: str | None = None,
    line: int | None = None,
    column: int | None = None,
    header: str | None = None,
    severity: Literal["error", "warning"] | None = None,
    hint: str | None = None,
    candidates: Iterable[str] = (),
    **details,
) -> ValidationIssue:
    """Create a validation issue at an optional file, line and column.

    A hint or candidates add a suggestion. The severity defaults to warning for
    warning codes and to error otherwise.
    """
    source = None
    if file is not None:
        letter = column_letter(column) if column is not None else None
        source = SourceLocation(
            file=file,
            sheet=file.removesuffix(".tsv") if file.endswith(".tsv") else None,
            row=line,
            column=letter,
            cell=f"{letter}{line}" if letter and line else None,
            header=header,
        )
    candidates = list(candidates)
    suggestions = (
        [
            Suggestion(
                kind="fix",
                message=hint or "Did you mean one of these?",
                candidates=candidates,
            )
        ]
        if hint or candidates
        else []
    )
    category = CATEGORIES.get(code)
    return ValidationIssue(
        code=code,
        severity=severity or ("warning" if code in WARNINGS else "error"),
        message=message,
        source=source,
        category=category,
        stage="parse" if category in _PARSE else "validate",
        suggestions=suggestions,
        **details,
    )


def row_issue(
    table: LoadedTable,
    row: Row,
    code: str,
    message: str,
    column: str | None = None,
    **details,
) -> ValidationIssue:
    """Issue at a row of a loaded table, optionally at one of its columns."""
    return make_issue(
        code,
        message,
        file=table.file,
        line=row.line,
        column=table.column_index(column) if column else None,
        header=column,
        **details,
    )
