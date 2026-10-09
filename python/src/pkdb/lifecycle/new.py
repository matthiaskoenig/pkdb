"""Create a study format 2 folder: `pkdb new`."""

import hashlib
import shutil
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from pkdb.identity import Author
from pkdb.lifecycle.names import parse_location
from pkdb.references import ReferenceError, ReferenceResolver, sync_reference
from pkdb.repository import STUDIES
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
    REVIEW_JSON,
    ROOT,
    SOURCE_PATTERN,
    STUDY_JSON,
    SUBJECTS,
)
from pkdb.studyformat.text import natural_key, render_tsv

PAPERS = "papers"
# Automatic curations are a source of their own: on the server such a study
# stands beside a manual curation of the same paper.
AUTOMATIC_SOURCE_KEY = "pkdb.ai"


class NewStudyRefused(ValueError):
    """The study cannot be created; nothing was written."""


@dataclass(frozen=True)
class NewStudy:
    """A created study: its folder, the files taken from and left in its paper folder, and the reference change."""

    folder: Path
    moved: list[str]
    left: list[str]
    reference: str | None


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
    if pmid is not None and doi is not None:
        raise NewStudyRefused("Give a PubMed ID or a DOI, not both")
    if pmid is None and doi is None:
        raise NewStudyRefused("Give a PubMed ID or a DOI")
    paper = Path(root) / PAPERS / substance / name
    taken, left = _paper_files(paper, name)
    pdf = [path for path in taken if path.name == f"{name}.pdf"]
    provenance = _provenance(author, agent_version, run_id, pdf, assets)
    if author.agent is not None and provenance is None:
        raise NewStudyRefused(
            f"An automatic curation names what it read: put {name}.pdf into "
            f"{PAPERS}/{substance}/{name}/ or pass --asset FILE"
        )
    metadata = _metadata(pmid, doi, licence, access, author, provenance)

    new_substance = not substances.exists()
    substances.mkdir(exist_ok=True)
    staging = substances / f".{name}.new"
    try:
        try:
            staging.mkdir()
        except FileExistsError:
            raise NewStudyRefused(
                f"{STUDIES}/{substance}/{staging.name} is left from an interrupted "
                "pkdb new; remove it and try again"
            ) from None
        try:
            # The folder has the study's name: formatting writes it into the
            # tables and the reference takes it as its name.
            folder = staging / name
            reference = _build(folder, metadata, taken, resolver)
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
    staging.rmdir()
    for path in taken:
        path.unlink(missing_ok=True)
    if paper.is_dir():
        _remove_if_empty(paper)
        _remove_if_empty(paper.parent)
    return NewStudy(target, [path.name for path in taken], left, reference)


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
        raise NewStudyRefused(_errors(formatted.issues))
    return reference


def _refuse_case_twin(folder: Path, name: str, shown: str) -> None:
    """Refuse a name that only differs in case from an entry of the folder.

    Such names collide on the file systems of macOS and Windows.
    """
    if not folder.is_dir():
        return
    for entry in folder.iterdir():
        if entry.name != name and entry.name.casefold() == name.casefold():
            raise NewStudyRefused(
                f"{shown}/{name} differs from {shown}/{entry.name} only in case"
            )


def _is_paper_file(file: str, study: str) -> bool:
    """Whether `pkdb new` takes a file of the paper folder: the PDF or an image of a source."""
    if file == f"{study}.pdf":
        return True
    source = file.removeprefix(f"{study}_").removesuffix(".png")
    return (
        file == f"{study}_{source}.png" and SOURCE_PATTERN.fullmatch(source) is not None
    )


def _paper_files(paper: Path, study: str) -> tuple[list[Path], list[str]]:
    """The files of the paper folder that the study takes, and the names of the others."""
    if not paper.is_dir():
        return [], []
    taken: list[Path] = []
    left: list[str] = []
    for path in sorted(paper.iterdir(), key=lambda item: natural_key(item.name)):
        if path.is_file(follow_symlinks=False) and _is_paper_file(path.name, study):
            taken.append(path)
        else:
            left.append(path.name)
    return taken, left


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


def _errors(issues: Iterable[ValidationIssue]) -> str:
    """The error messages of issues, each with its file when it has one."""
    return "; ".join(
        f"{issue.source.file}: {issue.message}"
        if issue.source is not None and issue.source.file
        else issue.message
        for issue in issues
        if issue.severity == "error"
    )


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="")


def _remove_if_empty(folder: Path) -> None:
    try:
        folder.rmdir()
    except OSError:
        pass
