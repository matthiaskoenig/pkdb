"""Reading study format 2 folders into the canonical study and preparing them."""

from copy import deepcopy

import pytest

from pkdb.domain.validation import PROCESSING_VERSION
from pkdb.schemas.provenance import ManualCuration
from pkdb.schemas.review import Release, Review
from pkdb.schemas.source import SourceLocation
from pkdb.schemas.study import (
    Comment,
    Curator,
    Description,
    Dimension,
    Notes,
    Statistics,
    Subset,
)
from pkdb.schemas.validation import StudyValidationError
from pkdb.source_files import attachments_and_digest
from pkdb.studyformat import prepare_folder, read_study
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.jsonio import dump_json, load_json
from pkdb.studyformat.load import load_study

DOSE = {
    "source": "Text",
    "measurement": "dosing",
    "substance": "drug",
    "route": "oral",
    "form": "tablet",
    "application": "single dose",
    "time_unit": "h",
    "unit": "mg",
}
CMAX = {
    "subjects": "all",
    "interventions": "D1",
    "measurement": "cmax",
    "substance": "drug",
    "tissue": "plasma",
    "mean": "2.5",
    "sd": "0.5",
    "unit": "mg/l",
}


def read(folder):
    study = load_study(folder)
    assert study.issues == []
    return read_study(study)


def study_json(folder) -> dict:
    data = load_json((folder / "study.json").read_bytes())
    assert isinstance(data, dict)
    return data


def by_key(records):
    return {record.key: record for record in records}


def write(folder, name, text):
    (folder / name).write_text(text, encoding="utf-8", newline="")
    assert format_folder(folder).ok


def test_identity_metadata_and_reference(valid_study):
    study = read(valid_study)
    assert study.sid == "caffeine/Example"
    metadata = study.metadata
    assert (metadata.name, metadata.date, metadata.creator) == (
        "Example",
        None,
        "curator",
    )
    assert metadata.curators == [Curator(user="curator", rating=3)]
    assert (metadata.licence, metadata.access) == ("open", "private")
    assert metadata.provenance == ManualCuration()
    assert (metadata.issue, metadata.release) == (None, None)
    assert metadata.review == Review(status="draft")
    assert study.reference.model_dump(exclude_none=True) == {
        "sid": "123",
        "name": "Example",
        "pmid": "123",
        "title": "Example study",
        "authors": [],
        "provenance": {},
    }
    assert study.section_notes == {}


def test_study_json_notes_release_and_review(valid_study):
    path = valid_study / "study.json"
    data = study_json(valid_study)
    data.update(
        issue=2158,
        release={"pkdb_id": "PKDB01237", "date": "2026-09-28"},
        access="public",
        collaborators=["Jane Doe"],
        descriptions=["Crossover study."],
        comments=[{"user": "curator", "text": "Doses from the methods."}],
        notes={
            "timecourses": {
                "descriptions": ["Digitized."],
                "comments": [{"user": "reviewer", "text": "Check Fig1."}],
            }
        },
    )
    path.write_text(dump_json(data), encoding="utf-8", newline="")
    review = {
        "status": "in_review",
        "reviewers": ["reviewer"],
        "items": [
            {
                "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2AB",
                "kind": "question",
                "text": "Fasted?",
                "author": "reviewer",
                "created": "2026-10-05T10:12:00Z",
            }
        ],
    }
    write(valid_study, "review.json", dump_json(review))
    metadata = read(valid_study).metadata
    assert metadata.issue == 2158
    assert metadata.release == Release(pkdb_id="PKDB01237", date="2026-09-28")
    assert metadata.date == metadata.release.date
    assert metadata.access == "public"
    assert metadata.collaborators == ["Jane Doe"]
    assert metadata.descriptions == [Description(text="Crossover study.")]
    assert metadata.comments == [
        Comment(user="curator", text="Doses from the methods.")
    ]
    assert metadata.review == Review.model_validate(review)
    assert read(valid_study).section_notes == {
        "timecourses": Notes(
            descriptions=[Description(text="Digitized.")],
            comments=[Comment(user="reviewer", text="Check Fig1.")],
        )
    }


def test_reference_sid_is_the_doi_without_a_pmid(valid_study):
    data = study_json(valid_study)
    data["reference"] = {"doi": "10.1234/abc"}
    (valid_study / "study.json").write_text(
        dump_json(data), encoding="utf-8", newline=""
    )
    reference = {"sid": "x", "name": "Example", "doi": "10.1234/abc"}
    (valid_study / "reference.json").write_text(
        dump_json(reference), encoding="utf-8", newline=""
    )
    assert read(valid_study).reference.sid == "10.1234/abc"


def test_reference_sid_is_the_normalized_doi(valid_study):
    # DOIs are case-insensitive; the server matches publications by the lowercase form.
    data = study_json(valid_study)
    data["reference"] = {"doi": "10.1234/ABC.Def"}
    (valid_study / "study.json").write_text(
        dump_json(data), encoding="utf-8", newline=""
    )
    reference = {"sid": "x", "name": "Example", "doi": "10.1234/ABC.Def"}
    (valid_study / "reference.json").write_text(
        dump_json(reference), encoding="utf-8", newline=""
    )
    study = read(valid_study)
    assert (study.reference.sid, study.reference.doi) == (
        "10.1234/abc.def",
        "10.1234/ABC.Def",
    )


def test_reference_sid_follows_study_json_not_the_enriched_snapshot(valid_study):
    # study.json names the publication; a PubMed ID found later in the snapshot
    # does not change the identifier of a study that names its DOI.
    data = study_json(valid_study)
    data["reference"] = {"doi": "10.1234/abc"}
    (valid_study / "study.json").write_text(
        dump_json(data), encoding="utf-8", newline=""
    )
    reference = {"sid": "10.1234/abc", "name": "Example", "doi": "10.1234/abc"}
    reference["pmid"] = "123"
    (valid_study / "reference.json").write_text(
        dump_json(reference), encoding="utf-8", newline=""
    )
    study = read(valid_study)
    assert (study.reference.sid, study.reference.pmid) == ("10.1234/abc", "123")


def test_manual_reference_keeps_its_sid(valid_study):
    data = study_json(valid_study)
    del data["reference"]
    (valid_study / "study.json").write_text(
        dump_json(data), encoding="utf-8", newline=""
    )
    reference = {"sid": "Smith2020", "name": "Example", "pmid": "123"}
    (valid_study / "reference.json").write_text(
        dump_json(reference), encoding="utf-8", newline=""
    )
    assert read(valid_study).reference.sid == "Smith2020"


def test_refused_reference_is_reported_at_its_file(valid_study, sf_vocabulary):
    doi = "10.1234/" + "a" * 300
    data = study_json(valid_study)
    data["reference"] = {"doi": doi}
    (valid_study / "study.json").write_text(
        dump_json(data), encoding="utf-8", newline=""
    )
    reference = {"sid": "x", "name": "Example", "doi": doi}
    (valid_study / "reference.json").write_text(
        dump_json(reference), encoding="utf-8", newline=""
    )
    with pytest.raises(StudyValidationError) as error:
        prepare_folder(valid_study, sf_vocabulary)
    [issue] = error.value.report.issues
    assert (issue.code, issue.field) == ("string_too_long", "sid")
    assert issue.source == SourceLocation(file="reference.json")


def test_subjects_become_groups_and_individuals(valid_study):
    study = read(valid_study)
    [group] = study.groups
    assert (group.key, group.name, group.count, group.parent) == ("all", "all", 2, None)
    assert group.image == "Example_Tab1.png"
    assert [(i.key, i.name, i.group, i.image) for i in study.individuals] == [
        ("S1", "S1", "all", "Example_TabA.png"),
        ("S2", "S2", "all", "Example_TabA.png"),
    ]
    assert [
        (c.key, c.measurement_type, c.choice, c.image) for c in group.characteristica
    ] == [
        ("characteristica.tsv:2", "healthy", "Y", "Example_Tab1.png"),
        ("characteristica.tsv:3", "sex", "M", "Example_Tab1.png"),
        ("characteristica.tsv:4", "species", "Homo sapiens", "Example_Tab1.png"),
    ]
    [age] = study.individuals[0].characteristica
    assert (age.key, age.measurement_type, age.unit) == (
        "characteristica.tsv:5",
        "age",
        "yr",
    )
    assert age.statistics == Statistics(mean=30.0)


def test_group_without_count_and_characteristic_context(valid_study, tsv):
    write(
        valid_study,
        "subjects.tsv",
        tsv(
            "subjects",
            {"name": "all", "count": "2", "source": "Tab1"},
            {"name": "S1", "parent": "all", "count": "1", "source": "TabA"},
            {"name": "S2", "parent": "all", "count": "1", "source": "TabA"},
            {"name": "unknown", "parent": "all", "comment": "Count not given."},
        ),
    )
    write(
        valid_study,
        "characteristica.tsv",
        tsv(
            "characteristica",
            {
                "source": "Text",
                "subjects": "unknown",
                "measurement": "concentration",
                "substance": "drug",
                "tissue": "plasma",
                "method": "HPLC",
                "time": "NR",
                "time_unit": "NR",
                "count": "5",
                "mean": "1.5",
                "cv": "12.5",
                "unit": "mg/l",
                "comment": "Baseline.",
            },
        ),
    )
    study = read(valid_study)
    unknown = next(group for group in study.groups if group.name == "unknown")
    assert (unknown.count, unknown.parent, unknown.image) == (None, "all", None)
    assert unknown.comments == [Comment(text="Count not given.")]
    [baseline] = unknown.characteristica
    assert (baseline.tissue, baseline.method, baseline.image) == (
        "plasma",
        "HPLC",
        None,
    )
    assert (baseline.time, baseline.time_unit) == (None, None)
    assert baseline.time_not_reported and baseline.time_unit_not_reported
    assert baseline.statistics == Statistics(mean=1.5, cv=0.125, count=5)
    assert baseline.comments == [Comment(text="Baseline.")]


def test_interventions_carry_schedules_context_and_statistics(valid_study, tsv):
    write(
        valid_study,
        "interventions.tsv",
        tsv(
            "interventions",
            {**DOSE, "name": "D1", "time": "0", "mean": "100"},
            {
                **DOSE,
                "name": "D2",
                "time": "0;12;40",
                "mean": "1.5",
                "sd": "0.2",
                "cv": "10",
                "unit": "mg/kg",
                "subjects": "all",
            },
            {
                **DOSE,
                "source": "Tab1",
                "name": "D3",
                "application": "multiple dose",
                "time": "0",
                "interval": "24",
                "doses": "7",
                "mean": "50",
                "tissue": "plasma",
                "method": "HPLC",
            },
            {
                **DOSE,
                "name": "D4",
                "application": "constant infusion",
                "time": "NR",
                "time_end": "2",
                "time_unit": "NR",
                "mean": "10",
            },
            {
                "source": "Text",
                "name": "fasted",
                "measurement": "fasting",
                "choice": "Y",
                "comment": "Overnight.",
            },
        ),
    )
    interventions = by_key(read(valid_study).interventions)
    assert set(interventions) == {"D1", "D2", "D3", "D4", "fasted"}
    one = interventions["D1"]
    assert (one.name, one.measurement_type, one.substance) == ("D1", "dosing", "drug")
    assert (one.route, one.form, one.application) == ("oral", "tablet", "single dose")
    assert (one.time, one.time_unit, one.unit, one.image) == (0.0, "h", "mg", None)
    assert one.statistics == Statistics(mean=100.0)
    listed = interventions["D2"]
    assert (listed.time, listed.interval, listed.doses) == (
        [0.0, 12.0, 40.0],
        None,
        None,
    )
    assert listed.subject == "all"
    assert listed.statistics == Statistics(mean=1.5, sd=0.2, cv=0.1)
    repeated = interventions["D3"]
    assert (repeated.time, repeated.interval, repeated.doses) == (0.0, 24.0, 7)
    assert (repeated.tissue, repeated.method) == ("plasma", "HPLC")
    assert repeated.image == "Example_Tab1.png"
    infusion = interventions["D4"]
    assert (infusion.time, infusion.time_end, infusion.time_unit) == (None, 2.0, None)
    assert infusion.time_not_reported and infusion.time_unit_not_reported
    fasted = interventions["fasted"]
    assert (fasted.measurement_type, fasted.choice, fasted.unit) == (
        "fasting",
        "Y",
        None,
    )
    assert fasted.comments == [Comment(text="Overnight.")]


def test_outputs_carry_subjects_interventions_and_all_statistics(valid_study, tsv):
    write(
        valid_study,
        "outputs_Tab2.tsv",
        tsv(
            "outputs",
            {
                **CMAX,
                "calculation": "sample mean",
                "time": "NR",
                "time_unit": "h",
                "count": "2",
                "se": "0.35",
                "cv": "20",
                "gmean": "2.4",
                "gsd": "1.2",
                "gcv": "18",
                "median": "2.5",
                "min": "2",
                "max": "3",
                "comment": "Table 2.",
            },
            {
                **CMAX,
                "subjects": "S1",
                "sd": "",
                "mean": "2",
                "error_bar": "2.6",
                "error_type": "sd",
            },
        ),
    )
    outputs = by_key(read(valid_study).measurements)
    group = outputs["outputs_Tab2.tsv:2"]
    assert (group.group, group.individual, group.interventions) == ("all", None, ["D1"])
    assert (group.output_type, group.label, group.series_key) == ("output", None, None)
    assert (group.tissue, group.method, group.image) == (
        "plasma",
        None,
        "Example_Tab2.png",
    )
    assert (group.time, group.time_unit, group.time_not_reported) == (None, "h", True)
    assert not group.time_unit_not_reported
    assert group.calculation_type == "sample mean"
    assert group.statistics == Statistics(
        count=2,
        mean=2.5,
        sd=0.5,
        se=0.35,
        cv=0.2,
        gmean=2.4,
        gsd=1.2,
        gcv=0.18,
        median=2.5,
        min=2.0,
        max=3.0,
    )
    assert group.comments == [Comment(text="Table 2.")]
    individual = outputs["outputs_Tab2.tsv:3"]
    assert (individual.group, individual.individual) == (None, "S1")
    assert individual.statistics == Statistics(mean=2.0, error_bar=2.6, error_type="sd")


def test_timecourse_points_keep_their_label(valid_study):
    points = [
        m for m in read(valid_study).measurements if m.output_type == "timecourse"
    ]
    assert [(p.key, p.time, p.statistics.mean) for p in points] == [
        ("timecourses_Fig1.tsv:2", 0.0, 0.0),
        ("timecourses_Fig1.tsv:3", 1.0, 2.0),
        ("timecourses_Fig1.tsv:4", 2.0, 1.0),
    ]
    for point in points:
        assert point.label == "drug_plasma"
        assert point.series_key == "timecourses_Fig1.tsv:drug_plasma"
        assert (point.group, point.interventions) == ("all", ["D1"])
        assert (point.substance, point.tissue, point.unit) == ("drug", "plasma", "mg/l")
        assert (point.time_unit, point.image) == ("h", "Example_Fig1.png")


def test_scatter_rows_become_paired_measurements_and_a_dataset(valid_study):
    study = read(valid_study)
    measurements = by_key(study.measurements)
    x = measurements["scatters_Fig2.tsv:2:x"]
    y = measurements["scatters_Fig2.tsv:2:y"]
    assert (x.label, x.individual, x.interventions) == ("age_vs_cmax_x", "S1", [])
    assert (x.measurement_type, x.statistics, x.unit) == (
        "age",
        Statistics(mean=30.0),
        "yr",
    )
    assert (y.label, y.individual, y.interventions) == ("age_vs_cmax_y", "S1", ["D1"])
    assert (y.measurement_type, y.substance, y.tissue) == ("cmax", "drug", "plasma")
    assert (y.statistics, y.unit, y.image) == (
        Statistics(mean=2.0),
        "mg/l",
        "Example_Fig2.png",
    )
    assert measurements["scatters_Fig2.tsv:3:y"].individual == "S2"
    [dataset] = study.scatters
    assert (dataset.key, dataset.name, dataset.data_type) == (
        "scatters_Fig2.tsv:age_vs_cmax",
        "age_vs_cmax",
        "scatter",
    )
    assert dataset.image == "Example_Fig2.png"
    assert dataset.subsets == [
        Subset(
            name="age_vs_cmax",
            dimensions=[
                Dimension(dimension="0", output="age_vs_cmax_x"),
                Dimension(dimension="1", output="age_vs_cmax_y"),
            ],
            shared=["individual"],
        )
    ]


def test_scatter_of_groups_pairs_by_group(valid_study, tsv):
    point = {
        "name": "groups",
        "subjects": "all",
        "x_measurement": "age",
        "x_mean": "35",
        "x_unit": "yr",
        "y_interventions": "D1",
        "y_measurement": "cmax",
        "y_mean": "2.5",
        "y_unit": "mg/l",
    }
    write(valid_study, "scatters_Fig2.tsv", tsv("scatters", point))
    study = read(valid_study)
    assert study.scatters[0].subsets[0].shared == ["group"]
    assert by_key(study.measurements)["scatters_Fig2.tsv:2:y"].group == "all"


def test_source_locations_point_to_rows_and_cells(valid_study):
    study = read(valid_study)
    output = by_key(study.measurements)["outputs_Tab2.tsv:2"]
    source = output.source
    assert source == SourceLocation(
        file="outputs_Tab2.tsv", sheet="outputs_Tab2", row=2
    )
    assert source.for_header("mean") == SourceLocation(
        file="outputs_Tab2.tsv",
        sheet="outputs_Tab2",
        row=2,
        column="N",
        cell="N2",
        header="mean",
    )
    assert source.for_field("measurement_type").cell == "E2"
    assert source.for_field("group").header == "subjects"
    assert source.for_field("unknown") is source
    scatter = by_key(study.measurements)
    assert scatter["scatters_Fig2.tsv:3:x"].source.for_field("mean").cell == "L3"
    assert scatter["scatters_Fig2.tsv:3:y"].source.for_field("mean").cell == "U3"
    assert scatter["scatters_Fig2.tsv:3:y"].source.for_field("individual").cell == "D3"
    individual = study.individuals[1]
    assert individual.source.for_field("group").cell == "C4"
    characteristic = study.individuals[0].characteristica[0]
    assert characteristic.source.for_field("mean").cell == "M5"
    assert study.interventions[0].source.for_field("time").cell == "N2"
    assert study.scatters[0].source.for_field("name").cell == "C2"


def test_attachments_and_digest_cover_every_other_file(valid_study):
    (valid_study / "Example.xlsx").write_bytes(b"generated workbook")
    study = read(valid_study)
    names = [attachment.name for attachment in study.attachments]
    assert "study.json" not in names and "reference.json" not in names
    assert "Example.xlsx" not in names
    assert {"review.json", "subjects.tsv", "Example.pdf", "Example_Fig2.png"} <= set(
        names
    )
    attachments, digest = attachments_and_digest(
        load_json((valid_study / "study.json").read_bytes()),
        load_json((valid_study / "reference.json").read_bytes()),
        {name: valid_study / name for name in names},
    )
    assert [a.model_dump() for a in study.attachments] == attachments
    assert study.source_digest == digest
    (valid_study / "Example.pdf").write_bytes(b"%PDF-1.7")
    assert read(valid_study).source_digest != digest


def test_reading_does_not_change_the_loaded_study(valid_study):
    loaded = load_study(valid_study)
    before = deepcopy(loaded.tables)
    read_study(loaded)
    assert loaded.tables == before


def test_prepare_folder_runs_the_server_stages(valid_study, sf_vocabulary):
    prepared = prepare_folder(valid_study, sf_vocabulary)
    assert prepared.report.valid and prepared.report.issues == []
    assert prepared.processing_version == PROCESSING_VERSION
    assert prepared.vocabulary_version == sf_vocabulary.version
    study = prepared.study
    assert study.sid == "caffeine/Example"
    labels = {
        tuple(point.label for point in course.points) for course in study.timecourses
    }
    assert ("drug_plasma",) * 3 in labels
    scatter = next(record for record in study.scatters if record.name == "age_vs_cmax")
    assert scatter.subsets[0].points == [
        ["scatters_Fig2.tsv:2:x:normalized", "scatters_Fig2.tsv:2:y:normalized"],
        ["scatters_Fig2.tsv:3:x:normalized", "scatters_Fig2.tsv:3:y:normalized"],
    ]
    assert any(m.calculated for m in study.measurements)


def test_prepare_folder_reports_layers_one_to_five(valid_study, tsv, sf_vocabulary):
    (valid_study / "outputs_Tab2.tsv").write_text(
        tsv("outputs", {**CMAX, "subjects": "S9"}), encoding="utf-8", newline=""
    )
    with pytest.raises(StudyValidationError) as error:
        prepare_folder(valid_study, sf_vocabulary)
    assert {issue.code for issue in error.value.report.issues} == {
        "not_formatted",
        "unknown_reference",
    }


def test_prepare_folder_keeps_warnings_of_every_layer(valid_study, tsv, sf_vocabulary):
    write(
        valid_study,
        "outputs_Tab2.tsv",
        tsv("outputs", {**CMAX, "se": "1"}, {**CMAX, "mean": "3"}),
    )
    report = prepare_folder(valid_study, sf_vocabulary).report
    assert report.valid
    assert sorted(
        (issue.code, issue.source and issue.source.row) for issue in report.issues
    ) == [
        ("duplicate_observation", 3),
        ("inconsistent_statistics", 2),
    ]


def test_prepare_folder_reports_postprocessing_errors_at_their_cell(
    valid_study, tsv, sf_vocabulary
):
    row = {**CMAX, "subjects": "S1", "sd": "", "error_bar": "3", "error_type": "sd"}
    write(valid_study, "outputs_Tab2.tsv", tsv("outputs", row))
    with pytest.raises(StudyValidationError) as error:
        prepare_folder(valid_study, sf_vocabulary)
    [issue] = error.value.report.issues
    assert issue.code == "individual_statistics"
    assert issue.source == SourceLocation(
        file="outputs_Tab2.tsv",
        sheet="outputs_Tab2",
        row=2,
        column="Y",
        cell="Y2",
        header="error_bar",
    )


def test_prepare_folder_limits(valid_study, sf_vocabulary):
    for limits, code in (
        ({"max_rows": 5}, "row_limit"),
        ({"max_files": 3}, "file_limit"),
    ):
        with pytest.raises(StudyValidationError) as error:
            prepare_folder(valid_study, sf_vocabulary, **limits)
        assert [issue.code for issue in error.value.report.issues] == [code]


def test_over_long_names_are_reported_at_their_cell(valid_study, tsv, sf_vocabulary):
    name = "s" * 600
    write(
        valid_study,
        "scatters_Fig2.tsv",
        tsv(
            "scatters",
            {
                "name": name,
                "subjects": "S1",
                "x_measurement": "age",
                "x_mean": "30",
                "x_unit": "yr",
                "y_interventions": "D1",
                "y_measurement": "cmax",
                "y_mean": "2",
                "y_unit": "mg/l",
            },
        ),
    )
    with pytest.raises(StudyValidationError) as error:
        prepare_folder(valid_study, sf_vocabulary)
    issue = error.value.report.issues[0]
    assert issue.code == "string_too_long"
    assert issue.source is not None
    assert (issue.source.file, issue.source.row) == ("scatters_Fig2.tsv", 2)
