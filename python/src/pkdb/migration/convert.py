"""Convert one format 1 study folder into a format 2 work folder."""

import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import openpyxl
from pydantic import ValidationError

from pkdb.importers.folder import load_folder, parse_bundle
from pkdb.migration.formulas import error_bars
from pkdb.migration.metadata import review, study_metadata
from pkdb.migration.model import Decision, NotConverted
from pkdb.migration.registry import Registry
from pkdb.migration.rows import render, study_tables, used_sources
from pkdb.migration.sources import IMAGE_SUFFIXES, copy_images, image_sources, sheet_of
from pkdb.references import ReferenceError, ReferenceResolver, sync_reference
from pkdb.schemas.study import CanonicalStudy, DataRecord, Observation, Subject
from pkdb.schemas.validation import StudyValidationError, ValidationIssue
from pkdb.source_files import ignored_source
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.jsonio import dump_json
from pkdb.studyformat.models import canonical_review_json, canonical_study_json
from pkdb.studyformat.tables import REFERENCE_JSON, REVIEW_JSON, STUDY_JSON, TEXT_SOURCE

DATA_SUFFIXES = (".tsv", ".csv", ".json", ".xls", ".xlsx")
# Fields of reference.json that format 1 allows as numbers and format 2 keeps as text.
TEXT_IDENTIFIERS = ("sid", "pmid")
# At most this many issues name the reason of a study that is not converted.
SHOWN_ISSUES = 3


@dataclass(frozen=True)
class Conversion:
    folder: Path
    decisions: list[Decision]


def is_v1_file(name: str, study: str) -> bool:
    """Files that a format 2 study does not keep: v1 tables, workbooks and other data files.

    These are the v1 study.json, `<study>.xlsx`, `.xls` files, the hidden
    `.<study>_<sheet>.tsv` files, other TSV and CSV files and JSON files other
    than reference.json.
    """
    return name != REFERENCE_JSON and Path(name).suffix.lower() in DATA_SUFFIXES


def _quiet(name: str, study: str) -> bool:
    """Dropped files that need no decision: the v1 study.json, workbook and hidden TSVs."""
    return name in (STUDY_JSON, f"{study}.xlsx") or (
        name.startswith(f".{study}_") and name.endswith(".tsv")
    )


def _sheets(v1: Path, study: str) -> set[str]:
    """The sheets of the workbook and of the hidden TSV files."""
    hidden = f".{study}_"
    sheets = {
        path.name.removeprefix(hidden).removesuffix(".tsv")
        for path in v1.iterdir()
        if path.name.startswith(hidden) and path.name.endswith(".tsv")
    }
    workbook = v1 / f"{study}.xlsx"
    if workbook.exists():
        book = openpyxl.load_workbook(workbook, read_only=True)
        try:
            sheets.update(book.sheetnames)
        finally:
            book.close()
    return sheets


def _all_records(study: CanonicalStudy) -> list[Observation | Subject | DataRecord]:
    """Every entity of the study that comes from a row of a sheet or of study.json."""
    records: list[Observation | Subject | DataRecord] = []
    for subject in [*study.groups, *study.individuals]:
        records.append(subject)
        records.extend(subject.characteristica)
    records.extend(study.interventions)
    records.extend(study.measurements)
    records.extend(study.scatters)
    return records


def _read_sheets(study: CanonicalStudy, name: str) -> set[str]:
    """The sheets that at least one entity of the study came from."""
    sheets = (
        sheet_of(record.source, name)
        for record in _all_records(study)
        if record.source is not None
    )
    return {sheet for sheet in sheets if sheet is not None}


def _issues(issues: Iterable[ValidationIssue]) -> str:
    """The first error messages, each with its file when it has one."""
    texts = [
        f"{issue.source.file}: {issue.message}"
        if issue.source is not None
        else issue.message
        for issue in issues
        if issue.severity == "error"
    ]
    return "; ".join(texts[:SHOWN_ISSUES])


def _fields(error: ValidationError) -> str:
    """The first invalid fields of a pydantic error, each with its message."""
    return "; ".join(
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
        for item in error.errors()[:SHOWN_ISSUES]
    )


def _reference(reference: dict) -> dict:
    """reference.json with its sid and PubMed ID as text, as the v1 importer reads them."""
    return {
        key: str(value) if key in TEXT_IDENTIFIERS and type(value) is int else value
        for key, value in reference.items()
    }


def _attachments(v1: Path, target: Path, name: str, images: set[str]) -> list[Decision]:
    """Copy every file and folder that format 2 keeps; list the dropped v1 files."""
    decisions = []
    for path in sorted(v1.iterdir()):
        if ignored_source(Path(path.name)) or path.name in (STUDY_JSON, REFERENCE_JSON):
            continue
        if path.is_dir():
            # Format 2 ignores hidden folders and reports others; neither is lost.
            shutil.copytree(path, target / path.name)
            continue
        if path.stem in images and path.suffix.lower() in IMAGE_SUFFIXES:
            continue  # written by copy_images
        if is_v1_file(path.name, name):
            if not _quiet(path.name, name):
                decisions.append(Decision(kind="removed_file", detail=path.name))
            continue
        shutil.copyfile(path, target / path.name)
    return decisions


def convert_study(
    v1: Path,
    target: Path,
    *,
    registry: Registry,
    approver: str | None,
    resolver: ReferenceResolver,
) -> Conversion:
    """Write the format 2 study of the v1 folder into `target`, an empty or missing folder.

    Raises NotConverted when format 2 cannot hold the study or a step fails.
    """
    name = v1.name
    if target.name != name:
        raise ValueError(f"The work folder {target} must be named {name}")
    try:
        bundle = load_folder(v1)
        study = parse_bundle(bundle)
    except StudyValidationError as error:
        raise NotConverted("unreadable", _issues(error.report.issues)) from error
    workbook = v1 / f"{name}.xlsx"
    bars = error_bars(workbook, study) if workbook.exists() else {}
    tables, decisions = study_tables(study, name, bars, images=image_sources(v1, name))
    if "subjects.tsv" not in tables:
        raise NotConverted("no_subjects", "The study has no groups or individuals")
    release = registry.release(f"{v1.parent.name}/{name}")
    try:
        metadata, metadata_decisions = study_metadata(
            bundle.study, bundle.reference, release, creator_fallback=approver or "pkdb"
        )
        status = review(release, approver)
    except ValidationError as error:
        raise NotConverted("metadata", _fields(error)) from error
    decisions += metadata_decisions
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        raise FileExistsError(f"The work folder {target} is not empty")
    for file, text in render(tables).items():
        (target / file).write_text(text, encoding="utf-8", newline="")
    (target / STUDY_JSON).write_text(
        canonical_study_json(metadata), encoding="utf-8", newline=""
    )
    (target / REVIEW_JSON).write_text(
        canonical_review_json(status), encoding="utf-8", newline=""
    )
    # load_folder requires reference.json, so a readable study always has one.
    (target / REFERENCE_JSON).write_text(
        dump_json(_reference(bundle.reference)), encoding="utf-8", newline=""
    )
    try:
        sync_reference(target, resolver)
    except ReferenceError as error:
        raise NotConverted("reference", str(error)) from error
    sources = used_sources(tables) - {TEXT_SOURCE}
    decisions += copy_images(v1, target, name, sources)
    images = {f"{name}_{source}" for source in sources}
    decisions += _attachments(v1, target, name, images)
    for sheet in sorted(_sheets(v1, name) - _read_sheets(study, name)):
        decisions.append(Decision(kind="unreferenced_sheet", detail=sheet))
    result = format_folder(target)
    if not result.ok:
        raise NotConverted("format", _issues(result.issues))
    return Conversion(target, decisions)
