"""Validate and prepare a study format 2 folder.

Layers 1 to 5 check layout, format, rows, relationships and vocabulary terms.
Layer 6 reads the folder into the canonical study and runs the postprocessing
of the server (`prepare_study`): derived statistics, unit normalization,
datasets and pharmacokinetics.
"""

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from pkdb.domain.validation import prepare_study
from pkdb.domain.vocabulary import Vocabulary
from pkdb.schemas.prepared import PreparedStudy
from pkdb.schemas.validation import (
    StudyValidationError,
    ValidationIssue,
    ValidationReport,
    fail,
)
from pkdb.studyformat.formatter import planned_files
from pkdb.studyformat.issues import make_issue
from pkdb.studyformat.jsonio import JsonFileError, load_json
from pkdb.studyformat.load import LoadedStudy, load_study
from pkdb.studyformat.reader import read_study
from pkdb.studyformat.relations import check_relations
from pkdb.studyformat.rows import check_rows
from pkdb.studyformat.tables import REFERENCE_JSON, STUDY_JSON
from pkdb.studyformat.terms import check_terms

FORMAT_VERSION = 2
_DECLARES_FORMAT_2 = re.compile(rb'"format"\s*:\s*2\b')
# Files that only study format 2 folders have.
_FORMAT_2_FILES = ("subjects.tsv", "review.json")


def study_label(folder: Path) -> str:
    """The `<substance>/<name>` label of a study folder, independent of how the path was spelled."""
    folder = Path(folder).resolve()
    return f"{folder.parent.name}/{folder.name}"


def study_path(sid: str) -> str:
    """The URL path of a study: its sid with each segment percent-encoded.

    A study format 2 sid `<substance>/<name>` takes two path segments, a
    study format 1 sid one.
    """
    return "/".join(quote(part, safe="") for part in sid.split("/"))


def is_v2_folder(folder: Path) -> bool:
    """Whether a folder is in study format 2, decided leniently.

    A broken study.json (a merge conflict, a duplicate key) must not turn a
    format 2 folder into a format 1 folder, so its raw text and the files only
    format 2 has decide when it cannot be read as an object.
    """
    folder = Path(folder)
    try:
        raw = (folder / STUDY_JSON).read_bytes()
    except OSError:
        raw = None
    if raw is not None:
        try:
            data = load_json(raw)
        except JsonFileError:
            data = None
        if isinstance(data, dict):
            if data.get("format") == FORMAT_VERSION:
                return True
        elif _DECLARES_FORMAT_2.search(raw):
            return True
    return any(
        (folder / name).exists(follow_symlinks=False) for name in _FORMAT_2_FILES
    )


def format_issues(study: LoadedStudy) -> list[ValidationIssue]:
    """Files whose content differs from the canonical form `pkdb format` writes."""
    issues = []
    for name, text in planned_files(study).items():
        if text is None:
            issues.append(
                make_issue(
                    "not_formatted",
                    f"{name} has no rows; run pkdb format to remove it",
                    file=name,
                )
            )
        elif (data := (study.folder / name).read_bytes()) != text.encode("utf-8"):
            line = first_difference(data, text.encode("utf-8"))
            issues.append(
                make_issue(
                    "not_formatted",
                    f"{name} is not in canonical form (first difference in line {line}); run pkdb format",
                    file=name,
                    line=line,
                )
            )
    return issues


def first_difference(current: bytes, canonical: bytes) -> int:
    """Number of the first line that differs, counting line endings as part of a line."""
    lines = current.splitlines(keepends=True)
    expected = canonical.splitlines(keepends=True)
    for number, (line, wanted) in enumerate(zip(lines, expected, strict=False), 1):
        if line != wanted:
            return number
    return min(len(lines), len(expected)) + 1


@dataclass(frozen=True)
class Acknowledgement:
    """Where a review item acknowledges a warning; None reaches every file or line."""

    file: str | None = None
    column: str | None = None
    lines: frozenset[int] | None = None


def acknowledgements(study: LoadedStudy) -> dict[str, list[Acknowledgement]]:
    """The acknowledgements of the review items by issue code.

    The lines that a row filter selects are computed once per review item, not
    once per issue, so that many acknowledged warnings stay fast.
    """
    result: dict[str, list[Acknowledgement]] = defaultdict(list)
    for item in study.review.items if study.review else ():
        if item.acknowledges is None:
            continue
        target = item.target
        if target is None or target.file is None:
            result[item.acknowledges].append(Acknowledgement())
            continue
        lines = None
        if target.rows:
            table = study.table(target.file)
            lines = table.matching_lines(target.rows) if table else frozenset()
        result[item.acknowledges].append(
            Acknowledgement(target.file, target.column, lines)
        )
    return result


def acknowledged(
    issue: ValidationIssue, acknowledgements: dict[str, list[Acknowledgement]]
) -> bool:
    """Whether a review item acknowledges this warning; errors never are."""
    if issue.severity != "warning":
        return False
    source = issue.source
    for target in acknowledgements.get(issue.code, ()):
        if target.file is None:
            return True
        if source is None or source.file != target.file:
            continue
        if target.column and source.header != target.column:
            continue
        if target.lines is not None and source.row not in target.lines:
            continue
        return True
    return False


def _severities(issues: list[ValidationIssue]) -> tuple[int, int]:
    errors = sum(issue.severity == "error" for issue in issues)
    return errors, len(issues) - errors


def _check(
    study: LoadedStudy, vocabulary: Vocabulary, max_issues: int
) -> tuple[PreparedStudy | None, ValidationReport]:
    """Run every layer; layer 6 runs only when layers 1 to 5 found no error.

    Returns the prepared study, None when any layer found an error, and the
    report of all issues except acknowledged warnings.
    """
    issues = [
        *study.issues,
        *format_issues(study),
        *check_rows(study),
        *check_relations(study),
        *check_terms(study, vocabulary),
    ]
    prepared = None
    postprocessing = ValidationReport()
    if not any(issue.severity == "error" for issue in issues):
        try:
            prepared = prepare_study(
                read_study(study), vocabulary, max_issues=max_issues
            )
            postprocessing = prepared.report
        except StudyValidationError as error:
            postprocessing = error.report
        issues.extend(postprocessing.issues)
    known = acknowledgements(study)
    kept = [issue for issue in issues if not acknowledged(issue, known)]
    # Issues that postprocessing counted but did not return stay counted.
    returned_errors, returned_warnings = _severities(postprocessing.issues)
    errors, warnings = _severities(kept)
    report = ValidationReport(
        issues=kept,
        error_count=errors + postprocessing.error_count - returned_errors,
        warning_count=warnings + postprocessing.warning_count - returned_warnings,
        complete=postprocessing.complete,
        stopped_reason=postprocessing.stopped_reason,
    ).finalize(max_issues)
    return (prepared if report.valid else None), report


def validate_folder(
    folder: Path, vocabulary: Vocabulary, *, max_issues: int = 1000
) -> ValidationReport:
    """Run every validation layer and collect all issues except acknowledged warnings."""
    return _check(load_study(Path(folder)), vocabulary, max_issues)[1]


def check_limits(
    study: LoadedStudy, *, max_rows: int | None = None, max_files: int | None = None
) -> None:
    """Fail with `file_limit` or `row_limit` when a study exceeds upload limits.

    `max_rows` limits the table rows and `max_files` the files besides
    study.json and reference.json.
    """
    files = study.layout.files - {STUDY_JSON, REFERENCE_JSON}
    if max_files is not None and len(files) > max_files:
        fail("file_limit", f"The study has more than {max_files} files")
    if max_rows is not None and sum(len(t.rows) for t in study.tables) > max_rows:
        fail("row_limit", f"The study tables have more than {max_rows} rows")


def prepare_folder(
    folder: Path,
    vocabulary: Vocabulary,
    *,
    max_issues: int = 1000,
    max_rows: int | None = None,
    max_files: int | None = None,
) -> PreparedStudy:
    """Validate a folder and prepare its canonical study as the server does.

    The prepared report holds the warnings of every layer except acknowledged
    ones. Any error raises StudyValidationError with the report of all layers.
    `max_rows` limits the table rows and `max_files` the files besides
    study.json and reference.json.
    """
    study = load_study(Path(folder))
    check_limits(study, max_rows=max_rows, max_files=max_files)
    prepared, report = _check(study, vocabulary, max_issues)
    if prepared is None:
        raise StudyValidationError(report)
    return prepared.model_copy(update={"report": report})
