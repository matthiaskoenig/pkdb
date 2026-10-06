"""Checked edits of `study.json`, shared by `pkdb study` and the curation app."""

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from pkdb.references import ReferenceError, sync_reference
from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.issues import make_issue
from pkdb.studyformat.jsonio import JsonFileError, load_json
from pkdb.studyformat.load import validation_issues
from pkdb.studyformat.models import StudyMetadata, canonical_study_json
from pkdb.studyformat.revision import folder_lock, read_revision, write_checked
from pkdb.studyformat.tables import STUDY_JSON

CODE = "invalid_study_json"


class MetadataError(ValueError):
    """study.json or the new metadata is invalid; nothing was written."""

    def __init__(self, issues: list[ValidationIssue]):
        super().__init__("; ".join(issue.message for issue in issues))
        self.issues = issues


@dataclass(frozen=True)
class MetadataDocument:
    metadata: StudyMetadata
    revision: str


@dataclass(frozen=True)
class MetadataWrite:
    revision: str
    reference: str | None = None
    reference_error: str | None = None


def _validated(data: object) -> StudyMetadata:
    try:
        return StudyMetadata.model_validate(data)
    except ValidationError as error:
        raise MetadataError(validation_issues(error, STUDY_JSON, CODE)) from None


def read_metadata(folder: Path) -> MetadataDocument:
    data, revision = read_revision(Path(folder) / STUDY_JSON)
    if data is None:
        raise MetadataError(
            [make_issue("missing_file", f"{STUDY_JSON} is required", file=STUDY_JSON)]
        )
    try:
        value = load_json(data)
    except JsonFileError as error:
        raise MetadataError(
            [make_issue(error.code, str(error), file=STUDY_JSON)]
        ) from None
    return MetadataDocument(_validated(value), revision)


def write_metadata(
    folder: Path, metadata: StudyMetadata, revision: str | None, *, resolver=None
) -> MetadataWrite:
    """Write study.json in canonical form when it is still at `revision`.

    A changed PubMed ID or DOI refreshes reference.json with `resolver`;
    without one, validation reports the mismatch.
    """
    folder = Path(folder)
    metadata = _validated(metadata.model_dump(mode="json"))
    with folder_lock(folder):
        try:
            before = read_metadata(folder).metadata.reference
        except MetadataError:
            before = None
        new_revision = write_checked(
            folder / STUDY_JSON, canonical_study_json(metadata), revision
        )
    reference = None
    if resolver is not None and metadata.reference != before:
        try:
            reference = sync_reference(folder, resolver)
        except (ReferenceError, OSError) as error:
            # study.json is written; validation reports the reference mismatch.
            return MetadataWrite(new_revision, None, reference_error=str(error))
    return MetadataWrite(new_revision, reference)


def merge_patch(target: object, patch: object) -> object:
    """Apply a JSON merge patch (RFC 7386)."""
    if not isinstance(patch, dict):
        return patch
    result = dict(target) if isinstance(target, dict) else {}
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = merge_patch(result.get(key), value)
    return result


def patch_metadata(
    folder: Path, patch: dict, revision: str | None, *, resolver=None
) -> MetadataWrite:
    """Apply a merge patch to study.json and write it.

    `revision` None patches the current content; otherwise `write_checked`
    raises a RevisionConflict when the file changed since that revision.
    """
    document = read_metadata(folder)
    data = merge_patch(
        document.metadata.model_dump(mode="json", exclude_none=True), patch
    )
    return write_metadata(
        folder,
        _validated(data),
        document.revision if revision is None else revision,
        resolver=resolver,
    )
