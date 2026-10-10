"""Prepare unchanged study folders using the same engine as the server."""

import hashlib
import json
import shutil
from collections.abc import Generator, Mapping
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from typing import BinaryIO

from pkdb.cache import bundled_vocabulary
from pkdb.domain.validation import prepare_study
from pkdb.domain.vocabulary import Vocabulary, vocabulary_hash
from pkdb.errors import SourceChangedError
from pkdb.importers.folder import load_folder, parse_bundle
from pkdb.progress import ProgressCallback, emit
from pkdb.schemas.prepared import PreparedStudy
from pkdb.schemas.source import SourceBundle, SourceLocation
from pkdb.schemas.study import CanonicalStudy
from pkdb.schemas.validation import ValidationReport, fail
from pkdb.source_files import below_hidden_folder, ignored_source
from pkdb.studyformat.load import load_study
from pkdb.studyformat.tables import REFERENCE_JSON, STUDY_JSON
from pkdb.studyformat.validation import (
    is_v2_folder,
    prepare_folder,
    study_path,
)

type Part = tuple[str, tuple[None, bytes] | tuple[str, bytes | BinaryIO, str]]

# The limits of a prepared study: data rows of all tables, and files besides
# study.json and reference.json. A server may allow less; the upload checks its limits.
MAX_ROWS = 1_000_000
MAX_FILES = 256


def study_folders(path: str | Path) -> list[Path]:
    """The study folder `path`, or the folders with a study.json below it.

    Folders below a hidden folder are skipped, such as `.git` or the build
    folder `.<name>.new/<name>` that an interrupted `pkdb new` leaves.
    """
    root = Path(path)
    if not root.is_dir():
        raise ValueError("Study path must be a directory")
    if (root / "study.json").is_file():
        return [root]
    # Sorted by the text of each part, since Windows paths sort without regard
    # to case; part by part keeps `caffeine/B` before `caffeine-citrate/A`.
    folders = sorted(
        (
            file.parent
            for file in root.rglob("study.json")
            if not below_hidden_folder(file.relative_to(root))
        ),
        key=lambda folder: folder.as_posix().split("/"),
    )
    if not folders:
        raise ValueError("No study.json files found")
    return folders


def source_hashes(folder: Path) -> dict[str, str]:
    result = {}
    for path in sorted(folder.rglob("*")):
        if ignored_source(path.relative_to(folder)):
            continue
        if path.is_symlink():
            fail(
                "symlink",
                "Symlinks are not accepted",
                SourceLocation(file=path.relative_to(folder).as_posix()),
            )
        if path.is_file():
            with path.open("rb") as handle:
                result[path.relative_to(folder).as_posix()] = hashlib.file_digest(
                    handle, "sha256"
                ).hexdigest()
    return result


@contextmanager
def source_snapshot(folder: Path):
    """Parse and upload the same private copy, never changing the curator's files."""
    folder = folder.resolve(strict=True)
    before = source_hashes(folder)
    with TemporaryDirectory(prefix="pkdb-prepare-") as temporary:
        # Study format 2 identifies a study by its substance folder and its name.
        root = Path(temporary) / folder.parent.name / folder.name
        root.mkdir(parents=True)
        for name in before:
            source = folder / name
            if source.is_symlink():
                raise SourceChangedError(
                    "Source changed while preparing; prepare again"
                )
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        if source_hashes(root) != before or source_hashes(folder) != before:
            raise SourceChangedError("Source changed while preparing; prepare again")
        yield root, before


@dataclass(frozen=True)
class UploadSource:
    """The parts of a study upload, read from a private snapshot of its folder.

    `study` and `reference` are the content of the study and reference parts:
    the exact bytes of study.json and reference.json in study format 2, sent as
    files so the server checks those bytes, and the parsed objects as JSON
    text fields in study format 1. `files` maps the attachment names to their
    files in the snapshot at `root`. `prepared` is the snapshot prepared again,
    so the upload sends what was checked.
    """

    root: Path
    prepared: PreparedStudy
    study: bytes
    reference: bytes
    files: Mapping[str, Path]
    study_format: int = 1

    @property
    def upload_path(self) -> str:
        """The API path that creates or replaces the study."""
        return f"/api/v2/studies/{study_path(self.prepared.study.sid)}"

    @property
    def validation_path(self) -> str:
        """The API path that validates the study without saving it.

        Study format 2 names the study in the path, format 1 in study.json.
        """
        if self.study_format == 2:
            return f"{self.upload_path}/validate"
        return "/api/v2/studies/validate"

    def check_rows(self, max_rows: int) -> None:
        """Fail with `row_limit` when the tables have more rows than `max_rows`."""
        if self.study_format == 2:
            load_study(self.root, max_rows=max_rows)
        else:
            parse_bundle(load_folder(self.root), max_rows=max_rows)

    def parts(self, stack: ExitStack) -> list[Part]:
        """The multipart parts: study, reference and a `files` part per file.

        The files stay open until `stack` closes.
        """
        parts: list[Part] = (
            [
                ("study", (STUDY_JSON, self.study, "application/json")),
                ("reference", (REFERENCE_JSON, self.reference, "application/json")),
            ]
            if self.study_format == 2
            else [("study", (None, self.study)), ("reference", (None, self.reference))]
        )
        parts.extend(
            (
                "files",
                (
                    name,
                    stack.enter_context(path.open("rb")),
                    "application/octet-stream",
                ),
            )
            for name, path in self.files.items()
        )
        return parts


def read_upload(
    root: Path,
    vocabulary: Vocabulary,
    *,
    study_format: int,
    max_rows: int,
    progress: ProgressCallback | None = None,
) -> UploadSource:
    """Prepare a snapshot of a study folder and read the parts of its upload.

    Study format 2 sends the exact bytes of study.json and reference.json and
    every other file of the study; the server reads them as the client does.
    """
    if study_format == 2:
        emit(progress, "validate")
        prepared = prepare_folder(root, vocabulary, max_rows=max_rows)
        files = {item.name: root / item.name for item in prepared.study.attachments}
        return UploadSource(
            root,
            prepared,
            (root / STUDY_JSON).read_bytes(),
            (root / REFERENCE_JSON).read_bytes(),
            MappingProxyType(files),
            study_format=2,
        )
    bundle = load_folder(root)
    emit(progress, "parse")
    canonical = parse_bundle(bundle, max_rows=max_rows)
    emit(progress, "validate")
    return UploadSource(
        root,
        prepare_study(canonical, vocabulary),
        json.dumps(bundle.study).encode(),
        json.dumps(bundle.reference).encode(),
        MappingProxyType(dict(bundle.files)),
    )


@dataclass(frozen=True)
class PreparedBundle:
    path: Path
    prepared: PreparedStudy
    vocabulary: Vocabulary
    file_hashes: Mapping[str, str]
    max_rows: int
    study_format: int = 1

    def __post_init__(self):
        object.__setattr__(
            self, "file_hashes", MappingProxyType(dict(self.file_hashes))
        )

    @property
    def study(self) -> CanonicalStudy:
        return self.prepared.study

    @property
    def report(self) -> ValidationReport:
        return self.prepared.report

    @property
    def vocabulary_hash(self) -> str:
        return vocabulary_hash(self.vocabulary)

    def model_dump(self) -> dict:
        return {
            **self.prepared.model_dump(mode="json"),
            "vocabulary_hash": self.vocabulary_hash,
            "file_hashes": dict(self.file_hashes),
        }

    @contextmanager
    def source(self) -> Generator[UploadSource]:
        """The upload of a private snapshot equal to the prepared folder.

        The snapshot is prepared again with the vocabulary of the preparation,
        so a changed folder or a changed prepared study never reaches a server.
        """
        with source_snapshot(self.path) as (root, hashes):
            if hashes != self.file_hashes:
                raise SourceChangedError(
                    "Study files changed after validation; prepare the folder again"
                )
            yield read_upload(
                root,
                self.vocabulary,
                study_format=self.study_format,
                max_rows=self.max_rows,
            )


def prepare(
    folder: str | Path,
    *,
    vocabulary: Vocabulary | None = None,
    max_rows: int = MAX_ROWS,
    max_files: int = MAX_FILES,
    progress: ProgressCallback | None = None,
) -> PreparedBundle:
    emit(progress, "read")
    path = Path(folder).resolve(strict=True)
    vocabulary = vocabulary if vocabulary is not None else bundled_vocabulary()
    if is_v2_folder(path):
        with source_snapshot(path) as (root, hashes):
            emit(progress, "validate")
            prepared = prepare_folder(
                root, vocabulary, max_rows=max_rows, max_files=max_files
            )
        return PreparedBundle(
            path, prepared, vocabulary, hashes, max_rows, study_format=2
        )
    with source_snapshot(path) as (root, hashes):
        bundle: SourceBundle = load_folder(root)
        if len(bundle.files) > max_files:
            fail("file_limit", "Too many source files")
        emit(progress, "parse")
        canonical = parse_bundle(bundle, max_rows=max_rows)
        emit(progress, "validate")
        prepared = prepare_study(canonical, vocabulary)
    return PreparedBundle(path, prepared, vocabulary, hashes, max_rows)
