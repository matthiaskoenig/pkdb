"""Read a study format 2 folder into the canonical study.

The reader expects a study without errors in validation layers 1 to 5: every
cell is typed and every reference resolves. Records that the canonical model
still refuses, such as keys longer than the database allows, are reported as
issues at their cell instead of raising.
"""

from collections import defaultdict
from collections.abc import Callable, Mapping

from pydantic import BaseModel, ValidationError

from pkdb.schemas.source import SourceLocation
from pkdb.schemas.study import (
    CanonicalStudy,
    Comment,
    DataRecord,
    Description,
    Dimension,
    Group,
    Individual,
    Intervention,
    Measurement,
    Metadata,
    Notes,
    Observation,
    Reference,
    Statistics,
    Subset,
)
from pkdb.schemas.validation import (
    StudyValidationError,
    ValidationIssue,
    ValidationReport,
)
from pkdb.source_files import attachments_and_digest
from pkdb.studyformat import models
from pkdb.studyformat.cells import NOT_REPORTED
from pkdb.studyformat.issues import column_letter
from pkdb.studyformat.jsonio import load_json
from pkdb.studyformat.load import LoadedStudy, LoadedTable, Row
from pkdb.studyformat.tables import (
    REFERENCE_JSON,
    STUDY_JSON,
    TABLES,
    TEXT_SOURCE,
    image_file,
)

STATISTICS = tuple(Statistics.model_fields)
# Statistics written in percent and stored as fractions.
PERCENT = frozenset({"cv", "gcv"})
# Record fields and the columns that hold them, shared by the observation tables.
_OBSERVATION = {
    "measurement_type": "measurement",
    "calculation_type": "calculation",
    "substance": "substance",
    "tissue": "tissue",
    "method": "method",
    "choice": "choice",
    "time": "time",
    "time_not_reported": "time",
    "time_unit": "time_unit",
    "time_unit_not_reported": "time_unit",
    "unit": "unit",
    "image": "source",
    **{name: name for name in STATISTICS},
}
_OUTPUT = {
    **_OBSERVATION,
    "group": "subjects",
    "individual": "subjects",
    "interventions": "interventions",
    "label": "label",
}
_FIELDS = {
    "subjects": {
        "name": "name",
        "parent": "parent",
        "group": "parent",
        "count": "count",
        "image": "source",
    },
    "characteristica": _OBSERVATION,
    "interventions": {
        **_OBSERVATION,
        "name": "name",
        "subject": "subjects",
        "route": "route",
        "form": "form",
        "application": "application",
        "time_end": "time_end",
        "interval": "interval",
        "doses": "doses",
    },
    "outputs": _OUTPUT,
    "timecourses": _OUTPUT,
    "scatters": {"name": "name", "image": "source"},
}
_AXIS = (
    "measurement",
    "substance",
    "tissue",
    "method",
    "time",
    "time_unit",
    "mean",
    "unit",
    "interventions",
)


def _axis_fields(prefix: str) -> dict[str, str]:
    """Record fields of one scatter axis and their `x_` or `y_` columns."""
    fields = {
        field: f"{prefix}_{column}"
        for field, column in _OUTPUT.items()
        if column in _AXIS
    }
    fields.update(group="subjects", individual="subjects", label="name", image="source")
    return fields


def _headers(kind: str, fields: Mapping[str, str]) -> dict[str, str]:
    names = TABLES[kind].names
    return {field: header for field, header in fields.items() if header in names}


HEADERS = {kind: _headers(kind, fields) for kind, fields in _FIELDS.items()}
AXIS_HEADERS = {
    prefix: _headers("scatters", _axis_fields(prefix)) for prefix in ("x", "y")
}


def _comments(row: Row) -> list[Comment]:
    text = row.cells["comment"]
    return [Comment(text=text)] if text else []


def _names(value: object) -> list[str]:
    return list(value) if isinstance(value, tuple) else []


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _number(value: object) -> float | None:
    return value if isinstance(value, float) else None


def _time(values: Mapping[str, object], prefix: str = "") -> dict:
    """Time, time unit and their not-reported flags of an observation."""
    time, unit = values[f"{prefix}time"], values[f"{prefix}time_unit"]
    return dict(
        time=_number(time),
        time_unit=None if unit == NOT_REPORTED else _text(unit),
        time_not_reported=time == NOT_REPORTED,
        time_unit_not_reported=unit == NOT_REPORTED,
    )


def _statistics(values: Mapping[str, object], prefix: str = "") -> Statistics:
    data: dict[str, object] = {}
    for name in STATISTICS:
        value = values.get(prefix + name)
        if isinstance(value, float) and name in PERCENT:
            value /= 100
        if value is not None:
            data[name] = value
    return Statistics.model_validate(data)


def _notes(notes: models.Notes) -> Notes:
    return Notes(
        descriptions=[Description(text=text) for text in notes.descriptions],
        comments=[Comment(user=c.user, text=c.text) for c in notes.comments],
    )


class _Reader:
    def __init__(self, study: LoadedStudy):
        self.study = study
        self.issues: list[ValidationIssue] = []
        subjects = {
            row.cells["name"]: row.values["count"] for _, row in study.rows("subjects")
        }
        self.individuals = {name for name, count in subjects.items() if count == 1}

    def build[M: BaseModel](
        self, model: type[M], source: SourceLocation, **data
    ) -> M | None:
        """A record at its source location, or None after reporting why it is refused."""
        return self.validate(model, source, {**data, "source": source})

    def validate[M: BaseModel](
        self, model: type[M], location: SourceLocation, data: dict
    ) -> M | None:
        """The model, or None after reporting each refused field at its location."""
        try:
            return model.model_validate(data)
        except ValidationError as error:
            for detail in error.errors(include_url=False):
                field = ".".join(str(part) for part in detail["loc"])
                head = str(detail["loc"][0]) if detail["loc"] else ""
                self.issues.append(
                    ValidationIssue(
                        code=detail["type"],
                        message=f"{field or model.__name__}: {detail['msg']}",
                        source=location.for_field(head),
                        category="schema",
                        stage="parse",
                        field=field or None,
                    )
                )
            return None

    def image(self, source: object) -> str | None:
        if not isinstance(source, str) or source == TEXT_SOURCE:
            return None
        return image_file(self.study.name, source)

    def subject(self, name: object) -> dict:
        """The `group` or `individual` field of a record about a subject."""
        if not isinstance(name, str):
            return {}
        return {"individual" if name in self.individuals else "group": name}

    def tables(
        self, kind: str
    ) -> list[tuple[LoadedTable, Callable[[Row, dict], SourceLocation]]]:
        return [(table, _locator(table)) for table in self.study.of_kind(kind)]

    def subjects(self) -> tuple[list[Group], list[Individual]]:
        characteristica = defaultdict(list)
        for table, locate in self.tables("characteristica"):
            for row in table.rows:
                values = row.values
                record = self.build(
                    Observation,
                    locate(row, HEADERS["characteristica"]),
                    key=f"{table.file}:{row.line}",
                    image=self.image(values["source"]),
                    comments=_comments(row),
                    **self.observation(values),
                )
                if record is not None:
                    characteristica[values["subjects"]].append(record)
        groups, individuals = [], []
        for table, locate in self.tables("subjects"):
            for row in table.rows:
                values = row.values
                name, parent = values["name"], values["parent"]
                common = dict(
                    key=name,
                    name=name,
                    image=self.image(values["source"]),
                    comments=_comments(row),
                    characteristica=characteristica[name],
                )
                source = locate(row, HEADERS["subjects"])
                if values["count"] == 1:
                    record = self.build(Individual, source, group=parent, **common)
                    if record is not None:
                        individuals.append(record)
                else:
                    group = self.build(
                        Group, source, count=values["count"], parent=parent, **common
                    )
                    if group is not None:
                        groups.append(group)
        return groups, individuals

    def observation(self, values: Mapping[str, object]) -> dict:
        """Fields of an observation row: terms, time and statistics."""
        return dict(
            measurement_type=values["measurement"],
            calculation_type=values["calculation"],
            substance=values["substance"],
            tissue=values["tissue"],
            method=values["method"],
            choice=values["choice"],
            unit=values["unit"],
            statistics=_statistics(values),
            **_time(values),
        )

    def interventions(self) -> list[Intervention]:
        records = []
        for table, locate in self.tables("interventions"):
            for row in table.rows:
                values = row.values
                fields = self.observation(values)
                times = values["time"]
                fields["time"] = (
                    (times[0] if len(times) == 1 else list(times))
                    if isinstance(times, tuple)
                    else None
                )
                record = self.build(
                    Intervention,
                    locate(row, HEADERS["interventions"]),
                    key=values["name"],
                    name=values["name"],
                    time_end=values["time_end"],
                    interval=values["interval"],
                    doses=values["doses"],
                    subject=values["subjects"],
                    route=values["route"],
                    form=values["form"],
                    application=values["application"],
                    image=self.image(values["source"]),
                    comments=_comments(row),
                    **fields,
                )
                if record is not None:
                    records.append(record)
        return records

    def measurements(self) -> list[Measurement]:
        records = []
        for kind in ("outputs", "timecourses"):
            for table, locate in self.tables(kind):
                image = self.image(table.source)
                for row in table.rows:
                    values = row.values
                    label = values.get("label")
                    record = self.build(
                        Measurement,
                        locate(row, HEADERS[kind]),
                        key=f"{table.file}:{row.line}",
                        output_type="timecourse" if label else "output",
                        label=label,
                        series_key=f"{table.file}:{label}" if label else None,
                        interventions=_names(values["interventions"]),
                        image=image,
                        comments=_comments(row),
                        **self.subject(values["subjects"]),
                        **self.observation(values),
                    )
                    if record is not None:
                        records.append(record)
        return records

    def scatters(self) -> tuple[list[Measurement], list[DataRecord]]:
        points, datasets = [], []
        for table, locate in self.tables("scatters"):
            image = self.image(table.source)
            # The first row and the subjects of every scatter dataset.
            first: dict[str, Row] = {}
            subjects: dict[str, set[object]] = defaultdict(set)
            for row in table.rows:
                values = row.values
                name = row.cells["name"]
                first.setdefault(name, row)
                subjects[name].add(values["subjects"])
                for prefix in ("x", "y"):
                    axis = f"{prefix}_"
                    point = self.build(
                        Measurement,
                        locate(row, AXIS_HEADERS[prefix]),
                        key=f"{table.file}:{row.line}:{prefix}",
                        label=f"{name}_{prefix}",
                        measurement_type=values[f"{axis}measurement"],
                        substance=values[f"{axis}substance"],
                        tissue=values[f"{axis}tissue"],
                        method=values[f"{axis}method"],
                        unit=values[f"{axis}unit"],
                        statistics=_statistics(values, axis),
                        interventions=_names(values[f"{axis}interventions"]),
                        image=image,
                        comments=_comments(row),
                        **self.subject(values["subjects"]),
                        **_time(values, axis),
                    )
                    if point is not None:
                        points.append(point)
            for name, row in first.items():
                individual = subjects[name] <= self.individuals
                shared = "individual" if individual else "group"
                dataset = self.build(
                    DataRecord,
                    locate(row, HEADERS["scatters"]),
                    key=f"{table.file}:{name}",
                    name=name,
                    data_type="scatter",
                    image=image,
                    subsets=[
                        Subset(
                            name=name,
                            dimensions=[
                                Dimension(dimension="0", output=f"{name}_x"),
                                Dimension(dimension="1", output=f"{name}_y"),
                            ],
                            shared=[shared],
                        )
                    ],
                )
                if dataset is not None:
                    datasets.append(dataset)
        return points, datasets


def _locator(table: LoadedTable) -> Callable[[Row, dict], SourceLocation]:
    """Locations of the rows of a table; columns and headers are shared, not copied."""
    sheet = table.file.removesuffix(".tsv")
    columns = {name: column_letter(index) for index, name in enumerate(table.header)}

    def locate(row: Row, headers: dict) -> SourceLocation:
        location = SourceLocation(file=table.file, sheet=sheet, row=row.line)
        location._columns = columns
        location._headers = headers
        return location

    return locate


def _metadata(study: LoadedStudy) -> dict:
    """Fields of the canonical metadata from study.json and review.json."""
    metadata = study.metadata
    assert metadata is not None
    release = metadata.release
    return dict(
        name=study.name,
        date=release.date if release else None,
        creator=metadata.creator,
        curators=[dict(user=c.user, rating=c.rating) for c in metadata.curators],
        collaborators=list(metadata.collaborators),
        licence=metadata.licence,
        access=metadata.access,
        provenance=metadata.provenance,
        issue=metadata.issue,
        release=release,
        review=study.review,
        descriptions=[dict(text=text) for text in metadata.descriptions],
        comments=[dict(user=c.user, text=c.text) for c in metadata.comments],
    )


def _reference(study: LoadedStudy) -> dict:
    """The reference snapshot with the sid of the publication that study.json names.

    study.json is the single source for the publication: its PubMed ID, else
    its DOI, identifies the reference even when the snapshot was enriched with
    other identifiers. A manual reference keeps the sid of its snapshot.
    """
    assert study.metadata is not None and study.reference is not None
    named = study.metadata.reference
    data = dict(study.reference)
    if named is not None:
        data["sid"] = named.pmid or named.doi
    return data


def read_study(study: LoadedStudy) -> CanonicalStudy:
    """The canonical study of a folder without errors in validation layers 1 to 5.

    Raises StudyValidationError with located issues for records that the
    canonical model refuses.
    """
    assert study.metadata is not None and study.reference is not None
    reader = _Reader(study)
    groups, individuals = reader.subjects()
    interventions = reader.interventions()
    measurements = reader.measurements()
    points, scatters = reader.scatters()
    study_json = SourceLocation(file=STUDY_JSON)
    metadata = reader.validate(Metadata, study_json, _metadata(study))
    reference = reader.validate(
        Reference, SourceLocation(file=REFERENCE_JSON), _reference(study)
    )
    files = {
        name: study.folder / name
        for name in sorted(study.layout.files)
        if name not in (STUDY_JSON, REFERENCE_JSON)
    }
    attachments, digest = attachments_and_digest(
        load_json((study.folder / STUDY_JSON).read_bytes()), study.reference, files
    )
    if not reader.issues:
        canonical = reader.validate(
            CanonicalStudy,
            study_json,
            dict(
                sid=f"{study.layout.substance}/{study.name}",
                metadata=metadata,
                reference=reference,
                groups=groups,
                individuals=individuals,
                interventions=interventions,
                measurements=[*measurements, *points],
                scatters=scatters,
                attachments=attachments,
                section_notes={
                    kind: _notes(notes) for kind, notes in study.metadata.notes.items()
                },
                source_digest=digest,
            ),
        )
        if canonical is not None:
            return canonical
    raise StudyValidationError(ValidationReport(issues=reader.issues))
