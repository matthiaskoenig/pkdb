"""Validate a study format 2 folder: layout, format, rows, relationships, vocabulary."""

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from pkdb.domain.vocabulary import Vocabulary
from pkdb.schemas.validation import ValidationIssue, ValidationReport
from pkdb.studyformat.formatter import planned_files
from pkdb.studyformat.issues import make_issue
from pkdb.studyformat.jsonio import JsonFileError, load_json
from pkdb.studyformat.load import LoadedStudy, load_study
from pkdb.studyformat.relations import check_relations
from pkdb.studyformat.rows import check_rows
from pkdb.studyformat.tables import STUDY_JSON
from pkdb.studyformat.terms import check_terms

FORMAT_VERSION = 2
_DECLARES_FORMAT_2 = re.compile(rb'"format"\s*:\s*2\b')
# Files that only study format 2 folders have.
_FORMAT_2_FILES = ("subjects.tsv", "review.json")


def study_label(folder: Path) -> str:
    """The `<substance>/<name>` label of a study folder, independent of how the path was spelled."""
    folder = Path(folder).resolve()
    return f"{folder.parent.name}/{folder.name}"


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


def validate_folder(
    folder: Path, vocabulary: Vocabulary, *, max_issues: int = 1000
) -> ValidationReport:
    """Run every validation layer and collect all issues except acknowledged warnings."""
    study = load_study(Path(folder))
    issues = [
        *study.issues,
        *format_issues(study),
        *check_rows(study),
        *check_relations(study),
        *check_terms(study, vocabulary),
    ]
    known = acknowledgements(study)
    kept = [issue for issue in issues if not acknowledged(issue, known)]
    return ValidationReport(issues=kept).finalize(max_issues)
