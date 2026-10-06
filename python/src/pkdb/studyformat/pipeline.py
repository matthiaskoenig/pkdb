"""The sync-then-format step that `pkdb upload` and the curation app share."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pkdb.domain.vocabulary import Vocabulary
from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.formatter import FileChange, FormatResult, format_folder
from pkdb.studyformat.sync import SyncResult, sync_study
from pkdb.studyformat.workbook.base import workbook_path

Stopped = Literal["sync", "saved_again", "format"]


@dataclass(frozen=True)
class PipelineResult:
    """Outcome of syncing the workbook and formatting the tables of a folder.

    `syncs` are the syncs that ran, none without a workbook, two when the
    workbook was saved during the first. `formatted` is None when a sync
    stopped the pipeline. `stopped` names the stage that stopped it: `sync` for
    a sync with errors, `saved_again` when the workbook was saved during both
    syncs, `format` for formatting with errors.
    """

    syncs: tuple[SyncResult, ...] = ()
    formatted: FormatResult | None = None
    stopped: Stopped | None = None

    @property
    def ok(self) -> bool:
        return self.stopped is None

    @property
    def changes(self) -> tuple[FileChange, ...]:
        """The sync changes, the last change per file, then the format changes."""
        synced = {change.file: change for sync in self.syncs for change in sync.changes}
        formatted = self.formatted.changes if self.formatted else []
        return (*synced.values(), *formatted)

    @property
    def issues(self) -> tuple[ValidationIssue, ...]:
        """The issues of the stage that stopped, else the warnings of the last sync and of formatting."""
        last = self.syncs[-1].issues if self.syncs else ()
        formatted = tuple(self.formatted.issues) if self.formatted else ()
        match self.stopped:
            case "sync" | "saved_again":
                return last
            case "format":
                return formatted
            case None:
                return (*last, *formatted)


def sync_and_format(
    folder: Path,
    vocabulary: Vocabulary,
    *,
    max_rows: int | None = None,
    on_stage: Callable[[str], None] | None = None,
) -> PipelineResult:
    """Sync the workbook into the tables when there is one, then format the tables.

    A workbook saved during the sync is synced once more. A folder without
    workbook only gets formatted, and no workbook is created. `on_stage` is
    called with `sync` before the sync stage and `format` before formatting.
    """
    if on_stage:
        on_stage("sync")
    syncs: list[SyncResult] = []
    if workbook_path(folder).exists():
        syncs.append(sync_study(folder, vocabulary, max_rows=max_rows))
        if syncs[-1].ok and syncs[-1].workbook_action == "sync_again":
            # The save is not in the tables yet; this sync merges it.
            syncs.append(sync_study(folder, vocabulary, max_rows=max_rows))
        if not syncs[-1].ok:
            return PipelineResult(tuple(syncs), stopped="sync")
        if syncs[-1].workbook_action == "sync_again":
            return PipelineResult(tuple(syncs), stopped="saved_again")
    if on_stage:
        on_stage("format")
    formatted = format_folder(folder)
    return PipelineResult(tuple(syncs), formatted, None if formatted.ok else "format")
