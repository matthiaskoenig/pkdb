"""Check the format 2 studies of a pkdb_data checkout, without writing or contacting the network.

`pkdb check` runs these checks in the pre-commit hook (`--staged`) and the CI
(`--changed BASE`) of pkdb_data: the canonical form of `pkdb format --check`,
offline validation, workbooks that git must not track, and the identifiers and
issue numbers of `pkdb registry --check`. Format 1 studies are skipped.
"""

import re
import subprocess
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from pkdb.cache import VocabularyCache, select_vocabulary
from pkdb.domain.vocabulary import Vocabulary
from pkdb.lifecycle.registry import duplicates, registry_problems, scan
from pkdb.preparation import study_folders
from pkdb.repository import STUDIES, location
from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.tables import STUDY_JSON
from pkdb.studyformat.text import natural_key
from pkdb.studyformat.validation import is_v2_folder, validate_folder
from pkdb.studyformat.workbook.base import state_path, workbook_path

VOCABULARY_LOCK = "vocabulary.lock.json"
# The changes that touch a study: added, copied, deleted, modified, renamed and
# type changed files. Without rename detection a move is a deletion and an addition.
CHANGES = ("--no-renames", "--diff-filter=ACDMRT")
# Validation reports the files that formatting would change as well.
NOT_FORMATTED = "not_formatted"


class CheckError(ValueError):
    """A usage problem: not a git repository, an unknown base, a path outside the checkout."""


class Problem(BaseModel):
    """A problem of the study at a location, or of the repository when `study` is None."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    study: str | None
    code: str
    message: str
    file: str | None = None
    row: int | None = None
    severity: Literal["error", "warning"] = "error"


class CheckReport(BaseModel):
    """The checked format 2 studies, the skipped format 1 studies, the deleted studies and the problems."""

    model_config = ConfigDict(extra="forbid")
    checked: list[str] = Field(default_factory=list)
    format_1: int = 0
    deleted: list[str] = Field(default_factory=list)
    problems: list[Problem] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Whether no problem is an error; warnings do not fail the check."""
        return not any(problem.severity == "error" for problem in self.problems)


def _git(root: Path, *args: str) -> bytes:
    """The output of git run in `root`, or a CheckError with git's error line."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "--literal-pathspecs", *args],
            capture_output=True,
            check=False,
        )
    except OSError as error:
        raise CheckError(f"Cannot run git: {error.strerror or error}") from None
    if completed.returncode:
        lines = completed.stderr.decode("utf-8", "replace").strip().splitlines()
        line = next(
            (line for line in lines if line.startswith(("fatal:", "error:"))),
            lines[0] if lines else f"exit code {completed.returncode}",
        )
        reason = re.sub(r"^(fatal|error): ", "", line)
        raise CheckError(f"git {args[0]} failed: {reason}")
    return completed.stdout


def _names(output: bytes) -> list[str]:
    """The NUL separated paths of git output; bytes that are not UTF-8 survive as surrogates."""
    return [
        name.decode("utf-8", "surrogateescape") for name in output.split(b"\0") if name
    ]


def _study_of(root: Path, name: str) -> Path | None:
    """The folder `studies/<substance>/<name>` of a path relative to the root, or None.

    Paths outside study folders and below hidden folders give None.
    """
    parts = PurePosixPath(name).parts
    if (
        len(parts) < 4
        or parts[0] != STUDIES
        or any(part.startswith(".") for part in parts[1:3])
    ):
        return None
    return root.joinpath(*parts[:3])


def _is_study(folder: Path) -> bool:
    """Whether a folder still holds a study, not only files that git leaves behind."""
    return (folder / STUDY_JSON).is_file() or is_v2_folder(folder)


def _in_order(folders) -> list[Path]:
    """Folders once each, in the natural order of their locations."""
    return sorted(
        set(folders), key=lambda folder: (natural_key(location(folder)), str(folder))
    )


def _visible(studies: Path, folders: list[Path]) -> list[Path]:
    """The folders that are not hidden and not below a hidden folder of the studies folder."""
    return [
        folder
        for folder in folders
        if not any(part.startswith(".") for part in folder.relative_to(studies).parts)
    ]


def _below(root: Path, path: Path) -> list[Path]:
    """The study folders of a path inside the studies folder, without hidden folders."""
    studies = root / STUDIES
    path = Path(path).resolve()
    if not path.is_relative_to(studies):
        raise CheckError(f"{path} is outside {studies}")
    try:
        return _visible(studies, study_folders(path))
    except ValueError as error:
        raise CheckError(f"{path}: {error}") from None


def _changed(root: Path, *, staged: bool, changed: str | None) -> list[Path]:
    """The study folders of the staged files or of the files changed since a base."""
    args = ["diff", "--name-only", "-z", "--relative", *CHANGES]
    if staged:
        args.append("--cached")
    else:
        # A base is never read as an option, such as --output that writes a file.
        args += ["--end-of-options", f"{changed}...HEAD", "--"]
    found = (_study_of(root, name) for name in _names(_git(root, *args)))
    return [folder for folder in found if folder is not None]


def select(
    root: Path,
    *,
    paths: Sequence[Path] = (),
    staged: bool = False,
    changed: str | None = None,
) -> tuple[list[Path], list[str]]:
    """The existing study folders to check and the locations of deleted studies.

    The studies below `paths`, the studies of the staged files, the studies of
    the files changed since the base `changed`, or every study of the checkout.
    A study whose folder is gone is deleted. Hidden folders are never selected.
    """
    root = Path(root).resolve()
    if sum((bool(paths), staged, changed is not None)) > 1:
        raise CheckError("Choose study paths, the staged files or a base, not several")
    if paths:
        return _in_order(folder for path in paths for folder in _below(root, path)), []
    if staged or changed is not None:
        folders = set(_changed(root, staged=staged, changed=changed))
        deleted = [location(folder) for folder in folders if not _is_study(folder)]
        existing = [folder for folder in folders if _is_study(folder)]
        return _in_order(existing), sorted(deleted, key=natural_key)
    studies = root / STUDIES
    if not studies.is_dir():
        raise CheckError(f"{root} has no {STUDIES} folder")
    try:
        folders = study_folders(studies)
    except ValueError:  # no study.json below the studies folder
        return [], []
    return _in_order(_visible(studies, folders)), []


def vocabulary_for(root: Path, path: Path | None) -> Vocabulary:
    """The vocabulary of `path`, else the lock file of the checkout, else the one bundled with pkdb.

    It never contacts a server.
    """
    lock = Path(root) / VOCABULARY_LOCK
    chosen = path or (lock if lock.exists() else None)
    try:
        return select_vocabulary(chosen, None, VocabularyCache())
    except (OSError, ValueError) as error:
        raise CheckError(
            f"Cannot read the vocabulary {chosen or 'bundled with pkdb'}: {error}"
        ) from None


def _issue_problem(study: str, issue: ValidationIssue) -> Problem:
    """A validation issue as a problem of the study, at its file and row."""
    source = issue.source
    return Problem(
        study=study,
        code=issue.code,
        message=issue.message,
        file=source.file if source else None,
        row=source.row if source else None,
        severity=issue.severity,
    )


def _form_problems(folder: Path, study: str) -> list[Problem]:
    """The files that pkdb format would change, and the errors that keep it from reading them."""
    result = format_folder(folder, check=True)
    problems = [
        Problem(
            study=study,
            code="not_canonical",
            message=f"{change.file} is not in canonical form; run pkdb format",
            file=change.file,
        )
        for change in result.changes
    ]
    problems += [
        _issue_problem(study, issue)
        for issue in result.issues
        if issue.severity == "error"
    ]
    return problems


def _validation_problems(
    folder: Path, study: str, vocabulary: Vocabulary
) -> list[Problem]:
    """The errors and warnings of offline validation, without acknowledged warnings.

    The canonical form is left to the form check. A report that leaves out
    errors or stopped early adds an error, so the check never passes it.
    """
    report = validate_folder(folder, vocabulary)
    problems = [
        _issue_problem(study, issue)
        for issue in report.issues
        if issue.code != NOT_FORMATTED
    ]
    listed = sum(issue.severity == "error" for issue in report.issues)
    if report.error_count > listed or not report.complete:
        message = (
            report.stopped_reason
            or f"{report.error_count - listed} more errors are not listed; run pkdb validate to see them"
        )
        problems.append(
            Problem(study=study, code="validation_incomplete", message=message)
        )
    return problems


def _workbook_problems(root: Path, folder: Path, study: str) -> list[Problem]:
    """An error when git tracks or stages the workbook of the study or its state file."""
    workbook = workbook_path(folder)
    files = (workbook, state_path(workbook))
    output = _git(root, "ls-files", "--cached", "-z", "--", *map(str, files))
    listed = {PurePosixPath(name).name for name in _names(output)}
    tracked = [file.name for file in files if file.name in listed]
    if not tracked:
        return []
    one = len(tracked) == 1
    message = (
        f"{' and '.join(tracked)} {'is' if one else 'are'} generated; "
        f"remove {'it' if one else 'them'} from git with git rm --cached"
    )
    return [
        Problem(study=study, code="workbook_tracked", message=message, file=tracked[0])
    ]


def _unreadable(folder: Path, study: str, error: OSError) -> Problem:
    """A file of the study that cannot be read."""
    file = None
    if error.filename and (path := Path(str(error.filename))).is_relative_to(folder):
        file = path.relative_to(folder).as_posix()
    name = file or error.filename or "the study"
    return Problem(
        study=study,
        code="unreadable_file",
        message=f"Cannot read {name}: {error.strerror or error}",
        file=file,
    )


def _repository_problems(root: Path) -> list[Problem]:
    """Shared identifiers and issue numbers, unreadable study.json files and registry file conflicts."""
    result = scan(root)
    found = [
        *(("duplicate_identifier", message) for message in duplicates(result)),
        *(("unreadable_study", message) for message in result.errors),
        *(("registry_file", message) for message in registry_problems(result, root)),
    ]
    return [Problem(study=None, code=code, message=message) for code, message in found]


def check(
    root: Path,
    folders: Sequence[Path],
    vocabulary: Vocabulary,
    *,
    deleted: Sequence[str] = (),
) -> CheckReport:
    """Check the format 2 studies of `folders` and the repository; count format 1 studies.

    It never writes a file and never contacts the network.
    """
    root = Path(root).resolve()
    if not (root / STUDIES).is_dir():
        raise CheckError(f"{root} has no {STUDIES} folder")
    report = CheckReport(deleted=list(deleted))
    for folder in folders:
        folder = Path(folder).resolve()
        if not is_v2_folder(folder):
            report.format_1 += 1
            continue
        study = location(folder)
        report.checked.append(study)
        # git runs first, so that a git failure stops the check before the slow part.
        workbook = _workbook_problems(root, folder, study)
        try:
            found = [
                *_form_problems(folder, study),
                *_validation_problems(folder, study, vocabulary),
            ]
        except OSError as error:
            found = [_unreadable(folder, study, error)]
        # Formatting and validation report the same structural errors.
        report.problems += list(dict.fromkeys([*found, *workbook]))
    report.problems += _repository_problems(root)
    return report
