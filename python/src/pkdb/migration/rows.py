"""Table rows of a parsed format 1 study: the inverse of the format 2 reader."""

from collections import Counter
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path

from pkdb.domain.datasets import STATISTICS_FIELDS
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
from pkdb.studyformat.tables import TABLES, TEXT_SOURCE, table_file
from pkdb.studyformat.text import format_number, render_tsv

Tables = dict[str, list[dict[str, str]]]
ErrorBars = Mapping[str, tuple[float, str]]
STATISTICS = tuple(name for name in Statistics.model_fields if name != "error_type")
PERCENT = frozenset({"cv", "gcv"})
# A list of names, such as the interventions of a row.
LIST = ","
# The administration times of an irregular schedule.
TIMES = ";"
GEOMETRIC_MEAN = "geometric mean"


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


def _geometric(
    record: Observation, row: dict[str, str], decisions: list[Decision]
) -> dict[str, str]:
    """A geometric mean that format 1 wrote as `mean` moves to `gmean`."""
    stats = record.statistics
    if (
        record.calculation_type != GEOMETRIC_MEAN
        or stats.gmean is not None
        or stats.mean is None
    ):
        return row
    if any(getattr(stats, name) is not None for name in ("sd", "se", "cv")):
        decisions.append(
            Decision(
                kind="geometric_spread",
                detail=f"{record.key}: geometric mean with sd, se or cv",
            )
        )
    # Format 2 retired the calculation `geometric mean`: gmean says it.
    return {**row, "gmean": row["mean"], "mean": "", "calculation": ""}


def _name(name: str) -> str:
    if not NAME_PATTERN.fullmatch(name) or name != name.strip():
        raise NotConverted(
            "subject_name",
            f"Subject name {name!r} is no format 2 name. Format 2 names hold no "
            "comma, semicolon, tab or line break and no space at their ends.",
        )
    return name


def _subjects(
    study: CanonicalStudy, name: str, images: frozenset[str], decisions: list[Decision]
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
                "source": curator_source(subject.source, subject.image, name, images),
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
    study: CanonicalStudy,
    name: str,
    images: frozenset[str],
    error_bars: ErrorBars,
    decisions: list[Decision],
) -> list[dict[str, str]]:
    rows = []
    subjects: list[Group | Individual] = [*study.groups, *study.individuals]
    for subject in subjects:
        for record in subject.characteristica:
            assert record.source is not None
            image = _characteristic_image(record, subject, name)
            row = {
                **observation(record, error_bars),
                "subjects": subject.name,
                "source": curator_source(record.source, image, name, images),
            }
            rows.append(_geometric(record, row, decisions))
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
    images: frozenset[str],
    error_bars: ErrorBars,
    decisions: list[Decision],
) -> list[dict[str, str]]:
    rows = []
    for record in study.interventions:
        if (decision := _schedule(record)) is not None:
            decisions.append(decision)
        assert record.source is not None
        row = {
            **observation(record, error_bars),
            "name": record.name,
            "subjects": text(record.subject),
            "route": text(record.route),
            "form": text(record.form),
            "application": text(record.application),
            "time_end": number(record.time_end),
            "interval": number(record.interval),
            "doses": number(record.doses),
            "source": curator_source(record.source, record.image, name, images),
        }
        rows.append(_geometric(record, row, decisions))
    return rows


def _measurement(
    record: Measurement, name: str, error_bars: ErrorBars, images: frozenset[str]
) -> tuple[str, dict[str, str]]:
    """The source and the row of an output or a timecourse point."""
    assert record.source is not None
    source = observation_source(record.source, record.image, name, images)
    return source, {
        **observation(record, error_bars),
        "subjects": text(record.group or record.individual),
        "interventions": LIST.join(record.interventions),
        "source": source,
    }


def _by_subject(scatter: str, records: list[Measurement]) -> dict[str, Measurement]:
    """The points of one scatter axis by their subject, which pairs x and y."""
    points: dict[str, Measurement] = {}
    for record in records:
        subject = record.group or record.individual
        if subject is None:
            raise NotConverted(
                "scatter_pairs", f"Scatter {scatter} has a point without a subject."
            )
        if subject in points:
            raise NotConverted(
                "scatter_pairs",
                f"Scatter {scatter} has more than one point of subject {subject}; "
                "format 2 pairs x and y by subject.",
            )
        points[subject] = record
    return points


def _shared(record: Measurement, field: str) -> object:
    """A field by which format 1 pairs the points of a scatter."""
    values = record.statistics if field in STATISTICS_FIELDS else record
    return getattr(values, field, None)


def _scatter_pairs(
    scatter: str,
    labels: list[str],
    shared: list[str],
    by_label: Mapping[str, list[Measurement]],
) -> list[tuple[str, Measurement, Measurement]]:
    """Subject, x and y output of each point, paired by subject as format 2 pairs them.

    Format 1 pairs the outputs by the `shared` fields, so these must agree too.
    """
    xs, ys = (_by_subject(scatter, by_label.get(label, [])) for label in labels)
    if set(xs) != set(ys) or any(
        _shared(xs[subject], field) != _shared(ys[subject], field)
        for subject in xs
        for field in shared
    ):
        raise NotConverted(
            "scatter_pairs",
            f"Scatter {scatter}: the x and y outputs do not pair by subject.",
        )
    return [(subject, x, ys[subject]) for subject, x in xs.items()]


def _scatter_source(
    scatter: str, records: list[Measurement], name: str, images: frozenset[str]
) -> str:
    """The one source of the points of a scatter, which names its file."""
    sources = {
        observation_source(record.source, record.image, name, images)
        for record in records
        if record.source is not None
    }
    if len(sources) > 1:
        raise NotConverted(
            "scatter_source",
            f"Scatter {scatter} has points from {', '.join(sorted(sources))}; "
            "a format 2 scatter has one source.",
        )
    return sources.pop() if sources else TEXT_SOURCE


def _point(scatter: str, prefix: str, record: Measurement) -> dict[str, str]:
    """The `x_` or `y_` cells of a scatter point."""
    stats = record.statistics
    lost = [
        name
        for name in STATISTICS
        if name not in ("mean", "count") and getattr(stats, name) is not None
    ]
    if record.calculation_type is not None:
        lost.append("calculation")
    if record.choice is not None:
        lost.append("choice")
    if lost:
        raise NotConverted(
            "scatter_statistics",
            f"Scatter {scatter} has {', '.join(lost)}; "
            "a format 2 scatter point holds a mean only.",
        )
    return {
        f"{prefix}_interventions": LIST.join(record.interventions),
        f"{prefix}_measurement": text(record.measurement_type),
        f"{prefix}_substance": text(record.substance),
        f"{prefix}_tissue": text(record.tissue),
        f"{prefix}_method": text(record.method),
        f"{prefix}_time": time(record),
        f"{prefix}_time_unit": NOT_REPORTED
        if record.time_unit_not_reported
        else text(record.time_unit),
        f"{prefix}_mean": number(stats.mean),
        f"{prefix}_unit": text(record.unit),
    }


def _scatter_rows(
    study: CanonicalStudy, name: str, images: frozenset[str], decisions: list[Decision]
) -> tuple[Tables, dict[str, str]]:
    """Rows of scatters_<source>.tsv, one per subject pairing its x and y outputs.

    Each subset of a format 1 dataset is one format 2 scatter, named by the
    subset. Its source is the source of its points, as for any output. Also
    returns the table file of each output that became a scatter point.
    """
    by_label: dict[str, list[Measurement]] = {}
    for record in study.measurements:
        if record.label:
            by_label.setdefault(record.label, []).append(record)
    tables: Tables = {}
    used: dict[str, str] = {}
    names: set[str] = set()
    for dataset in study.scatters:
        for subset in dataset.subsets:
            scatter = subset.name or dataset.name
            if scatter in names:
                raise NotConverted(
                    "scatter_name", f"Two scatters have the name {scatter}."
                )
            names.add(scatter)
            labels = [dimension.output for dimension in subset.dimensions]
            if len(labels) != 2:
                raise NotConverted(
                    "scatter_dimensions",
                    f"Scatter {scatter} has {len(labels)} dimensions; "
                    "a format 2 scatter has x and y.",
                )
            pairs = _scatter_pairs(scatter, labels, subset.shared, by_label)
            points = [record for _, x, y in pairs for record in (x, y)]
            source = _scatter_source(scatter, points, name, images)
            file = table_file("scatters", source)
            for record in points:
                if record.key in used:
                    raise NotConverted(
                        "scatter_outputs",
                        f"Output {record.label} is in more than one scatter; "
                        "format 2 holds each point once.",
                    )
                if record.output_type == "timecourse":
                    raise NotConverted(
                        "scatter_outputs",
                        f"Scatter {scatter} uses the timecourse {record.label}; "
                        "format 2 holds a point in a timecourse or in a scatter.",
                    )
                used[record.key] = file
            for subject, x, y in pairs:
                notes = dict.fromkeys(note for note in (comment(x), comment(y)) if note)
                tables.setdefault(file, []).append(
                    {
                        "name": scatter,
                        "subjects": text(subject),
                        "source": source,
                        **_point(scatter, "x", x),
                        **_point(scatter, "y", y),
                        "comment": " / ".join(notes),
                    }
                )
            if labels != [f"{scatter}_x", f"{scatter}_y"]:
                decisions.append(
                    Decision(
                        kind="scatter_label",
                        detail=f"{scatter}: {labels[0]}, {labels[1]} become "
                        f"{scatter}_x, {scatter}_y",
                    )
                )
    return tables, used


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def study_tables(
    study: CanonicalStudy,
    name: str,
    error_bars: ErrorBars = {},
    *,
    images: frozenset[str],
) -> tuple[Tables, list[Decision]]:
    """The format 2 tables of a parsed format 1 study and the decisions to check.

    `images` are the sources that have an image in the v1 folder (`image_sources`).
    """
    decisions: list[Decision] = []
    scatters, used = _scatter_rows(study, name, images, decisions)
    tables: Tables = {
        "subjects.tsv": _subjects(study, name, images, decisions),
        "characteristica.tsv": _characteristica(
            study, name, images, error_bars, decisions
        ),
        "interventions.tsv": _interventions(study, name, images, error_bars, decisions),
    }
    arrays: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    for record in study.measurements:
        if record.key in used:
            file = used[record.key]
        else:
            source, row = _measurement(record, name, error_bars, images)
            row = _geometric(record, row, decisions)
            if record.label and record.output_type in ("timecourse", "array"):
                file = table_file("timecourses", source)
                row = {**row, "label": text(record.label)}
            else:
                file = table_file("outputs", source)
                if record.label:
                    # The outputs table has no label column.
                    labels[file] += 1
            tables.setdefault(file, []).append(row)
        if record.output_type == "array":
            arrays[file] += 1
    tables |= scatters
    # One decision per table: a study can hold thousands of array outputs.
    decisions += [
        Decision(
            kind="array_output", detail=f"{_plural(count, 'array output')} in {file}"
        )
        for file, count in arrays.items()
    ]
    decisions += [
        Decision(
            kind="output_label",
            detail=f"{_plural(count, 'output label')} dropped in {file}",
        )
        for file, count in labels.items()
    ]
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
