"""Equivalence gate: the converted study must mean what the format 1 study meant.

Both folders are prepared with today's `prepare`, so counts are inherited and
calculation types filled the same way on both sides. The reported records of
the format 1 study (A) are rewritten by the intended changes of the conversion
and then compared with the reported records of the converted study (B).
"""

import math
from collections import Counter, defaultdict
from collections.abc import Callable, Collection, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

from pkdb.domain.vocabulary import Vocabulary
from pkdb.importers.folder import load_folder, parse_bundle
from pkdb.migration.metadata import single_line
from pkdb.migration.model import Change, Difference, StudyResult
from pkdb.migration.rows import comment, label_name, scatter_comment, series_arrays
from pkdb.migration.sources import image_sources
from pkdb.preparation import PreparedBundle, prepare
from pkdb.schemas.study import CanonicalStudy, Measurement, Observation, Statistics
from pkdb.schemas.validation import StudyValidationError, ValidationIssue
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.text import format_number

TOLERANCE = 1e-9
MAX_DIFFERENCES = 50
STATISTICS = tuple(Statistics.model_fields)
EXAMPLES = 3
GEOMETRIC_MEAN = "geometric mean"
# The calculation type that `prepare` fills in for the records of a group.
GROUP_CALCULATION = "sample mean"
# Spreads that a format 2 error bar gives as `abs(error_bar - mean)`.
SPREADS = ("sd", "se")
JPG_SUFFIXES = (".jpg", ".jpeg")
# The timecourse dataset that `prepare` generates from the timecourses.
GENERATED_DATASET = "dataset:auto"
# Fields of a key that are shown with their name, such as `time 1`.
NAMED = frozenset({"time", "time_end", "interval", "doses"})
# Fields of a key that the converter writes as text cells on one line.
TEXT = (
    "measurement_type",
    "calculation_type",
    "choice",
    "substance",
    "tissue",
    "method",
    "route",
    "form",
    "application",
    "time_unit",
    "unit",
)
NO_COMMENT = "no comment"
# Cells that identify a row of a converted table, shown with a validation issue.
IDENTIFYING = (
    "subjects",
    "name",
    "interventions",
    "measurement",
    "substance",
    "tissue",
    "time",
    "label",
    "x_measurement",
    "y_measurement",
)


class Key(NamedTuple):
    """What identifies a reported record: records with equal keys are compared."""

    table: str
    image: str | None = None
    output_type: str | None = None
    label: str | None = None
    name: str | None = None
    subject: str | None = None
    group: str | None = None
    individual: str | None = None
    interventions: tuple[str, ...] = ()
    measurement_type: str | None = None
    calculation_type: str | None = None
    choice: str | None = None
    substance: str | None = None
    tissue: str | None = None
    method: str | None = None
    route: str | None = None
    form: str | None = None
    application: str | None = None
    time: float | tuple[float, ...] | None = None
    time_unit: str | None = None
    time_not_reported: bool = False
    time_unit_not_reported: bool = False
    time_end: float | None = None
    interval: float | None = None
    doses: int | None = None
    unit: str | None = None


OBSERVATION = (
    "image",
    "measurement_type",
    "calculation_type",
    "choice",
    "substance",
    "tissue",
    "method",
    "time",
    "time_unit",
    "time_not_reported",
    "time_unit_not_reported",
    "unit",
)
INTERVENTION = ("name", "subject", "route", "form", "application")
INTERVENTION += ("time_end", "interval", "doses")
MEASUREMENT = ("output_type", "label", "group", "individual")


class Reported(NamedTuple):
    """The statistics of a reported record and its one-line comment.

    The comment of a record of A is the comment that the converter writes for
    it, so the comments of paired records must be equal.
    """

    statistics: Statistics
    comment: str


@dataclass
class Changes:
    """Intended changes found while normalizing A, by kind."""

    found: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def add(self, kind: str, example: str) -> None:
        self.found[kind].append(example)

    def listed(self) -> list[Change]:
        return [
            Change(kind=kind, count=len(examples), examples=examples[:EXAMPLES])
            for kind, examples in sorted(self.found.items())
        ]


def same(a: object, b: object) -> bool:
    if isinstance(a, float) and isinstance(b, float):
        return math.isclose(a, b, rel_tol=TOLERANCE, abs_tol=0)
    return a == b


def shown(value: object) -> str:
    if value is None:
        return "missing"
    if isinstance(value, float):
        return format_number(value)
    return str(value)


def described(key: Key) -> str:
    """The table and the fields of a key, such as `measurements[... all D1 cmax ...]`."""
    parts = []
    for name, value in zip(Key._fields[1:], key[1:], strict=True):
        if value is None or value is False or value == ():
            continue
        if value is True:
            parts.append(name)
        elif isinstance(value, tuple):
            parts.append(",".join(shown(item) for item in value))
        else:
            parts.append(f"{name} {shown(value)}" if name in NAMED else shown(value))
    return f"{key.table}[{' '.join(parts)}]"


def _summary(statistics: Statistics | None) -> str:
    if statistics is None:
        return "missing"
    values = [
        f"{name} {shown(getattr(statistics, name))}"
        for name in STATISTICS
        if getattr(statistics, name) is not None
    ]
    return ", ".join(values) or "no statistics"


def _key(table: str, record: Observation, fields: Iterable[str], **extra) -> Key:
    values = {name: getattr(record, name) for name in (*OBSERVATION, *fields)}
    if isinstance(values["time"], list):
        values["time"] = tuple(values["time"])
    return Key(table, **values, **extra)


def _individuals(a: CanonicalStudy, changes: Changes) -> set[str]:
    """Names of A's groups with count 1, which format 2 holds as individuals."""
    names = {group.name for group in a.groups if group.count == 1}
    for name in sorted(names):
        changes.add("group_count_1", name)
    return names


def _subjects(
    study: CanonicalStudy, as_individuals: set[str]
) -> dict[str, list[tuple]]:
    """Kind, count and parent of each subject by name."""
    subjects: dict[str, list[tuple]] = defaultdict(list)
    for group in study.groups:
        if group.name in as_individuals:
            subjects[group.name].append(("individual", 1, group.parent))
        else:
            subjects[group.name].append(("group", group.count, group.parent))
    for individual in study.individuals:
        subjects[individual.name].append(("individual", 1, individual.group))
    return {name: sorted(found, key=str) for name, found in subjects.items()}


def _subject_comments(study: CanonicalStudy) -> dict[str, tuple[str, ...]]:
    """The one-line comment of each subject by name, as the converter writes it."""
    comments: dict[str, list[str]] = defaultdict(list)
    for subject in [*study.groups, *study.individuals]:
        comments[subject.name].append(comment(subject))
    return {name: tuple(sorted(found)) for name, found in comments.items()}


def _comment_text(comments: tuple[str, ...]) -> str:
    return "; ".join(text or NO_COMMENT for text in comments)


def _subject_text(subjects: list[tuple] | None) -> str:
    if subjects is None:
        return "missing"
    texts = []
    for kind, count, parent in subjects:
        text = kind if kind == "individual" else f"{kind}, count {shown(count)}"
        texts.append(f"{text}, parent {parent}" if parent else text)
    return "; ".join(texts)


def _scatter_labels(study: CanonicalStudy) -> dict[str, str]:
    """The format 2 label of each output label that is a scatter dimension.

    A format 2 scatter is named by the format 1 subset and its points are
    labelled `<scatter>_x` and `<scatter>_y`, as the format 2 reader labels them.
    """
    labels = {}
    for dataset in study.scatters:
        if dataset.data_type != "scatter":
            continue
        for subset in dataset.subsets:
            name = subset.name or dataset.name
            for dimension, axis in zip(subset.dimensions, ("x", "y"), strict=False):
                labels.setdefault(dimension.output, f"{name}_{axis}")
    return labels


class _Normalizer:
    """Rewrites the keys and statistics of A's records by the intended changes."""

    def __init__(
        self,
        study: CanonicalStudy,
        as_individuals: set[str],
        changes: Changes,
        arrays: Collection[str],
    ):
        self.name = study.metadata.name
        self.as_individuals = as_individuals
        self.changes = changes
        self.arrays = arrays
        self.labels = _scatter_labels(study)
        self.groups = {group.name for group in study.groups}
        self.images: dict[str, str] = {}
        self.renamed: dict[str, str] = {}

    def whitespace(self, key: Key) -> Key:
        """Text as the converter writes it: on one line, and a blank cell is empty.

        Format 1 keeps text such as the unit `ng  hr/ml` or a substance cell
        holding a space as read.
        """
        # Any: ty checks keyword arguments of _replace against every field type.
        updates: dict[str, Any] = {}
        for name in TEXT:
            value = getattr(key, name)
            if isinstance(value, str) and (single_line(value) or None) != value:
                updates[name] = single_line(value) or None
        if not updates:
            return key
        self.changes.add("whitespace", described(key))
        return key._replace(**updates)

    def image(self, image: str | None) -> str | None:
        """The image file; format 1 keeps the image of a characteristic as written."""
        if not image:
            return image
        if not Path(image).suffix:
            image = f"{self.name}_{image}.png"
        path = Path(image)
        if path.suffix.lower() in JPG_SUFFIXES:
            converted = path.with_suffix(".png").name
            self.images[image] = converted
            return converted
        return image

    def subject(self, key: Key) -> Key:
        """A record of a group with count 1 is a record of an individual.

        `prepare` fills calculation type `sample mean` for the records of a
        group and none for those of an individual, which may report none.
        """
        if key.table == "measurements" and key.group in self.as_individuals:
            key = key._replace(group=None, individual=key.group)
        elif key.table != "characteristica" or key.subject not in self.as_individuals:
            return key
        if key.calculation_type == GROUP_CALCULATION:
            key = key._replace(calculation_type=None)
        return key

    def geometric(self, key: Key, statistics: Statistics) -> tuple[Key, Statistics]:
        """Format 2 retired the calculation `geometric mean`: gmean says it.

        The converter leaves the calculation empty, and `prepare` fills
        `sample mean` for a group's record. A geometric mean that format 1
        wrote as `mean` moves to `gmean`.
        """
        if key.calculation_type != GEOMETRIC_MEAN:
            return key, statistics
        of_group = key.group is not None or (
            key.table == "characteristica" and key.subject in self.groups
        )
        retired = key._replace(calculation_type=GROUP_CALCULATION if of_group else None)
        if statistics.mean is None or statistics.gmean is not None:
            self.changes.add("retired_calculation", described(key))
            return retired, statistics
        self.changes.add("gmean", described(key))
        return retired, statistics.model_copy(
            update={"gmean": statistics.mean, "mean": None}
        )

    def output(self, key: Key, record: str) -> Key:
        """Array outputs and output labels as format 2 holds them.

        Array outputs in `arrays` become timecourse points. Scatter points
        take the labels of their scatter; other outputs lose their label,
        since the format 2 outputs table has none.
        """
        scatter = self.labels.get(key.label) if key.label else None
        if key.output_type == "array":
            self.changes.add("array_output", described(key))
            kind = "timecourse" if record in self.arrays else "output"
            key = key._replace(output_type=kind)
        if scatter is not None and scatter != key.label:
            key = key._replace(label=scatter)
        elif scatter is None and key.label and key.output_type == "output":
            self.changes.add("output_label", described(key))
            key = key._replace(label=None)
        elif key.label and key.output_type == "timecourse":
            name = label_name(key.label)
            if name != key.label:
                self.renamed[key.label] = name
                key = key._replace(label=name)
        return key

    def __call__(
        self, key: Key, statistics: Statistics, record: str
    ) -> tuple[Key, Statistics]:
        key = self.whitespace(key)
        key, statistics = self.geometric(
            key._replace(image=self.image(key.image)), statistics
        )
        key = self.subject(key)
        if key.table == "measurements":
            key = self.output(key, record)
        return key, statistics

    def finish(self) -> None:
        for old, new in sorted(self.images.items()):
            self.changes.add("image_converted", f"{old} to {new}")
        for old, new in self.labels.items():
            if old != new:
                self.changes.add("scatter_label", f"{old} to {new}")
        for old, new in self.renamed.items():
            self.changes.add("label_renamed", f"{old!r} to {new}")


def _origin(by_key: Mapping[str, Measurement], record_key: str) -> Measurement | None:
    """The reported record that a measurement derives from."""
    record = by_key.get(record_key)
    while record is not None and record.origin != "reported":
        record = by_key.get(record.derived_from) if record.derived_from else None
    return record


def _scatter_comments(study: CanonicalStudy) -> dict[str, str]:
    """The comment of each scatter point: the converter joins those of x and y."""
    by_key = {record.key: record for record in study.measurements}
    comments = {}
    for dataset in study.scatters:
        if dataset.key == GENERATED_DATASET:
            continue
        for subset in dataset.subsets:
            for pair in subset.points:
                points = [_origin(by_key, key) for key in pair]
                if len(points) != 2 or None in points:
                    continue
                x, y = points
                assert x is not None and y is not None
                comments[x.key] = comments[y.key] = scatter_comment(x, y)
    return comments


def _records(
    study: CanonicalStudy,
    as_individuals: set[str],
    changes: Changes | None,
    arrays: Collection[str] = frozenset(),
) -> tuple[dict[Key, list[Reported]], dict[str, Key]]:
    """The reported records by key, and the key of each measurement.

    With `changes`, the records are A's, rewritten by the intended changes,
    with the comment that the converter writes for them; `arrays` are the
    array outputs that become timecourse points.
    """
    normalize = (
        None if changes is None else _Normalizer(study, as_individuals, changes, arrays)
    )
    scatter_comments = {} if changes is None else _scatter_comments(study)
    records: dict[Key, list[Reported]] = defaultdict(list)

    def add(key: Key, record: Observation) -> Key:
        statistics = record.statistics
        if normalize is not None:
            key, statistics = normalize(key, statistics, record.key)
        text = scatter_comments.get(record.key)
        records[key].append(
            Reported(statistics, comment(record) if text is None else text)
        )
        return key

    for subject in [*study.groups, *study.individuals]:
        for record in subject.characteristica:
            if record.origin == "reported":
                add(_key("characteristica", record, (), subject=subject.name), record)
    for record in study.interventions:
        if record.origin == "reported":
            add(_key("interventions", record, INTERVENTION), record)
    keys: dict[str, Key] = {}
    for record in study.measurements:
        if record.origin == "reported":
            key = _key(
                "measurements",
                record,
                MEASUREMENT,
                interventions=tuple(sorted(record.interventions)),
            )
            keys[record.key] = add(key, record)
    if normalize is not None:
        normalize.finish()
    return records, keys


def _reported(
    study: CanonicalStudy, keys: Mapping[str, Key]
) -> Callable[[str], object]:
    """The key of the reported record that a measurement derives from.

    A record that leads to no reported record keeps its own record key, which
    differs between the two formats, so it never matches.
    """
    by_key = {record.key: record for record in study.measurements}

    def reported(record_key: str) -> object:
        record = _origin(by_key, record_key)
        if record is None or record.key not in keys:
            return f"unknown record {record_key}"
        return keys[record.key]

    return reported


def _timecourses(
    study: CanonicalStudy, keys: Mapping[str, Key]
) -> dict[str, frozenset]:
    """The points of each timecourse by label, as reported records.

    The reported and the normalized timecourse of a label hold the same
    reported records. Format 1 array outputs that become timecourses join the
    timecourse of their label, as format 2 groups timecourse points by label.
    """
    reported = _reported(study, keys)
    courses: dict[str, set] = defaultdict(set)
    for course in study.timecourses:
        points = {reported(point.key) for point in course.points}
        labels = {point.label for point in points if isinstance(point, Key)}
        courses[" ".join(sorted(str(label) for label in labels))] |= points
    for record in study.measurements:
        key = keys.get(record.key)
        if record.output_type == "array" and key and key.output_type == "timecourse":
            courses[str(key.label)].add(key)
    return {label: frozenset(points) for label, points in courses.items()}


def _scatters(study: CanonicalStudy, keys: Mapping[str, Key]) -> dict[str, Counter]:
    """The points of each scatter by subset name, as pairs of reported records."""
    reported = _reported(study, keys)
    scatters: dict[str, Counter] = defaultdict(Counter)
    for dataset in study.scatters:
        if dataset.key == GENERATED_DATASET:
            continue
        for subset in dataset.subsets:
            points = frozenset(
                tuple(reported(point) for point in pair) for pair in subset.points
            )
            scatters[subset.name or dataset.name][dataset.data_type, points] += 1
    return scatters


def _order(statistics: Statistics) -> tuple:
    """Sort key of statistics: numbers by value, then text, then missing values."""
    order = []
    for name in STATISTICS:
        value = getattr(statistics, name)
        if value is None:
            order.append((2, 0))
        elif isinstance(value, str):
            order.append((1, value))
        else:
            order.append((0, value))
    return tuple(order)


def _same_statistics(a: Statistics, b: Statistics) -> bool:
    return all(same(getattr(a, name), getattr(b, name)) for name in STATISTICS)


def _error_bars(a: Statistics, b: Statistics) -> Statistics | None:
    """B's statistics with A's spread when B's error bar gives exactly that spread.

    The converter writes `error_bar` X and `error_type` for a format 1 spread
    computed as `ABS(X - mean)`; format 2 derives the spread back from them.
    """
    kind = b.error_type
    if (
        kind not in SPREADS
        or b.error_bar is None
        or getattr(b, kind) is not None
        or a.error_bar is not None
        or a.error_type is not None
    ):
        return None
    spread = getattr(a, kind)
    if spread is None or a.mean is None:
        return None
    if not same(spread, abs(b.error_bar - a.mean)):
        return None
    return b.model_copy(update={kind: spread, "error_bar": None, "error_type": None})


class _Paired(NamedTuple):
    """Records left unpaired, the number of pairs and of those paired by an error bar.

    `comments` holds the expected and the found comment of each pair whose
    comments differ.
    """

    a: list[Reported]
    b: list[Reported]
    pairs: int
    bars: int
    comments: list[tuple[str, str]]


def _same_record(a: Reported, b: Reported) -> bool:
    return a.comment == b.comment and _same_statistics(a.statistics, b.statistics)


def _same_values(a: Reported, b: Reported) -> bool:
    return _same_statistics(a.statistics, b.statistics)


def _by_error_bar(a: Reported, b: Reported) -> bool:
    bar = _error_bars(a.statistics, b.statistics)
    return bar is not None and _same_statistics(a.statistics, bar)


def _pair(a: list[Reported], b: list[Reported]) -> _Paired:
    """Pair records that are equal, directly or through B's error bar.

    Records with equal comments pair first, so that a differing comment is
    reported only where no record with the expected comment is left.
    """

    def order(record: Reported) -> tuple:
        return _order(record.statistics), record.comment

    left = sorted(a, key=order)
    right = sorted(b, key=order)
    if len(left) == len(right) and all(map(_same_record, left, right)):
        return _Paired([], [], len(left), 0, [])
    pairs, bars, comments = 0, 0, []
    for same in (_same_record, _same_values, _by_error_bar):
        unmatched = []
        for record in left:
            found = next(
                (i for i, other in enumerate(right) if same(record, other)), None
            )
            if found is None:
                unmatched.append(record)
                continue
            other = right.pop(found)
            pairs += 1
            bars += same is _by_error_bar
            if record.comment != other.comment:
                comments.append((record.comment, other.comment))
        left = unmatched
    return _Paired(left, right, pairs, bars, comments)


def _unpaired(key: Key, a: list[Reported], b: list[Reported]) -> list[Difference]:
    """Differences of the records of one key that found no equal record."""
    differences = []
    path = described(key)
    for index in range(max(len(a), len(b))):
        old = a[index].statistics if index < len(a) else None
        new = b[index].statistics if index < len(b) else None
        if old is None or new is None:
            differences.append(Difference(path=path, a=_summary(old), b=_summary(new)))
            continue
        new = _error_bars(old, new) or new
        differences.extend(
            Difference(
                path=f"{path}.{name}",
                a=shown(getattr(old, name)),
                b=shown(getattr(new, name)),
            )
            for name in STATISTICS
            if not same(getattr(old, name), getattr(new, name))
        )
    return differences


def _match(
    a: Mapping[Key, list[Reported]],
    b: Mapping[Key, list[Reported]],
    changes: Changes,
) -> list[Difference]:
    """Pair A's records with B's records of the same key, then list the rest.

    Images are provenance: an A record without image pairs with a B record
    that differs only by having one, an intended change `image_added`. An A
    image that differs from B's stays a difference. Paired records whose
    comments differ are a difference of their comment.
    """
    left_a: dict[Key, list[Reported]] = {}
    left_b = {key: list(records) for key, records in b.items()}
    differences = []

    def pair(key: Key, other: Key) -> int:
        paired = _pair(left_a[key], left_b.get(other, []))
        left_a[key], left_b[other] = paired.a, paired.b
        for _ in range(paired.bars):
            changes.add("error_bar", described(other))
        differences.extend(
            Difference(
                path=f"{described(key)}.comment",
                a=expected or NO_COMMENT,
                b=found or NO_COMMENT,
            )
            for expected, found in paired.comments
        )
        return paired.pairs

    for key, records in a.items():
        left_a[key] = records
        pair(key, key)
    with_image = defaultdict(list)
    for key in b:
        if key.image is not None:
            with_image[key._replace(image=None)].append(key)
    for key in a:
        if key.image is None:
            for other in with_image.get(key, []):
                for _ in range(pair(key, other)):
                    changes.add("image_added", described(other))
    for key in dict.fromkeys([*a, *b]):
        differences += _unpaired(key, left_a.get(key, []), left_b.get(key, []))
    return differences


def _differences[T](
    section: str,
    a: Mapping[str, T],
    b: Mapping[str, T],
    text: Callable[[T | None], str],
) -> list[Difference]:
    return [
        Difference(path=f"{section}[{name}]", a=text(a.get(name)), b=text(b.get(name)))
        for name in dict.fromkeys([*a, *b])
        if a.get(name) != b.get(name)
    ]


def _points(points: object) -> str:
    if points is None:
        return "missing"
    if isinstance(points, frozenset):
        return f"{len(points)} points"
    assert isinstance(points, Counter)
    return "; ".join(
        f"{kind} of {len(pairs)} points"
        for (kind, pairs), count in sorted(points.items(), key=lambda item: item[0][0])
        for _ in range(count)
    )


def compare(
    a: CanonicalStudy, b: CanonicalStudy, arrays: Collection[str] = frozenset()
) -> tuple[list[Change], list[Difference]]:
    """The intended changes from A to B and every other difference between them.

    `arrays` are the keys of A's array outputs that become timecourse points
    (`rows.series_arrays`); other array outputs become outputs.
    """
    changes = Changes()
    as_individuals = _individuals(a, changes)
    a_records, a_keys = _records(a, as_individuals, changes, arrays)
    b_records, b_keys = _records(b, set(), None)
    differences = _match(a_records, b_records, changes)
    # Timecourses and scatters hold records; their images are compared above.
    a_keys = {record: key._replace(image=None) for record, key in a_keys.items()}
    b_keys = {record: key._replace(image=None) for record, key in b_keys.items()}
    differences += _differences(
        "subjects",
        _subjects(a, as_individuals),
        _subjects(b, set()),
        _subject_text,
    )
    a_comments, b_comments = _subject_comments(a), _subject_comments(b)
    differences += [
        Difference(
            path=f"subjects[{name}].comment",
            a=_comment_text(a_comments[name]),
            b=_comment_text(b_comments[name]),
        )
        for name in a_comments
        if name in b_comments and a_comments[name] != b_comments[name]
    ]
    differences += _differences(
        "timecourses", _timecourses(a, a_keys), _timecourses(b, b_keys), _points
    )
    differences += _differences(
        "scatters", _scatters(a, a_keys), _scatters(b, b_keys), _points
    )
    return changes.listed(), differences


def _series_arrays(v1: Path, study: CanonicalStudy) -> frozenset[str]:
    """The array outputs of A that the converter writes as timecourse points.

    The converter decides this on the parsed, not the prepared, format 1
    study, whose calculation types `prepare` has not filled yet.
    """
    if not any(r.output_type == "array" and r.label for r in study.measurements):
        return frozenset()
    parsed = parse_bundle(load_folder(v1))
    return series_arrays(parsed, v1.name, image_sources(v1, v1.name))


def _errors(bundle: PreparedBundle) -> list[str]:
    return sorted({i.code for i in bundle.report.issues if i.severity == "error"})


def _where(issue: ValidationIssue) -> str:
    """The file and cell, else row, of an issue, such as `outputs_Tab2.tsv:E2`."""
    source = issue.source
    if source is None:
        return ""
    if source.cell:
        return f"{source.file}:{source.cell}"
    if source.row is not None:
        return f"{source.file}:{source.row}"
    return source.file


class _Rows:
    """The identifying cells of rows of the converted tables, each file read once.

    The converted folder is deleted after the run, so the curator learns from
    these cells which format 1 row to fix.
    """

    def __init__(self, folder: Path):
        self.folder = folder
        self.tables: dict[str, list[list[str]]] = {}

    def cells(self, issue: ValidationIssue) -> str:
        """Such as `[subjects=S2 measurement=age]`; empty for an issue without row."""
        source = issue.source
        if (
            source is None
            or source.row is None
            or source.row < 2
            or Path(source.file).name != source.file
            or not source.file.endswith(".tsv")
        ):
            return ""
        if source.file not in self.tables:
            try:
                text = (self.folder / source.file).read_text(encoding="utf-8")
            except OSError, ValueError:
                text = ""
            self.tables[source.file] = [line.split("\t") for line in text.split("\n")]
        lines = self.tables[source.file]
        if source.row > len(lines):
            return ""
        row = dict(zip(lines[0], lines[source.row - 1], strict=False))
        shown = [f"{name}={row[name]}" for name in IDENTIFYING if row.get(name)]
        return f"[{' '.join(shown)}]" if shown else ""


def _invalid(
    study: str, check: str, issues: Iterable[ValidationIssue], folder: Path
) -> StudyResult:
    """A converted study that format 2 refuses, with the errors a curator fixes."""
    errors = [issue for issue in issues if issue.severity == "error"]
    rows = _Rows(folder)
    return StudyResult(
        study=study,
        outcome="mismatch",
        issues=sorted({issue.code for issue in errors}),
        differences=[
            Difference(
                path=" ".join(
                    part for part in (check, _where(i), i.code, rows.cells(i)) if part
                ),
                a="valid",
                b=i.message,
            )
            for i in errors[:MAX_DIFFERENCES]
        ],
    )


def judge(v1: Path, converted: Path, vocabulary: Vocabulary) -> StudyResult:
    """Prepare the format 1 study and its conversion and classify the conversion."""
    study = f"{v1.parent.name}/{v1.name}"
    try:
        a = prepare(v1, vocabulary=vocabulary)
    except StudyValidationError as error:
        issues = sorted({i.code for i in error.report.issues})
        return StudyResult(study=study, outcome="invalid_v1", issues=issues)
    if errors := _errors(a):
        return StudyResult(study=study, outcome="invalid_v1", issues=errors)
    formatted = format_folder(converted, check=True)
    if not formatted.ok:
        return _invalid(study, "format", formatted.issues, converted)
    if formatted.changes:
        return StudyResult(
            study=study,
            outcome="mismatch",
            differences=[
                Difference(path="format", a="canonical", b="needs formatting")
            ],
        )
    try:
        b = prepare(converted, vocabulary=vocabulary)
    except StudyValidationError as error:
        return _invalid(study, "validation", error.report.issues, converted)
    if _errors(b):
        return _invalid(study, "validation", b.report.issues, converted)
    changes, differences = compare(a.study, b.study, _series_arrays(v1, a.study))
    if differences:
        return StudyResult(
            study=study,
            outcome="mismatch",
            changes=changes,
            differences=differences[:MAX_DIFFERENCES],
        )
    return StudyResult(
        study=study, outcome="intended" if changes else "identical", changes=changes
    )
