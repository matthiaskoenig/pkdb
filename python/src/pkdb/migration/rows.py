"""Table rows of a parsed format 1 study: the inverse of the format 2 reader."""

from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path

from pkdb.migration.metadata import single_line
from pkdb.migration.model import Decision, NotConverted
from pkdb.migration.sources import curator_source, observation_source
from pkdb.schemas.study import (
    CanonicalStudy,
    Group,
    Individual,
    Intervention,
    Measurement,
    Notes,
    Observation,
    Statistics,
)
from pkdb.studyformat.cells import NAME_PATTERN, NOT_REPORTED
from pkdb.studyformat.tables import TABLES, table_file
from pkdb.studyformat.text import format_number, render_tsv

Tables = dict[str, list[dict[str, str]]]
ErrorBars = Mapping[str, tuple[float, str]]
STATISTICS = tuple(name for name in Statistics.model_fields if name != "error_type")
PERCENT = frozenset({"cv", "gcv"})
# A list of names, such as the interventions of a row.
LIST = ","
# The administration times of an irregular schedule.
TIMES = ";"


def number(value: float | int | None) -> str:
    return "" if value is None else format_number(float(value))


def percent(value: float | None) -> str:
    """A fraction in percent, shifted in decimal so that 0.123 gives 12.3."""
    if value is None:
        return ""
    return format_number(float(Decimal(format_number(value)).scaleb(2)))


def comment(record: Notes) -> str:
    """Descriptions, then comments as `user: text`, on one line."""
    parts = [d.text for d in record.descriptions]
    parts += [f"{c.user}: {c.text}" if c.user else c.text for c in record.comments]
    return single_line(" / ".join(part for part in parts if part.strip()))


def text(value: object) -> str:
    return "" if value is None else single_line(value)


def time(record: Observation) -> str:
    """A time, the `;` list of an irregular dosing schedule, or NR."""
    if record.time_not_reported:
        return NOT_REPORTED
    if isinstance(record.time, list):
        return TIMES.join(number(value) for value in record.time)
    return number(record.time)


def statistics(record: Observation, error_bars: ErrorBars) -> dict[str, str]:
    stats = record.statistics
    cells = {
        name: percent(getattr(stats, name))
        if name in PERCENT
        else number(getattr(stats, name))
        for name in STATISTICS
    }
    cells["error_type"] = text(stats.error_type)
    if record.key in error_bars:
        bar, kind = error_bars[record.key]
        cells.update({"error_bar": number(bar), "error_type": kind, kind: ""})
    return cells


def observation(record: Observation, error_bars: ErrorBars) -> dict[str, str]:
    """The cells that every observation table shares."""
    return {
        "measurement": text(record.measurement_type),
        "calculation": text(record.calculation_type),
        "substance": text(record.substance),
        "tissue": text(record.tissue),
        "method": text(record.method),
        "choice": text(record.choice),
        "time": time(record),
        "time_unit": NOT_REPORTED
        if record.time_unit_not_reported
        else text(record.time_unit),
        "unit": text(record.unit),
        "comment": comment(record),
        **statistics(record, error_bars),
    }


def _name(name: str) -> str:
    if not NAME_PATTERN.fullmatch(name) or name != name.strip():
        raise NotConverted(
            "subject_name",
            f"Subject name {name!r} is no format 2 name. Format 2 names hold no "
            "comma, semicolon, tab or line break and no space at their ends.",
        )
    return name


def _subjects(
    study: CanonicalStudy, name: str, decisions: list[Decision]
) -> list[dict[str, str]]:
    rows, seen = [], set()
    subjects: list[Group | Individual] = [*study.groups, *study.individuals]
    for subject in subjects:
        if subject.name in seen:
            raise NotConverted(
                "subject_name", f"Two subjects have the name {subject.name}"
            )
        seen.add(subject.name)
        if isinstance(subject, Group):
            parent, count = subject.parent, subject.count
            if count == 1:
                decisions.append(Decision(kind="group_count_1", detail=subject.name))
        else:
            parent, count = subject.group, 1
        assert subject.source is not None
        rows.append(
            {
                "name": _name(subject.name),
                "parent": text(parent),
                "count": number(count),
                "source": curator_source(subject.source, subject.image, name),
                "comment": comment(subject),
            }
        )
    return rows


def _characteristic_image(
    record: Observation, subject: Group | Individual, name: str
) -> str | None:
    """The image file of a characteristic, else the image of its subject.

    `parse_bundle` names the image of a subject, intervention or output
    `<study>_<image>.png` but keeps the image of a characteristic as written,
    so it is named here the same way.
    """
    image = record.image
    if image and not Path(image).suffix:
        image = f"{name}_{image}.png"
    return image or subject.image


def _characteristica(
    study: CanonicalStudy, name: str, error_bars: ErrorBars
) -> list[dict[str, str]]:
    rows = []
    subjects: list[Group | Individual] = [*study.groups, *study.individuals]
    for subject in subjects:
        for record in subject.characteristica:
            assert record.source is not None
            image = _characteristic_image(record, subject, name)
            rows.append(
                {
                    **observation(record, error_bars),
                    "subjects": subject.name,
                    "source": curator_source(record.source, image, name),
                }
            )
    return rows


def _schedule(record: Intervention) -> Decision | None:
    """A decision to check a dosing schedule or a list of administration times."""
    listed = isinstance(record.time, list)
    if record.interval is None and record.doses is None and not listed:
        return None
    parts = [f"time {time(record)}"]
    if record.interval is not None:
        parts.append(f"interval {number(record.interval)}")
    if record.doses is not None:
        parts.append(f"doses {number(record.doses)}")
    return Decision(kind="schedule", detail=f"{record.name}: {', '.join(parts)}")


def _interventions(
    study: CanonicalStudy,
    name: str,
    error_bars: ErrorBars,
    decisions: list[Decision],
) -> list[dict[str, str]]:
    rows = []
    for record in study.interventions:
        if (decision := _schedule(record)) is not None:
            decisions.append(decision)
        assert record.source is not None
        rows.append(
            {
                **observation(record, error_bars),
                "name": record.name,
                "subjects": text(record.subject),
                "route": text(record.route),
                "form": text(record.form),
                "application": text(record.application),
                "time_end": number(record.time_end),
                "interval": number(record.interval),
                "doses": number(record.doses),
                "source": curator_source(record.source, record.image, name),
            }
        )
    return rows


def _measurement(
    record: Measurement, name: str, error_bars: ErrorBars
) -> tuple[str, dict[str, str]]:
    """The source and the row of an output or a timecourse point."""
    assert record.source is not None
    source = observation_source(record.source, record.image, name)
    return source, {
        **observation(record, error_bars),
        "subjects": text(record.group or record.individual),
        "interventions": LIST.join(record.interventions),
        "source": source,
    }


def study_tables(
    study: CanonicalStudy, name: str, error_bars: ErrorBars = {}
) -> tuple[Tables, list[Decision]]:
    """The format 2 tables of a parsed format 1 study and the decisions to check."""
    decisions: list[Decision] = []
    tables: Tables = {
        "subjects.tsv": _subjects(study, name, decisions),
        "characteristica.tsv": _characteristica(study, name, error_bars),
        "interventions.tsv": _interventions(study, name, error_bars, decisions),
    }
    for record in study.measurements:
        if record.output_type == "timecourse":
            source, row = _measurement(record, name, error_bars)
            tables.setdefault(table_file("timecourses", source), []).append(
                {**row, "label": text(record.label)}
            )
        elif record.output_type == "output":
            source, row = _measurement(record, name, error_bars)
            tables.setdefault(table_file("outputs", source), []).append(row)
    return {file: rows for file, rows in tables.items() if rows}, decisions


def render(tables: Tables) -> dict[str, str]:
    """TSV text of each table, columns in template order."""
    rendered = {}
    for file, rows in tables.items():
        kind = file.removesuffix(".tsv").partition("_")[0]
        names = TABLES[kind].names
        for row in rows:
            if unknown := row.keys() - set(names):
                raise ValueError(f"{file} has no columns {sorted(unknown)}")
        rendered[file] = render_tsv(
            names, [tuple(row.get(column, "") for column in names) for row in rows]
        )
    return rendered


def used_sources(tables: Tables) -> set[str]:
    """The sources that the rows name, whose images the converted study needs."""
    return {
        row["source"] for rows in tables.values() for row in rows if row.get("source")
    }
