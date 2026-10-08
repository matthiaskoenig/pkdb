"""What a review target selects in a loaded study: the lines of its rows and its digitized series."""

from dataclasses import dataclass

from pkdb.schemas.review import ReviewTarget
from pkdb.studyformat.digitize import SERIES_COLUMNS
from pkdb.studyformat.load import LoadedStudy
from pkdb.studyformat.sources import source_kind


@dataclass(frozen=True)
class DigitizedSeries:
    """A series of a figure with a WebPlotDigitizer project: the figure and the series name."""

    source: str
    series: str


@dataclass(frozen=True)
class TargetMatch:
    """What a review target selects.

    `lines` are the TSV lines of the rows that its row filter matches in a data table, in file
    order; None for a target without a row filter or of a file that is no data table. `series` is
    the series that its filter names in a timecourse or scatter table of a figure with a
    WebPlotDigitizer project, else None.
    """

    lines: tuple[int, ...] | None
    series: DigitizedSeries | None


def match_target(study: LoadedStudy, target: ReviewTarget | None) -> TargetMatch:
    """The rows and the digitized series of a review target, as `pkdb review show` counts them."""
    if target is None or target.file is None:
        return TargetMatch(None, None)
    table = study.table(target.file)
    if table is None:
        return TargetMatch(None, None)
    lines = tuple(sorted(table.matching_lines(target.rows))) if target.rows else None
    column = SERIES_COLUMNS.get(table.kind)
    name = target.rows.get(column) if column else None
    series = None
    if (
        name
        and table.source is not None
        and source_kind(table.source) == "figure"
        and study.digitization(table.source) is not None
    ):
        series = DigitizedSeries(table.source, name)
    return TargetMatch(lines, series)
