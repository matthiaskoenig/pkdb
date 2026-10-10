"""Check the format 2 studies of a pkdb_data checkout, without writing or contacting the network.

`pkdb check` runs these checks in the pre-commit hook (`--staged`) and the CI
(`--changed BASE`) of pkdb_data: offline validation, which includes the
canonical form of `pkdb format --check`, workbooks that git must not track, and
the identifiers and issue numbers of `pkdb registry --check`. Format 1 studies
are skipped.
"""

import logging
import os
import re
import subprocess
from collections.abc import Iterable, Sequence
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from pkdb.cache import VocabularyCache, lock_file, select_vocabulary
from pkdb.domain.vocabulary import Vocabulary
from pkdb.lifecycle.registry import duplicates, registry_problems, scan
from pkdb.preparation import study_folders
from pkdb.repository import STUDIES, location
from pkdb.repository import study_folders as checkout_folders
from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.tables import STUDY_JSON
from pkdb.studyformat.text import natural_key
from pkdb.studyformat.validation import is_v2_folder, validate_folder
from pkdb.studyformat.workbook.base import state_path, workbook_path

# The changes that touch a study: added, copied, deleted, modified, renamed and
# type changed files. Without rename detection a move is a deletion and an addition.
CHANGES = ("--no-renames", "--diff-filter=ACDMRT")
# The validation issue of a file that pkdb format would change.
NOT_FORMATTED = "not_formatted"
# Paths per git call, so that the command line stays short on every system.
BATCH = 200


class CheckError(ValueError):
    """A usage problem: not a git repository, an unknown base, a path outside the checkout."""


class Problem(BaseModel):
    """A problem of the study at a location, or of the repository when `study` is None."""

    model_config = ConfigDict(extra="forbid")
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


def _git(root: Path, *args: str, silent: str | None = None) -> bytes:
    """The output of git run in `root`, or a CheckError with git's error line.

    `silent` is the message when git fails without printing an error.
    """
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
        if not lines and silent:
            raise CheckError(silent)
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


def _git_paths(root: Path, args: Sequence[str], paths: Sequence[str]) -> list[str]:
    """The paths that git prints for `args -- paths`, in calls of at most BATCH paths.

    No path means no call: git without paths would list the whole repository.
    """
    return [
        name
        for start in range(0, len(paths), BATCH)
        for name in _names(_git(root, *args, "--", *paths[start : start + BATCH]))
    ]


def _relative(root: Path, path: Path) -> str:
    """The path relative to the root, as git prints it."""
    if not path.is_relative_to(root):
        raise CheckError(f"{path} is outside the checkout {root}")
    return path.relative_to(root).as_posix()


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


def _holds_study(folder: Path) -> bool:
    """Whether a folder holds a study of either format."""
    return (folder / STUDY_JSON).is_file() or is_v2_folder(folder)


def _in_order(folders: Iterable[Path]) -> list[Path]:
    """Folders once each, in the natural order of their locations."""
    return sorted(
        set(folders), key=lambda folder: (natural_key(location(folder)), str(folder))
    )


def _below(root: Path, path: Path) -> list[Path]:
    """The study folders `studies/<substance>/<name>` of a path inside the studies folder.

    Hidden folders are skipped; a study.json at another depth is a CheckError.
    """
    studies = root / STUDIES
    if not Path(path).exists():
        raise CheckError(f"{Path(path).as_posix()} does not exist")
    path = Path(path).resolve()
    if not path.is_relative_to(studies):
        raise CheckError(f"{path} is outside {studies}")
    try:
        found = study_folders(path)
    except ValueError as error:
        raise CheckError(f"{path}: {error}") from None
    except OSError as error:
        raise _listing_error(path, error) from None
    folders = []
    for folder in found:
        parts = folder.relative_to(studies).parts
        if any(part.startswith(".") for part in parts):
            continue
        if len(parts) != 2:
            raise CheckError(
                f"{folder.relative_to(root).as_posix()} is not a study folder "
                f"{STUDIES}/<substance>/<name>"
            )
        folders.append(folder)
    return folders


def _listing_error(folder: Path, error: OSError) -> CheckError:
    """The usage error for a folder of studies that cannot be listed."""
    where = Path(str(error.filename)) if error.filename else folder
    return CheckError(f"Cannot list {where.as_posix()}: {error.strerror or error}")


def _verify_base(root: Path, base: str) -> None:
    """A CheckError unless the base names a commit of the repository."""
    if not base.strip():
        raise CheckError("The base is empty; give a branch, tag or commit")
    _git(
        root,
        *("rev-parse", "--verify", "--quiet", "--end-of-options", f"{base}^{{commit}}"),
        silent=f"The base {base} is not a commit of the repository",
    )


def _changed(root: Path, base: str | None) -> tuple[list[Path], list[str]]:
    """The study folders of the staged files (no base) or of the files changed since a base, and the deleted studies.

    A study is deleted when its folder is gone or git tracks no file below it
    any more (the index for staged files, HEAD for a base), so that files that
    git rm leaves behind do not count, but a study that lost a file does.
    """
    args = ["diff", "--name-only", "-z", "--relative", *CHANGES]
    if base is None:
        args.append("--cached")
        listing = ["ls-files", "--cached", "-z"]
    else:
        _verify_base(root, base)
        # A base is never read as an option, such as --output that writes a file.
        args += ["--end-of-options", f"{base}...HEAD", "--"]
        listing = ["ls-tree", "-r", "--name-only", "-z", "HEAD"]
    found = {_study_of(root, name) for name in _names(_git(root, *args))}
    folders = _in_order(folder for folder in found if folder is not None)
    paths = [_relative(root, folder) for folder in folders]
    tracked = {_study_of(root, name) for name in _git_paths(root, listing, paths)}
    existing = [f for f in folders if f in tracked and f.is_dir()]
    deleted = [location(f) for f in folders if f not in existing]
    return existing, deleted


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
    A study folder is `studies/<substance>/<name>`; hidden folders are never
    selected.
    """
    root = Path(root).resolve()
    if sum((bool(paths), staged, changed is not None)) > 1:
        raise CheckError("Choose study paths, the staged files or a base, not several")
    if paths:
        return _in_order(folder for path in paths for folder in _below(root, path)), []
    if staged or changed is not None:
        return _changed(root, None if staged else changed)
    if not (root / STUDIES).is_dir():
        raise CheckError(f"{root} has no {STUDIES} folder")
    try:
        return [f for f in checkout_folders(root) if _holds_study(f)], []
    except OSError as error:
        raise _listing_error(root / STUDIES, error) from None


def vocabulary_for(root: Path, path: Path | None) -> Vocabulary:
    """The vocabulary of `path`, else the lock file of the checkout, else the one bundled with pkdb.

    This is `select_vocabulary` without an endpoint cache, on purpose: CI has no
    cache, and the hook must give the answer of CI, so the answer depends only
    on the checkout. It never contacts a server.
    """
    chosen = path or lock_file(root)
    try:
        return select_vocabulary(chosen, None, VocabularyCache())
    except (OSError, ValueError) as error:
        raise CheckError(
            f"Cannot read the vocabulary {chosen or 'bundled with pkdb'}: {error}"
        ) from None


def _issue_problem(study: str, issue: ValidationIssue) -> Problem:
    """A validation issue as a problem of the study, at its file and row.

    A file that pkdb format would change is `not_canonical`.
    """
    source = issue.source
    return Problem(
        study=study,
        code="not_canonical" if issue.code == NOT_FORMATTED else issue.code,
        message=issue.message,
        file=source.file if source else None,
        row=source.row if source else None,
        severity=issue.severity,
    )


def _validation_problems(
    folder: Path, study: str, vocabulary: Vocabulary
) -> list[Problem]:
    """The errors and warnings of offline validation, without acknowledged warnings.

    They include the files that pkdb format would change and the structural
    errors that keep it from reading a file. A report that leaves out errors or
    stopped early adds an error, so the check never passes it.
    """
    report = validate_folder(folder, vocabulary)
    problems = [_issue_problem(study, issue) for issue in report.issues]
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


def _workbook_problems(root: Path, folders: Sequence[Path]) -> dict[Path, Problem]:
    """An error for each study whose workbook or its state file git tracks or stages."""
    files = {
        folder: (workbook, state_path(workbook))
        for folder in folders
        for workbook in [workbook_path(folder)]
    }
    paths = [_relative(root, file) for pair in files.values() for file in pair]
    listed = set(_git_paths(root, ["ls-files", "--cached", "-z"], paths))
    problems = {}
    for folder, pair in files.items():
        tracked = [file.name for file in pair if _relative(root, file) in listed]
        if tracked:
            one = len(tracked) == 1
            message = (
                f"{' and '.join(tracked)} {'is' if one else 'are'} generated; "
                f"remove {'it' if one else 'them'} from git with git rm --cached"
            )
            problems[folder] = Problem(
                study=location(folder),
                code="workbook_tracked",
                message=message,
                file=tracked[0],
            )
    return problems


def _untracked(root: Path, folders: Sequence[Path]) -> set[str]:
    """The files below the folders that git does not track, relative to the root.

    Ignored files count as well: a commit leaves them out like any untracked file.
    """
    paths = [_relative(root, folder) for folder in folders]
    return set(_git_paths(root, ["ls-files", "--others", "-z"], paths))


def _tracked_only(
    root: Path, folder: Path, problems: list[Problem], untracked: set[str]
) -> list[Problem]:
    """The problems of a study without those of files that git does not track.

    Errors of such files stop validation before its last step, so a warning
    names them when any is left out.
    """
    prefix = _relative(root, folder)
    kept: list[Problem] = []
    names: set[str] = set()
    for problem in problems:
        if problem.file is None or f"{prefix}/{problem.file}" not in untracked:
            if problem.file is not None and _printable(problem.file) != problem.file:
                problem = problem.model_copy(update={"file": _printable(problem.file)})
            kept.append(problem)
        elif problem.severity == "error":
            names.add(problem.file)
    if names:
        kept.append(
            Problem(
                study=location(folder),
                code="untracked_errors",
                message=(
                    f"Errors in files that git does not track can hide other errors "
                    f"of the study: {', '.join(sorted(map(_printable, names), key=natural_key))}; add the files with git add or remove them"
                ),
                severity="warning",
            )
        )
    return kept


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


def _unencodable_file(folder: Path) -> str | None:
    """The first file below the folder whose name is not valid UTF-8, relative to it, else None."""
    for directory, folders, files in os.walk(folder):
        folders.sort()
        for name in sorted(files):
            try:
                name.encode("utf-8")
            except UnicodeEncodeError:
                return (Path(directory) / name).relative_to(folder).as_posix()
    return None


def _failed(folder: Path, study: str, error: Exception) -> Problem:
    """An unexpected error of the check of a study, at the file that caused it where that is known."""
    file = _unencodable_file(folder) if isinstance(error, UnicodeEncodeError) else None
    message = f"Cannot check the study: {type(error).__name__}: {error}"
    if file is not None:
        message += f" (the name of {_printable(file)} is not valid UTF-8)"
    return Problem(study=study, code="unreadable_study", message=message, file=file)


def _printable(name: str) -> str:
    """A file name with the bytes that are not valid UTF-8 written as escapes."""
    return name.encode("utf-8", "backslashreplace").decode("utf-8")


def _tracked_studies(root: Path) -> set[Path] | None:
    """The study folders whose study.json git tracks or has staged.

    None outside a git checkout, and when the checkout is not the top of its git
    work tree (a copy inside another repository), where every study counts.
    """
    try:
        top = _git(root, "rev-parse", "--show-toplevel")
    except CheckError:
        return None
    # A copy inside an unrelated work tree is not tracked by that repository.
    try:
        same = os.path.samefile(top.decode("utf-8", "surrogateescape").strip(), root)
    except OSError:
        same = False
    if not same:
        return None
    paths = [_relative(root, folder / STUDY_JSON) for folder in checkout_folders(root)]
    listed = _git_paths(root, ["ls-files", "--cached", "-z"], paths)
    return {folder for name in listed if (folder := _study_of(root, name)) is not None}


def _repository_problems(root: Path) -> list[Problem]:
    """Shared identifiers and issue numbers, unreadable study.json files and registry file conflicts.

    Inside a git checkout only the studies whose study.json git tracks or stages count: a commit
    and CI leave an untracked copy of a study out.
    """
    result = scan(root, _tracked_studies(root))
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
    staged: bool = False,
) -> CheckReport:
    """Check the format 2 studies of `folders` and the repository; count format 1 studies.

    With `staged`, the problems of files that git does not track are left out,
    because the commit leaves those files out: pre-commit sets aside the
    unstaged changes of tracked files, but not untracked files. It never writes
    a file and never contacts the network.
    """
    root = Path(root).resolve()
    if not (root / STUDIES).is_dir():
        raise CheckError(f"{root} has no {STUDIES} folder")
    report = CheckReport(deleted=list(deleted))
    studies = []
    for folder in map(Path, folders):
        if is_v2_folder(folder := folder.resolve()):
            studies.append(folder)
        else:
            report.format_1 += 1
    # git runs first, so that a git failure stops the check before the slow part.
    workbooks = _workbook_problems(root, studies)
    untracked = _untracked(root, studies) if staged else set()
    for folder in studies:
        study = location(folder)
        report.checked.append(study)
        try:
            found = _validation_problems(folder, study, vocabulary)
        except CheckError:
            raise
        except OSError as error:
            found = [_unreadable(folder, study, error)]
        except Exception as error:  # a defect must not hide the other studies
            logging.getLogger(__name__).debug(
                "Check of %s failed", study, exc_info=True
            )
            found = [_failed(folder, study, error)]
        report.problems += _tracked_only(root, folder, found, untracked)
        if folder in workbooks:
            report.problems.append(workbooks[folder])
    report.problems += _repository_problems(root)
    return report
