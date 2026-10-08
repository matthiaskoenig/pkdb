"""Run the migration over the study folders of a pkdb_data checkout.

A study whose conversion the gate proves (`identical` or `intended`) replaces
its v1 folder by a swap of two renames below the repository root:

1. `studies/<substance>/<name>` -> `.pkdb-migrate/v1/<substance>/<name>`
2. `.pkdb-migrate/new/<substance>/<name>` -> `studies/<substance>/<name>`

and the backup of step 1 is deleted afterwards. A run interrupted between the
renames leaves the backup behind; the next run puts it back or, when the swap
had finished, deletes it. A dry run never recovers: it refuses to start while
`.pkdb-migrate` exists. An exclusive lock on the repository root folder keeps a
second run from starting while one works on the checkout.
"""

import json
import multiprocessing
import os
import shutil
import tempfile
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from pkdb.cache import bundled_vocabulary
from pkdb.domain.vocabulary import Vocabulary
from pkdb.migration.convert import convert_study
from pkdb.migration.gate import judge
from pkdb.migration.model import (
    Decision,
    MigrationReport,
    NotConverted,
    PaperMove,
    StudyResult,
)
from pkdb.migration.registry import Registry
from pkdb.migration.report import write_report
from pkdb.references import ReferenceError, ReferenceResolver, sync_reference
from pkdb.studyformat.tables import REFERENCE_JSON, STUDY_JSON
from pkdb.studyformat.text import natural_key
from pkdb.studyformat.validation import is_v2_folder

# The work folder below the repository root; it exists only while a run works.
WORK = ".pkdb-migrate"
# Below the work folder: converted studies, v1 copies with a resolved reference
# and the v1 folders of swaps in progress, each as `<substance>/<name>`.
NEW = "new"
SOURCE = "source"
BACKUP = "v1"
STUDIES = "studies"
PAPERS = "papers"
PROVEN = ("identical", "intended")
# The reason of a study whose worker process stopped before it gave a result.
STOPPED = "converter_error: the worker process stopped"


class SwapError(RuntimeError):
    """A swap failed half way and its v1 folder could not be put back."""


class RunRefused(ValueError):
    """The run cannot start, and changed nothing; the message says why."""


@dataclass(frozen=True)
class Task:
    """One v1 study for `_one`; `work` is the work folder of the run."""

    v1: Path
    work: Path
    registry: Registry
    approver: str | None
    vocabulary: Vocabulary
    dry_run: bool
    resolver_factory: Callable[[], ReferenceResolver]


def repository_root(path: Path) -> Path:
    """The folder that contains `studies/`, found by walking up from `path`."""
    path = Path(path).resolve()
    for folder in (path, *path.parents):
        if (folder / STUDIES).is_dir():
            return folder
    raise ValueError(f"No folder above {path} contains a studies folder")


def _location(folder: Path) -> str:
    """The `<substance>/<name>` of a study folder."""
    return f"{folder.parent.name}/{folder.name}"


def _sorted(locations: Iterable[str]) -> list[str]:
    return sorted(locations, key=natural_key)


def _exists(path: Path) -> bool:
    return path.exists(follow_symlinks=False)


def _rename(source: Path, target: Path) -> None:
    """Rename atomically; refuses an existing target and another file system."""
    if _exists(target):
        raise FileExistsError(f"{target} exists")
    source.rename(target)


def _remove(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def _subfolders(folder: Path) -> list[Path]:
    """Folders below `folder`, without hidden folders and symbolic links."""
    return [
        path
        for path in folder.iterdir()
        if not path.name.startswith(".") and path.is_dir(follow_symlinks=False)
    ]


def _recover(root: Path, report: MigrationReport) -> None:
    """Finish or undo the swaps of an interrupted run, then delete its work folder."""
    work = root / WORK
    backups = work / BACKUP
    found = backups.glob("*/*") if backups.is_dir() else []
    for backup in sorted(found, key=lambda path: natural_key(_location(path))):
        location = _location(backup)
        folder = root / STUDIES / location
        if not _exists(folder):
            folder.parent.mkdir(parents=True, exist_ok=True)
            _rename(backup, folder)
        elif is_v2_folder(folder):
            shutil.rmtree(backup)
        else:
            raise ValueError(
                f"{backup} and {folder} both hold the format 1 study {location}; "
                f"keep one by hand, delete {work} and run again"
            )
        report.recovered.append(location)
    if _exists(work):
        shutil.rmtree(work)


def _discover(paths: list[Path], root: Path) -> list[Path]:
    """The study folders of the studies folder, substance folders and study folders."""
    studies = root / STUDIES
    folders: set[Path] = set()
    for path in paths:
        path = Path(path).resolve()
        if not path.is_dir():
            raise ValueError(f"{path} is not a folder")
        match len(path.relative_to(studies).parts):
            case 0:
                for substance in _subfolders(path):
                    folders.update(_subfolders(substance))
            case 1:
                folders.update(_subfolders(path))
            case 2:
                folders.add(path)
            case _:
                raise ValueError(
                    f"{path} is not the studies folder, a substance folder or a study folder"
                )
    return sorted(folders, key=lambda folder: natural_key(_location(folder)))


def _check_paths(paths: list[Path], root: Path) -> None:
    studies = root / STUDIES
    for path in paths:
        if not Path(path).resolve().is_relative_to(studies):
            raise ValueError(f"{path} is not in the studies folder {studies}")


def _files(folder: Path) -> list[str]:
    """Every file below a folder (anything but a folder), relative to it."""
    files = (
        path.relative_to(folder).as_posix()
        for path in folder.rglob("*")
        if not path.is_dir(follow_symlinks=False)
    )
    return sorted(files, key=natural_key)


def _paper(folder: Path, root: Path, report: MigrationReport, dry_run: bool) -> None:
    """Move a folder without study.json to `papers/`, unless that folder exists."""
    location = _location(folder)
    target = root / PAPERS / location
    if _exists(target):
        report.studies.append(
            StudyResult(
                study=location,
                outcome="not_converted",
                reason=(
                    f"papers_exists: {PAPERS}/{location} exists; "
                    "merge the two folders by hand"
                ),
            )
        )
        return
    files = _files(folder)
    report.papers.append(
        PaperMove(
            source=folder.relative_to(root).as_posix(),
            target=target.relative_to(root).as_posix(),
            files=files,
            workbook=any(name.lower().endswith(".xlsx") for name in files),
        )
    )
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        _rename(folder, target)


def _triage(
    folders: list[Path], root: Path, report: MigrationReport, dry_run: bool
) -> list[Path]:
    """Remove empty folders, move papers, skip format 2 folders; return the v1 studies."""
    tasks = []
    for folder in folders:
        if not _files(folder):
            report.removed_empty.append(_location(folder))
            if not dry_run:
                shutil.rmtree(folder)
        elif is_v2_folder(folder):
            report.skipped.append(_location(folder))
        elif not _exists(folder / STUDY_JSON):
            _paper(folder, root, report, dry_run)
        else:
            tasks.append(folder)
    return tasks


def _not_converted(study: str, reason: str) -> StudyResult:
    return StudyResult(study=study, outcome="not_converted", reason=reason)


def _attempt(task: Task, target: Path, copy: Path) -> StudyResult:
    """Convert and judge one study; the v1 folder is only read."""
    resolver = task.resolver_factory()
    v1 = task.v1
    study = _location(v1)
    decisions: list[Decision] = []
    if not _exists(v1 / REFERENCE_JSON):
        # The v1 folder stays as it is: the reference is resolved in a copy.
        shutil.copytree(v1, copy, symlinks=True)
        try:
            change = sync_reference(copy, resolver)
        except ReferenceError as error:
            return _not_converted(study, f"reference: {error}")
        if change is not None:
            decisions.append(Decision(kind="reference_resolved", detail=change))
        v1 = copy
    try:
        conversion = convert_study(
            v1,
            target,
            registry=task.registry,
            approver=task.approver,
            resolver=resolver,
        )
    except NotConverted as error:
        if error.code == "unreadable":
            judged = judge(v1, target, task.vocabulary)
            if judged.outcome == "invalid_v1":
                return judged
        return _not_converted(study, f"{error.code}: {error.message}")
    result = judge(v1, conversion.folder, task.vocabulary)
    return result.model_copy(update={"decisions": [*decisions, *conversion.decisions]})


def _one(task: Task) -> StudyResult:
    """Convert one study into `work/new/<substance>/<name>` and judge it.

    Never raises for a study: any error becomes `not_converted`. Only the
    folder of a proven study of a real run is kept, for its swap.
    """
    location = _location(task.v1)
    target = task.work / NEW / location
    copy = task.work / SOURCE / location
    try:
        result = _attempt(task, target, copy)
    except Exception as error:
        result = _not_converted(
            location, f"converter_error: {type(error).__name__}: {error}"
        )
    _remove(copy)
    if task.dry_run or result.outcome not in PROVEN:
        _remove(target)
    return result


def _without_result(task: Task, error: Exception) -> StudyResult:
    """A study whose worker gave no result; its work folders are deleted."""
    location = _location(task.v1)
    _remove(task.work / NEW / location)
    _remove(task.work / SOURCE / location)
    if isinstance(error, BrokenProcessPool):
        return _not_converted(location, STOPPED)
    return _not_converted(location, f"converter_error: {type(error).__name__}: {error}")


def _results(tasks: list[Task], jobs: int | None) -> Iterator[StudyResult]:
    """The result of each task as it completes; one job runs in this process.

    A worker process that stops breaks the pool: every study without a
    result yet is not converted, and the run goes on with the others.
    """
    if not tasks:
        return
    if jobs == 1:
        yield from map(_one, tasks)
        return
    executor = ProcessPoolExecutor(
        max_workers=jobs or os.cpu_count(),
        mp_context=multiprocessing.get_context("spawn"),
    )
    try:
        futures: dict[Future[StudyResult], Task] = {}
        unsubmitted: list[tuple[Task, Exception]] = []
        for task in tasks:
            try:
                futures[executor.submit(_one, task)] = task
            except BrokenProcessPool as error:
                unsubmitted.append((task, error))
        for future in as_completed(futures):
            try:
                result = future.result()
            except Exception as error:
                result = _without_result(futures[future], error)
            yield result
        for task, error in unsubmitted:
            yield _without_result(task, error)
    finally:
        executor.shutdown(cancel_futures=True)


def _swap(root: Path, folder: Path) -> None:
    """Replace a v1 study folder by its converted folder.

    Raises OSError when the v1 folder is in place, unchanged, and SwapError when
    it is left in `.pkdb-migrate/v1` for the next run to put back.
    """
    location = _location(folder)
    new = root / WORK / NEW / location
    backup = root / WORK / BACKUP / location
    backup.parent.mkdir(parents=True, exist_ok=True)
    _rename(folder, backup)
    try:
        _rename(new, folder)
    except BaseException:
        try:
            _rename(backup, folder)
        except OSError as error:
            raise SwapError(
                f"The v1 folder of {location} is in {backup}; "
                "run pkdb migrate again to put it back"
            ) from error
        raise
    # The converted folder is in place; a backup left behind is deleted with the work folder.
    _remove(backup)


def _released(root: Path) -> set[str]:
    """The `release.pkdb_id` of every format 2 study.json below root/studies."""
    released = set()
    for substance in _subfolders(root / STUDIES):
        for folder in _subfolders(substance):
            if not is_v2_folder(folder):
                continue
            try:
                data = json.loads((folder / STUDY_JSON).read_text(encoding="utf-8"))
            except OSError, ValueError:
                continue
            release = data.get("release") if isinstance(data, dict) else None
            if isinstance(release, dict) and isinstance(release.get("pkdb_id"), str):
                released.add(release["pkdb_id"])
    return released


def _registry(
    root: Path,
    registry_path: Path | None,
    registry: Registry,
    report: MigrationReport,
    dry_run: bool,
) -> None:
    """List the registry findings; delete the registry once every study is released."""
    findings = registry.findings(root)
    if (
        registry_path is not None
        and not dry_run
        and set(registry.identifiers) <= _released(root)
    ):
        registry_path.unlink()
        findings = findings.model_copy(update={"deleted": True})
    report.registry = findings


@contextmanager
def _locked(root: Path) -> Iterator[None]:
    """Hold an exclusive lock on the repository root folder; refuse a second run."""
    try:
        import fcntl
    except ImportError:
        raise RunRefused("pkdb migrate needs Linux or macOS.") from None
    descriptor = os.open(root, os.O_RDONLY)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RunRefused(
                f"Another pkdb migrate is running in {root}; wait for it to finish."
            ) from None
        try:
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


@contextmanager
def _work_folder(root: Path, dry_run: bool) -> Iterator[Path]:
    """`.pkdb-migrate` for a real run, a temporary folder for a dry run.

    `.pkdb-migrate` stays after an error, so the next run can recover its swaps.
    """
    if dry_run:
        with tempfile.TemporaryDirectory(prefix="pkdb-migrate-") as work:
            yield Path(work)
        return
    work = root / WORK
    yield work
    # Every swap deletes or puts back its backup; never delete one unseen.
    if any((work / BACKUP).glob("*/*")):
        raise SwapError(
            f"{work / BACKUP} still holds v1 folders; run pkdb migrate again to "
            "put them back"
        )
    if _exists(work):
        shutil.rmtree(work)


def migrate(
    paths: list[Path],
    *,
    report: Path,
    registry: Path | None,
    approver: str | None,
    dry_run: bool = False,
    jobs: int | None = None,
    vocabulary: Vocabulary | None = None,
    resolver_factory: Callable[[], ReferenceResolver] = ReferenceResolver,
) -> MigrationReport:
    """Convert the v1 studies below `paths` and write the report.

    `paths` are the studies folder, substance folders or study folders of one
    checkout. Only proven studies replace their v1 folder. A dry run writes
    only the report; it refuses to start while an interrupted run's
    `.pkdb-migrate` exists. Raises RunRefused when the run cannot start.
    """
    if not paths:
        raise ValueError(
            "Name the studies folder, a substance folder or a study folder"
        )
    if jobs is not None and jobs < 1:
        raise ValueError("The number of jobs must be at least 1")
    root = repository_root(paths[0])
    _check_paths(paths, root)
    known = Registry.read(registry)
    vocabulary = vocabulary if vocabulary is not None else bundled_vocabulary()
    with _locked(root):
        summary = MigrationReport(dry_run=dry_run)
        if dry_run and _exists(root / WORK):
            raise RunRefused(
                f"An interrupted run left {WORK} in {root}; run pkdb migrate "
                "without --dry-run to finish or undo it."
            )
        if not dry_run:
            _recover(root, summary)
        folders = _triage(_discover(paths, root), root, summary, dry_run)
        with _work_folder(root, dry_run) as work:
            tasks = [
                Task(
                    v1=folder,
                    work=work,
                    registry=known,
                    approver=approver,
                    vocabulary=vocabulary,
                    dry_run=dry_run,
                    resolver_factory=resolver_factory,
                )
                for folder in folders
            ]
            for study in _results(tasks, jobs):
                if not dry_run and study.outcome in PROVEN:
                    try:
                        _swap(root, root / STUDIES / study.study)
                    except OSError as error:
                        study = study.model_copy(
                            update={
                                "outcome": "not_converted",
                                "reason": f"swap: {type(error).__name__}: {error}",
                            }
                        )
                    else:
                        study = study.model_copy(update={"written": True})
                summary.studies.append(study)
        _registry(root, registry, known, summary, dry_run)
        summary.studies.sort(key=lambda study: natural_key(study.study))
        summary.skipped = _sorted(summary.skipped)
        summary.removed_empty = _sorted(summary.removed_empty)
        summary.recovered = _sorted(summary.recovered)
        summary.papers.sort(key=lambda move: natural_key(move.source))
        write_report(summary, report)
        return summary
