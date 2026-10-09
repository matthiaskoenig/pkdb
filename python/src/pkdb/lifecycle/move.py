"""Rename or move a study format 2 folder: `pkdb move`."""

import warnings
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pkdb.cache import atomic_bytes
from pkdb.domain.vocabulary import Vocabulary
from pkdb.lifecycle.names import case_twin, parse_location
from pkdb.lifecycle.new import error_messages
from pkdb.repository import STUDIES, location
from pkdb.schemas.review import Review
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.jsonio import dump_json, load_json
from pkdb.studyformat.metadata import read_metadata
from pkdb.studyformat.models import (
    StudyMetadata,
    canonical_review_json,
    canonical_study_json,
)
from pkdb.studyformat.raw import parse_raw_file
from pkdb.studyformat.review_edit import read_review
from pkdb.studyformat.revision import (
    RevisionConflict,
    check_revision,
    read_revision,
    write_checked,
)
from pkdb.studyformat.sync import sync_study
from pkdb.studyformat.tables import (
    REFERENCE_JSON,
    REVIEW_JSON,
    STUDY_JSON,
)
from pkdb.studyformat.text import natural_key
from pkdb.studyformat.validation import is_v2_folder
from pkdb.studyformat.workbook.base import (
    SHEET_NAME_LIMIT,
    is_scratch_sheet,
    open_lock,
    state_path,
    workbook_path,
)

EDITS_IN_WORKBOOK = (
    "The workbook holds edits that are not in the tables; run pkdb tables sync first"
)


@dataclass(frozen=True)
class Moved:
    """A moved study: its new folder and what changed in it.

    `renamed` lists the old and new name of every renamed file, `targets`
    counts the review targets that now name a renamed file, `issue` and
    `pkdb_id` are the issue number and PKDB identifier of study.json, and
    `workbook` names the removed workbook. `assets` counts the provenance
    assets of study.json that now name a renamed file, and `reference` tells
    whether reference.json got the new name.
    """

    folder: Path
    renamed: list[tuple[str, str]]
    targets: int
    issue: int | None
    workbook: str | None = None
    assets: int = 0
    reference: bool = False
    pkdb_id: str | None = None


class MoveRefused(ValueError):
    """The study cannot be moved; nothing was changed."""


class MoveIncomplete(RuntimeError):
    """The move failed part way.

    `moved` is the study at its new place when only a step after the renames
    failed, and None when the renames could not be undone.
    """

    def __init__(self, message: str, moved: Moved | None):
        super().__init__(message)
        self.moved = moved


@dataclass(frozen=True)
class _Write:
    """A change of a JSON file that names a renamed file or the study.

    `original` and `revision` are its content when it was checked, which an
    undo writes back.
    """

    file: str
    text: str
    original: bytes
    revision: str


@dataclass(frozen=True)
class _Workbook:
    """The checked workbook: its name, and its size and modification time then."""

    name: str
    signature: tuple[int, int]


@dataclass(frozen=True)
class _Plan:
    """The checked move: folders, file renames and the JSON files that change."""

    old: Path
    new: Path
    renames: list[tuple[str, str]]
    writes: list[_Write]
    targets: int
    assets: int
    issue: int | None
    pkdb_id: str | None
    workbook: _Workbook | None


# What undoes one done step, and how a failure to undo it is named.
_Undo = tuple[str, Callable[[], object]]


def move_study(root: Path, old: str, new: str, vocabulary: Vocabulary) -> Moved:
    """Move the study `studies/<old>` of a checkout to `studies/<new>`.

    Every check runs before the first change. The folder and file renames and
    the writes of the files that name them or the study (review targets,
    provenance assets and the reference name) are undone together when one of
    them fails, so the move either happens or leaves the study as it was.
    Steps after them, removing the workbook and formatting, raise
    MoveIncomplete with the study at its new place.
    """
    plan = _plan(Path(root), old, new, vocabulary)
    _apply(plan)
    _remove_if_empty(plan.old.parent)
    problems = []
    # Only the checked workbook goes, which holds nothing beyond the tables,
    # and only while it is closed and unchanged since. Its state file is named
    # after the old study and goes with it, or alone as a leftover.
    workbook = plan.new / workbook_path(plan.old).name
    changed = plan.workbook is not None and (
        open_lock(workbook) is not None
        or _signature(workbook) != plan.workbook.signature
    )
    if changed:
        removed = []
        problems.append(
            f"{workbook.name} changed or was opened during the move, so it stays "
            "with its sync state; carry its edits over to the tables by hand and "
            "remove it"
        )
    elif plan.workbook is None:
        removed = [state_path(workbook)]
    else:
        removed = [workbook, state_path(workbook)]
    moved = Moved(
        plan.new,
        plan.renames,
        plan.targets,
        plan.issue,
        None if plan.workbook is None or changed else plan.workbook.name,
        plan.assets,
        any(write.file == REFERENCE_JSON for write in plan.writes),
        plan.pkdb_id,
    )
    for path in removed:
        try:
            path.unlink(missing_ok=True)
        except OSError as error:
            problems.append(
                f"{path.name} could not be removed ({_reason(error)}); remove it by hand"
            )
    try:
        formatted = format_folder(plan.new)
    except OSError as error:
        problems.append(f"pkdb format failed ({_reason(error)}); run it again")
    else:
        if not formatted.ok:
            problems.append(
                f"pkdb format found errors ({error_messages(formatted.issues)}); "
                "fix them and run pkdb format"
            )
    if problems:
        raise MoveIncomplete(
            f"Moved {_shown(plan.old)} to {_shown(plan.new)}, but "
            f"{'; and '.join(problems)}. The study stays at its new place.",
            moved,
        )
    return moved


def _plan(root: Path, old: str, new: str, vocabulary: Vocabulary) -> _Plan:
    """Check the move without changing anything."""
    old_folder = _old_folder(root, old)
    try:
        substance, name = parse_location(new)
    except ValueError as error:
        raise MoveRefused(str(error)) from None
    studies = root / STUDIES
    if (substance, name) == (old_folder.parent.name, old_folder.name):
        raise MoveRefused(f"The study is at {new} already")
    if (twin := case_twin(studies, substance)) is not None:
        raise MoveRefused(
            f"{STUDIES}/{substance} differs from {STUDIES}/{twin} only in case"
        )
    substances = studies / substance
    if substances.exists(follow_symlinks=False) and not substances.is_dir(
        follow_symlinks=False
    ):
        raise MoveRefused(f"{STUDIES}/{substance} is not a folder")
    if (twin := case_twin(substances, name)) is not None:
        shown = f"{STUDIES}/{substance}"
        message = f"{shown}/{name} differs from {shown}/{twin} only in case"
        if substances / twin == old_folder:
            message += (
                "; to change only the case, move the study to a temporary name "
                f"first and then to {new}"
            )
        raise MoveRefused(message)
    target = substances / name
    if target.exists(follow_symlinks=False):
        raise MoveRefused(f"{_shown(target)} exists already")

    renames = _renames(old_folder, name)
    _refuse_collisions(old_folder, renames, name)
    _refuse_long_sheets(renames, name)
    # A study that pkdb format cannot read would stop the move half way.
    formatted = format_folder(old_folder, check=True)
    if not formatted.ok:
        raise MoveRefused(
            f"{_shown(old_folder)} has errors ({error_messages(formatted.issues)}); "
            "fix them before the move"
        )
    workbook = _removable_workbook(old_folder, vocabulary)
    renamed = dict(renames)
    writes: list[_Write] = []
    try:
        document = read_review(old_folder)
        metadata = read_metadata(old_folder)
    except ValueError as error:
        raise MoveRefused(f"{_shown(old_folder)}: {error}") from None
    review, targets = _retarget(document.review, renamed)
    if targets:
        text = canonical_review_json(review)
        writes.append(_write_of(old_folder, REVIEW_JSON, text, document.revision))
    updated, assets = _reassets(metadata.metadata, renamed)
    if assets:
        text = canonical_study_json(updated)
        writes.append(_write_of(old_folder, STUDY_JSON, text, metadata.revision))
    if (reference := _renamed_reference(old_folder, name)) is not None:
        writes.append(reference)
    release = metadata.metadata.release
    return _Plan(
        old_folder,
        target,
        renames,
        writes,
        targets,
        assets,
        metadata.metadata.issue,
        None if release is None else release.pkdb_id,
        workbook,
    )


def _write_of(folder: Path, file: str, text: str, revision: str) -> _Write:
    """The write of a file read at `revision`, with that content kept for its undo."""
    original, current = read_revision(folder / file)
    if original is None or current != revision:
        raise MoveRefused(f"{file} changed while the move was checked; move again")
    return _Write(file, text, original, revision)


def _old_folder(root: Path, value: str) -> Path:
    """The folder of the existing study `<substance>/<name>`; a trailing slash is ignored.

    Both parts must have the exact case of the folders. On macOS and Windows a
    folder is found in any case, but the files are named after the exact study
    name, so a move under another case would leave them behind.
    """
    parts = value.removesuffix("/").split("/")
    if len(parts) != 2 or not all(parts) or any(p.startswith(".") for p in parts):
        raise MoveRefused(f"{value!r} is not <substance>/<name>")
    substance, name = parts
    studies = root / STUDIES
    found = None
    if (spelled := _spelling(studies, substance)) is not None:
        if (study := _spelling(studies / spelled, name)) is not None:
            found = (spelled, study)
    if found is not None and found != (substance, name):
        raise MoveRefused(
            f"{STUDIES}/{substance}/{name} is {STUDIES}/{found[0]}/{found[1]}; "
            "give it in that spelling"
        )
    folder = studies / substance / name
    if (
        found is None
        or not folder.is_dir(follow_symlinks=False)
        or not is_v2_folder(folder)
    ):
        raise MoveRefused(
            f"{STUDIES}/{substance}/{name} is not a study format 2 folder"
        )
    return folder


def _spelling(folder: Path, name: str) -> str | None:
    """The entry of `folder` named `name`, else the one that differs only in case, else None."""
    if not folder.is_dir(follow_symlinks=False):
        return None
    if name in (entry.name for entry in folder.iterdir()):
        return name
    return case_twin(folder, name)


def _shown(folder: Path) -> str:
    """`studies/<substance>/<name>` of a study folder."""
    return f"{STUDIES}/{location(folder)}"


def _renamed(file: str, old: str, new: str) -> str | None:
    """The name of a file of the study `old` in the study `new`, or None for a file not named after it.

    These are the files `<old>.<extension>` and `<old>_<anything>`: the PDF,
    the images, the raw tables, the digitizations and other attachments such
    as `<old>_Supp.pdf`. Hidden files, such as the sync state of the
    workbook, are not: a study name never starts with a dot.
    """
    if file.startswith((f"{old}.", f"{old}_")):
        return new + file[len(old) :]
    return None


def _renames(folder: Path, new: str) -> list[tuple[str, str]]:
    """The old and new names of the files named after the study, in natural order.

    The workbook is not renamed: the move removes it.
    """
    renames = []
    workbook = workbook_path(folder).name
    for path in sorted(folder.iterdir(), key=lambda item: natural_key(item.name)):
        if path.is_dir(follow_symlinks=False) or path.name == workbook:
            continue
        renamed = _renamed(path.name, folder.name, new)
        if renamed is not None and renamed != path.name:
            renames.append((path.name, renamed))
    return renames


def _refuse_collisions(folder: Path, renames: list[tuple[str, str]], new: str) -> None:
    """Refuse a new file name that another file of the folder has, also ignoring case.

    A rename would replace that file, at least on the file systems of macOS
    and Windows. When the name changes, another file named like the workbook
    of the new name, or its sync state, would be taken for them; the study's
    own workbook and state file are checked and removed by the move.
    """
    names: dict[str, set[str]] = defaultdict(set)
    for path in folder.iterdir():
        names[path.name.casefold()].add(path.name)
    if new != folder.name:
        own = workbook_path(folder)
        own_files = {own.name, state_path(own).name}
        workbook = workbook_path(folder.with_name(new))
        for file in (workbook.name, state_path(workbook).name):
            if others := sorted(names[file.casefold()] - own_files):
                raise MoveRefused(
                    f"{others[0]} in {_shown(folder)} would belong to the workbook "
                    "of the moved study; remove it first"
                )
    for before, after in renames:
        if others := sorted(names[after.casefold()] - {before}):
            raise MoveRefused(
                f"{before} would become {after}, which collides with {others[0]} of "
                f"{_shown(folder)}; rename or remove {others[0]} first"
            )


def _refuse_long_sheets(renames: list[tuple[str, str]], name: str) -> None:
    """Refuse a raw table whose workbook sheet name the move makes too long for Excel."""
    for old, new in renames:
        if parse_raw_file(new, name) is None:
            continue
        sheet = new.removesuffix(".tsv")
        if len(sheet) > SHEET_NAME_LIMIT >= len(old.removesuffix(".tsv")):
            raise MoveRefused(
                f"The raw table {old} would become {new}, whose sheet name has "
                f"{len(sheet)} characters; Excel limits sheet names to "
                f"{SHEET_NAME_LIMIT} characters. Choose a shorter study name."
            )


def _removable_workbook(folder: Path, vocabulary: Vocabulary) -> _Workbook | None:
    """The workbook of the study when it holds nothing beyond the tables, None without one.

    It must be closed, hold no edits that are not in the tables, and have no
    scratch sheets, which only a regeneration of the workbook keeps.
    """
    workbook = workbook_path(folder)
    # Taken first, so that a save during the checks shows when it is removed.
    if (signature := _signature(workbook)) is None:
        return None
    if (lock := open_lock(workbook)) is not None:
        raise MoveRefused(
            f"{workbook.name} is open in a spreadsheet program ({lock.name}); "
            "close it and run the move again"
        )
    result = sync_study(folder, vocabulary, check=True)
    if result.changes or result.conflicts:
        raise MoveRefused(EDITS_IN_WORKBOOK)
    if errors := [issue for issue in result.issues if issue.severity == "error"]:
        raise MoveRefused(
            f"{workbook.name} cannot be compared with the tables "
            f"({error_messages(errors)}); run pkdb tables sync first"
        )
    if scratch := _scratch_sheets(workbook):
        raise MoveRefused(
            f"{workbook.name} has the scratch sheets {', '.join(scratch)}, which the "
            "move would remove with the workbook; copy what you need and delete them first"
        )
    return _Workbook(workbook.name, signature)


def _signature(path: Path) -> tuple[int, int] | None:
    """The size and modification time of a file, or None without one."""
    try:
        status = path.stat()
    except FileNotFoundError:
        return None
    return status.st_size, status.st_mtime_ns


def _scratch_sheets(workbook: Path) -> list[str]:
    import openpyxl

    try:
        with warnings.catch_warnings():
            # openpyxl warns about parts of Excel files it does not support.
            warnings.filterwarnings("ignore", module="openpyxl")
            book = openpyxl.load_workbook(workbook, read_only=True)
    except Exception as error:
        # openpyxl raises many kinds of errors for a damaged or foreign file.
        raise MoveRefused(f"{workbook.name} cannot be read: {error}") from None
    try:
        return [name for name in book.sheetnames if is_scratch_sheet(name)]
    finally:
        book.close()


def _retarget(review: Review, renamed: dict[str, str]) -> tuple[Review, int]:
    """The review with the targets of renamed files renamed, and how many changed.

    An acknowledgement of a warning is a review item with a target, so it follows too.
    """
    items, count = [], 0
    for item in review.items:
        target = item.target
        if target is not None and target.file in renamed:
            target = target.model_copy(update={"file": renamed[target.file]})
            item = item.model_copy(update={"target": target})
            count += 1
        items.append(item)
    return review.model_copy(update={"items": items}), count


def _reassets(
    metadata: StudyMetadata, renamed: dict[str, str]
) -> tuple[StudyMetadata, int]:
    """study.json with the provenance assets that name a renamed file renamed, and how many changed.

    An automatic curation or a data import names the files it read, such as the PDF.
    """
    provenance = metadata.provenance
    assets = getattr(provenance, "assets", None) or []
    count = sum(asset.url in renamed for asset in assets)
    if not count:
        return metadata, 0
    assets = [
        asset.model_copy(update={"url": renamed[asset.url]})
        if asset.url in renamed
        else asset
        for asset in assets
    ]
    provenance = provenance.model_copy(update={"assets": assets})
    return metadata.model_copy(update={"provenance": provenance}), count


def _renamed_reference(folder: Path, new: str) -> _Write | None:
    """reference.json with the new study name, when its name is the old study name.

    Another name, such as one with an umlaut or of a publication with several
    studies, names the publication and stays.
    """
    original, revision = read_revision(folder / REFERENCE_JSON)
    if original is None:
        return None
    try:
        reference = load_json(original)
    except ValueError as error:
        raise MoveRefused(f"{_shown(folder)}: {error}") from None
    if (
        new == folder.name
        or not isinstance(reference, dict)
        or reference.get("name") != folder.name
    ):
        return None
    text = dump_json({**reference, "name": new})
    return _Write(REFERENCE_JSON, text, original, revision)


def _apply(plan: _Plan) -> None:
    """Rename the folder and its files and write the JSON files, or undo every step."""
    substances = plan.new.parent
    created = False
    done: list[_Undo] = []
    try:
        if not substances.exists():
            substances.mkdir()
            created = True
        if plan.new.exists(follow_symlinks=False):
            raise MoveRefused(f"{_shown(plan.new)} exists already")
        _rename(plan.old, plan.new, done)
        for old, new in plan.renames:
            _rename(plan.new / old, plan.new / new, done)
        for write in plan.writes:
            _write(plan.new / write.file, write, done)
    except BaseException as error:
        failures = _undo(done)
        if created:
            _remove_if_empty(substances)
        what = f"move {_shown(plan.old)} to {_shown(plan.new)}"
        if failures:
            raise MoveIncomplete(
                f"Cannot {what}: {_reason(error)}. Undoing the move failed "
                f"({'; '.join(failures)}); finish or undo it by hand.",
                None,
            ) from error
        if isinstance(error, (OSError, RevisionConflict)):
            raise MoveRefused(
                f"Cannot {what}: {_reason(error)}. Nothing was changed."
            ) from error
        raise


def _rename(source: Path, target: Path, done: list[_Undo]) -> None:
    source.rename(target)
    done.append((f"{target.name} to {source.name}", lambda: target.rename(source)))


def _write(path: Path, write: _Write, done: list[_Undo]) -> None:
    written = write_checked(path, write.text, write.revision)

    def undo() -> None:
        # A change by another writer since is not overwritten.
        check_revision(path, written)
        atomic_bytes(path, write.original)

    done.append((f"{path.name} back to its content", undo))


def _undo(done: list[_Undo]) -> list[str]:
    """Undo the done steps in reverse order; the steps that could not be undone."""
    failures = []
    for name, undo in reversed(done):
        try:
            undo()
        except (OSError, RevisionConflict) as error:
            failures.append(f"{name}: {_reason(error)}")
    return failures


def _reason(error: BaseException) -> str:
    if isinstance(error, OSError):
        reason = str(error.strerror or error)
        return f"{reason} ({error.filename})" if error.filename else reason
    return str(error)


def _remove_if_empty(folder: Path) -> None:
    try:
        folder.rmdir()
    except OSError:
        pass
