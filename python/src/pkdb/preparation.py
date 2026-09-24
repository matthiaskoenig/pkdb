"""Prepare unchanged study folders using the same engine as the server."""

import hashlib
import shutil
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType

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


def study_folders(path: str | Path) -> list[Path]:
    root = Path(path)
    if not root.is_dir():
        raise ValueError("Study path must be a directory")
    if (root / "study.json").is_file():
        return [root]
    folders = sorted(file.parent for file in root.rglob("study.json"))
    if not folders:
        raise ValueError("No study.json files found")
    return folders


def source_hashes(folder: Path) -> dict[str, str]:
    result = {}
    for path in sorted(folder.rglob("*")):
        if path.is_symlink():
            fail(
                "symlink",
                "Symlinks are not accepted",
                SourceLocation(file=str(path.relative_to(folder))),
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
        root = Path(temporary) / folder.name
        root.mkdir()
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
class PreparedBundle:
    path: Path
    prepared: PreparedStudy
    vocabulary: Vocabulary
    file_hashes: Mapping[str, str]
    max_rows: int

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
    def source(self):
        with source_snapshot(self.path) as (root, hashes):
            if hashes != self.file_hashes:
                raise SourceChangedError(
                    "Study files changed after validation; prepare the folder again"
                )
            yield load_folder(root)


def prepare(
    folder: str | Path,
    *,
    vocabulary: Vocabulary | None = None,
    max_rows: int = 1_000_000,
    max_files: int = 256,
    progress: ProgressCallback | None = None,
) -> PreparedBundle:
    emit(progress, "read")
    path = Path(folder).resolve(strict=True)
    vocabulary = vocabulary if vocabulary is not None else bundled_vocabulary()
    with source_snapshot(path) as (root, hashes):
        bundle: SourceBundle = load_folder(root)
        if len(bundle.files) > max_files:
            fail("file_limit", "Too many source files")
        emit(progress, "parse")
        canonical = parse_bundle(bundle, max_rows=max_rows)
        emit(progress, "validate")
        prepared = prepare_study(canonical, vocabulary)
    return PreparedBundle(path, prepared, vocabulary, hashes, max_rows)
