"""Validate a study format 2 folder: layout, format, rows, relationships, vocabulary."""

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


def study_label(folder: Path) -> str:
    """The `<substance>/<name>` label of a study folder, independent of how the path was spelled."""
    folder = Path(folder).resolve()
    return f"{folder.parent.name}/{folder.name}"


def is_v2_folder(folder: Path) -> bool:
    """Whether study.json declares study format 2."""
    try:
        data = load_json((Path(folder) / STUDY_JSON).read_bytes())
    except OSError, JsonFileError:
        return False
    return isinstance(data, dict) and data.get("format") == FORMAT_VERSION


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
        elif (study.folder / name).read_bytes() != text.encode("utf-8"):
            issues.append(
                make_issue(
                    "not_formatted",
                    f"{name} is not in canonical form; run pkdb format",
                    file=name,
                )
            )
    return issues


def acknowledged(issue: ValidationIssue, study: LoadedStudy) -> bool:
    """Whether a review item acknowledges this warning; errors never are."""
    if issue.severity != "warning" or study.review is None:
        return False
    for item in study.review.items:
        if item.acknowledges != issue.code:
            continue
        target = item.target
        if target is None or target.file is None:
            return True
        source = issue.source
        if source is None or source.file != target.file:
            continue
        if target.column and source.header != target.column:
            continue
        if target.rows:
            table = study.table(target.file)
            lines = {
                row.line
                for row in (table.rows if table else [])
                if all(
                    row.cells.get(key) == value for key, value in target.rows.items()
                )
            }
            if source.row not in lines:
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
    kept = [issue for issue in issues if not acknowledged(issue, study)]
    return ValidationReport(issues=kept).finalize(max_issues)
