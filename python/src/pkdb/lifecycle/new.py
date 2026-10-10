"""Create a study format 2 folder: `pkdb new`."""

import hashlib
import json
import shutil
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from pkdb.identity import Author
from pkdb.lifecycle.names import case_twin, parse_location
from pkdb.references import ReferenceError, ReferenceResolver, sync_reference
from pkdb.repository import PAPERS, STUDIES
from pkdb.schemas.review import Review
from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.load import validation_issues
from pkdb.studyformat.models import (
    StudyMetadata,
    canonical_review_json,
    canonical_study_json,
)
from pkdb.studyformat.tables import (
    REFERENCE_JSON,
    REVIEW_JSON,
    ROOT,
    SOURCE_PATTERN,
    STUDY_JSON,
    SUBJECTS,
)
from pkdb.studyformat.text import natural_key, render_tsv

# Automatic curations are a source of their own: on the server such a study
# stands beside a manual curation of the same paper.
AUTOMATIC_SOURCE_KEY = "pkdb.ai"
# The keywords of the sources of paper images, see SOURCE_PATTERN.
SOURCE_KEYWORDS = ("Text", "Tab", "Fig")


class NewStudyRefused(ValueError):
    """The study cannot be created; nothing was written."""


@dataclass(frozen=True)
class NewStudy:
    """A created study and what happened to its paper folder.

    `moved` and `left` name the files taken from and left in the paper folder;
    `misnamed` maps a left file to the name it differs from only in case.
    `reference` is the change of reference.json, `new_substance` tells
    whether the substance folder was created for the study, and `warnings`
    name what could not be cleaned up after the study was complete.
    """

    folder: Path
    moved: list[str]
    left: list[str]
    reference: str | None
    misnamed: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    new_substance: bool = False


@dataclass(frozen=True)
class _PaperFiles:
    """The files of a paper folder: taken by the study, left, and left because of their case."""

    taken: list[Path] = field(default_factory=list)
    left: list[str] = field(default_factory=list)
    misnamed: dict[str, str] = field(default_factory=dict)


def create_study(
    root: Path,
    location: str,
    *,
    pmid: str | None,
    doi: str | None,
    licence: str,
    access: str,
    author: Author,
    resolver: ReferenceResolver,
    agent_version: str | None = None,
    run_id: str | None = None,
    assets: Sequence[Path] = (),
) -> NewStudy:
    """Create the draft study `studies/<location>` of a checkout.

    The study is built in a hidden folder beside it and renamed into place, so
    a refusal or an error leaves neither a study nor a change in `papers/`.
    """
    try:
        substance, name = parse_location(location)
    except ValueError as error:
        raise NewStudyRefused(str(error)) from None
    studies = Path(root) / STUDIES
    _refuse_case_twin(studies, substance, STUDIES)
    substances = studies / substance
    _refuse_case_twin(substances, name, f"{STUDIES}/{substance}")
    target = substances / name
    if target.exists():
        raise NewStudyRefused(f"{STUDIES}/{substance}/{name} exists already")
    if access == "public":
        raise NewStudyRefused(
            "A new study is private until its release; create it with --access "
            "private and set access to public when you release it."
        )
    if pmid is not None and doi is not None:
        raise NewStudyRefused("Give a PubMed ID or a DOI, not both")
    if pmid is None and doi is None:
        raise NewStudyRefused("Give a PubMed ID or a DOI")
    paper = Path(root) / PAPERS / substance / name
    shown = f"{PAPERS}/{substance}/{name}"
    found = _paper_files(paper, name)
    pdf = [path for path in found.taken if path.name == f"{name}.pdf"]
    provenance = _provenance(author, agent_version, run_id, pdf, assets)
    if author.agent is not None and provenance is None:
        raise NewStudyRefused(
            f"An automatic curation names what it read: {_pdf_hint(found, name, shown)} "
            "or pass --asset FILE"
        )
    metadata = _metadata(pmid, doi, licence, access, author, provenance)

    new_substance = not substances.exists()
    substances.mkdir(exist_ok=True)
    staging = substances / f".{name}.new"
    warnings: list[str] = []
    try:
        warnings += _remove_leftover(staging, name, f"{STUDIES}/{substance}")
        try:
            staging.mkdir()
        except FileExistsError:
            raise NewStudyRefused(
                f"{STUDIES}/{substance}/{staging.name} exists: another pkdb new of "
                f"{substance}/{name} may be running, or one was interrupted. Remove "
                "the folder only when no pkdb new is running."
            ) from None
        try:
            # The folder has the study's name: formatting writes it into the
            # tables and the reference takes it as its name.
            folder = staging / name
            reference = _build(folder, metadata, found.taken, resolver)
            if target.exists():
                raise NewStudyRefused(f"{STUDIES}/{substance}/{name} exists already")
            folder.rename(target)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
    finally:
        # A substance folder made for a refused study goes again.
        if new_substance:
            _remove_if_empty(substances)
    # The study is complete: what cannot be cleaned up now is only a warning.
    try:
        staging.rmdir()
    except OSError as error:
        warnings.append(
            f"{STUDIES}/{substance}/{staging.name} stays: {_reason(error)}. Remove "
            "the empty folder by hand."
        )
    for path in found.taken:
        try:
            path.unlink(missing_ok=True)
        except OSError as error:
            warnings.append(
                f"{path.name} is in the study but stays in {shown}: "
                f"{_reason(error)}. Remove it by hand."
            )
    if paper.is_dir():
        _remove_if_empty(paper)
        _remove_if_empty(paper.parent)
    return NewStudy(
        target,
        [path.name for path in found.taken],
        found.left,
        reference,
        found.misnamed,
        warnings,
        new_substance,
    )


def _remove_leftover(staging: Path, name: str, shown: str) -> list[str]:
    """Remove the hidden folder of a pkdb new that was killed, and say so in a warning.

    The study was not renamed into place (the caller refused a study that
    exists), so the folder never became a study. Only a folder that holds
    nothing but the study folder is removed; anything else, a symbolic link
    included, stays and is refused by the caller.
    """
    if staging.is_symlink() or not staging.is_dir():
        return []
    try:
        children = list(staging.iterdir())
        if any(
            child.name != name or child.is_symlink() or not child.is_dir()
            for child in children
        ):
            return []
        shutil.rmtree(staging)
    except OSError as error:
        raise NewStudyRefused(
            f"{shown}/{staging.name} is left over from an interrupted pkdb new "
            f"and cannot be removed: {_reason(error)}. Remove the folder by hand."
        ) from None
    return [
        f"Removed {shown}/{staging.name}, left over from an interrupted pkdb new "
        f"of {name}."
    ]


def _build(
    folder: Path,
    metadata: StudyMetadata,
    papers: list[Path],
    resolver: ReferenceResolver,
) -> str | None:
    """Write the files of a new study and return the reference change."""
    folder.mkdir()
    _write(folder / STUDY_JSON, canonical_study_json(metadata))
    _write(folder / REVIEW_JSON, canonical_review_json(Review(status="draft")))
    row = tuple(ROOT if column == "name" else "" for column in SUBJECTS.names)
    _write(folder / f"{SUBJECTS.kind}.tsv", render_tsv(SUBJECTS.names, [row]))
    for path in papers:
        shutil.copyfile(path, folder / path.name)
    try:
        reference = sync_reference(folder, resolver)
    except ReferenceError as error:
        raise NewStudyRefused(str(error)) from None
    formatted = format_folder(folder)
    if not formatted.ok:
        raise NewStudyRefused(error_messages(formatted.issues))
    return reference


def _refuse_case_twin(folder: Path, name: str, shown: str) -> None:
    """Refuse a name that only differs in case from an entry of the folder."""
    if (twin := case_twin(folder, name)) is not None:
        raise NewStudyRefused(
            f"{shown}/{name} differs from {shown}/{twin} only in case"
        )


def _paper_name(file: str, study: str) -> str | None:
    """The name of a file that `pkdb new` takes that `file` equals ignoring case.

    These are the PDF `<study>.pdf` and the images `<study>_<source>.png`
    with a source as in SOURCE_PATTERN. None for any other file.
    """
    if file.casefold() == f"{study}.pdf".casefold():
        return f"{study}.pdf"
    head, source, suffix = file[: len(study) + 1], file[len(study) + 1 : -4], file[-4:]
    if head.casefold() != f"{study}_".casefold() or suffix.casefold() != ".png":
        return None
    for keyword in SOURCE_KEYWORDS:
        if source[: len(keyword)].casefold() == keyword.casefold():
            source = keyword + source[len(keyword) :]
            break
    if SOURCE_PATTERN.fullmatch(source) is None:
        return None
    return f"{study}_{source}.png"


def _paper_files(paper: Path, study: str) -> _PaperFiles:
    """The files of a paper folder that the study takes, and the others."""
    found = _PaperFiles()
    if not paper.is_dir():
        return found
    for path in sorted(paper.iterdir(), key=lambda item: natural_key(item.name)):
        expected = (
            _paper_name(path.name, study)
            if path.is_file(follow_symlinks=False)
            else None
        )
        if expected == path.name:
            found.taken.append(path)
            continue
        found.left.append(path.name)
        if expected is not None:
            found.misnamed[path.name] = expected
    return found


def _pdf_hint(found: _PaperFiles, study: str, shown: str) -> str:
    """How to give an agent's study its PDF: rename one that differs in case, or add it."""
    pdf = f"{study}.pdf"
    for file, expected in found.misnamed.items():
        if expected == pdf:
            return f"rename {shown}/{file} to {pdf}"
    return f"put {pdf} into {shown}/"


def _provenance(
    author: Author,
    version: str | None,
    run_id: str | None,
    pdf: list[Path],
    assets: Sequence[Path],
) -> dict | None:
    """The automatic curation of an agent that read the PDF and the assets.

    None for a person, and for an agent that names no file.
    """
    read = [*pdf, *assets]
    if author.agent is None:
        if version is not None or run_id is not None or assets:
            raise NewStudyRefused(
                "--agent-version, --run-id and --asset describe an automatic "
                "curation; pass --agent as well"
            )
        return None
    if not version or not run_id:
        raise NewStudyRefused(
            "An automatic curation needs --agent-version and --run-id"
        )
    if not read:
        return None
    return {
        "kind": "automatic_curation",
        "source_key": AUTOMATIC_SOURCE_KEY,
        "method": author.agent,
        "version": version,
        "run_id": run_id,
        "assets": _assets(read),
    }


def _assets(files: Iterable[Path]) -> list[dict[str, str]]:
    """The file name and SHA-256 of each file, without repeats."""
    assets: list[dict[str, str]] = []
    for path in files:
        if not path.is_file():
            raise NewStudyRefused(f"The asset {path} is not a file")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        asset = {"url": path.name, "sha256": digest}
        if asset not in assets:
            assets.append(asset)
    return assets


def _metadata(
    pmid: str | None,
    doi: str | None,
    licence: str,
    access: str,
    author: Author,
    provenance: dict | None,
) -> StudyMetadata:
    """The checked study.json of the new study."""
    data: dict = {
        "format": 2,
        "reference": {"pmid": pmid} if pmid is not None else {"doi": doi},
        "creator": author.user,
        "licence": licence,
        "access": access,
    }
    if provenance is not None:
        data["provenance"] = provenance
    try:
        return StudyMetadata.model_validate(data)
    except ValidationError as error:
        issues = validation_issues(error, STUDY_JSON, "invalid_study_json")
        raise NewStudyRefused("; ".join(issue.message for issue in issues)) from None


def error_messages(issues: Iterable[ValidationIssue]) -> str:
    """The error messages of issues, each with its file when it has one."""
    return "; ".join(
        f"{issue.source.file}: {issue.message}"
        if issue.source is not None and issue.source.file
        else issue.message
        for issue in issues
        if issue.severity == "error"
    )


def citation(folder: Path) -> str | None:
    """First author, year and title of the paper in reference.json, such as `Smith et al. (2020) Title`.

    None when reference.json cannot be read or names none of them.
    """
    try:
        reference = json.loads((folder / REFERENCE_JSON).read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    if not isinstance(reference, dict):
        return None
    authors = reference.get("authors")
    authors = authors if isinstance(authors, list) else []
    first = authors[0] if authors and isinstance(authors[0], dict) else {}
    author = first.get("last_name") or first.get("organization") or ""
    if author and len(authors) > 1:
        author += " et al."
    year = str(reference.get("publication_date") or reference.get("date") or "")[:4]
    parts = [author, f"({year})" if year else "", reference.get("title") or ""]
    return " ".join(str(part) for part in parts if part) or None


def _reason(error: OSError) -> str:
    return error.strerror or str(error)


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="")


def _remove_if_empty(folder: Path) -> None:
    try:
        folder.rmdir()
    except OSError:
        pass
