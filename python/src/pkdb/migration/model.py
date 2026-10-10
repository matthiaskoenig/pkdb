"""Results of a migration run, shared by the converter, the gate, the runner and the report."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Outcome = Literal["identical", "intended", "mismatch", "invalid_v1", "not_converted"]


class NotConverted(Exception):
    """The converter cannot write a study; `code` names the reason in the report."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DroppedRow(Model):
    """A format 1 row without any value that the converter dropped, by its place.

    `table` is the format 2 table the row would be in; `file`, `sheet` and
    `row` locate it in format 1, or `path` in study.json.
    """

    table: str
    file: str
    sheet: str | None = None
    row: int | None = None
    path: str | None = None
    label: str | None = None
    subject: str | None = None
    measurement: str
    substance: str | None = None
    tissue: str | None = None
    comment: str | None = None

    def place(self) -> str:
        """Such as `Example.xlsx Tab2 row 4`, or `study.json groupset.groups.0`."""
        where = f"row {self.row}" if self.row is not None else self.path
        return " ".join(part for part in (self.file, self.sheet, where) if part)


class Decision(Model):
    """Something a person should check by hand, such as a converted dosing schedule.

    A dropped row without any value (`valueless_row`) also has its place, so
    that the Markdown report can list the rows of a sheet as ranges.
    """

    kind: str
    detail: str
    dropped: DroppedRow | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


class Change(Model):
    """An intended change of the conversion, counted per kind with a few examples."""

    kind: str
    count: int
    examples: list[str] = Field(default_factory=list)


class Difference(Model):
    """A difference between the v1 study (A) and the converted study (B)."""

    path: str
    a: str
    b: str


class StudyResult(Model):
    study: str
    outcome: Outcome
    reason: str | None = None
    changes: list[Change] = Field(default_factory=list)
    differences: list[Difference] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    written: bool = False
    # The SHA-256 hash of the vocabulary that converted and judged the study.
    vocabulary: str | None = None


class PaperMove(Model):
    """A folder without study.json moved to papers/."""

    source: str
    target: str
    files: list[str]
    workbook: bool


class VocabularyUsed(Model):
    """The vocabulary that the converter and the gate used, which decides conversions."""

    version: str
    hash: str


class RegistryFindings(Model):
    double_identifiers: dict[str, list[str]] = Field(default_factory=dict)
    missing_paths: list[str] = Field(default_factory=list)
    deleted: bool = False


class MigrationReport(Model):
    dry_run: bool
    vocabulary: VocabularyUsed | None = None
    # The run stopped before it finished, for example by Ctrl-C or a failed swap.
    interrupted: bool = False
    warnings: list[str] = Field(default_factory=list)
    studies: list[StudyResult] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)
    papers: list[PaperMove] = Field(default_factory=list)
    removed_empty: list[str] = Field(default_factory=list)
    recovered: list[str] = Field(default_factory=list)
    registry: RegistryFindings = Field(default_factory=RegistryFindings)
