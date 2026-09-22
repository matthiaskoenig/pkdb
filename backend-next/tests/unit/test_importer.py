"""Study files must expand without losing zeros, rows, or input diagnostics."""

import json

import openpyxl
import pytest

from pkdb.importers.folder import load_folder, parse_bundle
from pkdb.schemas.validation import StudyValidationError


@pytest.fixture
def study_folder(tmp_path):
    folder = tmp_path / "Example"
    folder.mkdir()
    data = {
        "sid": "PK1",
        "name": "Example",
        "date": "2026-01-01",
        "reference": 123,
        "creator": "curator",
        "curators": [["curator", 3]],
        "access": "public",
        "licence": "open",
        "groupset": {
            "groups": [
                {"name": "all", "count": 2, "characteristica": []},
            ]
        },
        "outputset": {
            "outputs": [
                {
                    "source": "Results",
                    "output_type": "output",
                    "group": "all",
                    "measurement_type": "concentration",
                    "substance": "apixaban",
                    "mean": "col==mean",
                    "unit": "ng/ml",
                }
            ]
        },
    }
    (folder / "study.json").write_text(json.dumps(data))
    (folder / "reference.json").write_text(
        json.dumps(
            {
                "sid": 123,
                "name": "Example",
                "date": "2026-01-01",
                "authors": [],
            }
        )
    )
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Results"
    sheet.append(["Comment row", "ignored"])
    sheet.append(["id", "mean"])
    sheet.append([1, 0])
    sheet.append([2, None])
    book.save(folder / "Example.xlsx")
    return folder


def test_missing_and_zero_are_distinct(study_folder):
    before = (study_folder / "Example.xlsx").read_bytes()
    study = parse_bundle(load_folder(study_folder))
    assert [m.statistics.mean for m in study.measurements] == [0.0, None]
    assert [m.source.row for m in study.measurements if m.source is not None] == [3, 4]
    assert study.reference.sid == "123"
    assert study.metadata.curators[0].rating == 3
    assert (study_folder / "Example.xlsx").read_bytes() == before
    assert not list(study_folder.glob("*.tsv"))


def test_unknown_column_has_source_location(study_folder):
    p = study_folder / "study.json"
    data = json.loads(p.read_text())
    data["outputset"]["outputs"][0]["mean"] = "col==missing"
    p.write_text(json.dumps(data))
    with pytest.raises(StudyValidationError) as error:
        parse_bundle(load_folder(study_folder))
    assert error.value.report.issues[0].code == "unknown_column"
    assert error.value.report.issues[0].source is not None
    assert error.value.report.issues[0].source.sheet == "Results"


def test_unknown_field_is_rejected(study_folder):
    p = study_folder / "study.json"
    data = json.loads(p.read_text())
    data["unexpected"] = 123
    p.write_text(json.dumps(data))
    with pytest.raises(StudyValidationError):
        parse_bundle(load_folder(study_folder))


def test_symlink_escape_is_rejected(study_folder, tmp_path):
    secret = tmp_path / "outside.txt"
    secret.write_text("private")
    (study_folder / "Example.txt").symlink_to(secret)
    with pytest.raises(StudyValidationError):
        load_folder(study_folder)


def test_expansion_limit_is_enforced(study_folder):
    with pytest.raises(StudyValidationError) as error:
        parse_bundle(load_folder(study_folder), max_rows=1)
    assert error.value.report.issues[0].code == "row_limit"


def test_workbook_is_authoritative_over_generated_tsv(study_folder):
    (study_folder / ".Example_Results.tsv").write_text("id\tstale_column\n1\t99\n")
    study = parse_bundle(load_folder(study_folder))
    assert study.measurements[0].statistics.mean == 0


def test_unreported_time_preserves_marker(study_folder):
    path = study_folder / "study.json"
    data = json.loads(path.read_text())
    data["outputset"]["outputs"][0].update(time="NR", time_unit="NR")
    path.write_text(json.dumps(data))
    record = parse_bundle(load_folder(study_folder)).measurements[0]
    assert record.time is None
    assert record.time_not_reported is True
    assert record.time_unit is None
    assert record.time_unit_not_reported is True


def test_malformed_section_is_a_validation_error(study_folder):
    path = study_folder / "study.json"
    data = json.loads(path.read_text())
    data["groupset"] = 123
    path.write_text(json.dumps(data))
    with pytest.raises(StudyValidationError):
        parse_bundle(load_folder(study_folder))


def test_upload_cannot_claim_calculated_provenance(study_folder):
    path = study_folder / "study.json"
    data = json.loads(path.read_text())
    data["outputset"]["outputs"][0]["origin"] = "calculated"
    path.write_text(json.dumps(data))
    with pytest.raises(StudyValidationError) as error:
        parse_bundle(load_folder(study_folder))
    assert error.value.report.issues[0].code == "reserved_field"


@pytest.mark.parametrize("kind", ["xlsx", "tsv"])
def test_duplicate_source_headers_are_rejected(study_folder, kind):
    from pkdb.importers.workbook import read_table

    path = study_folder / f"duplicate.{kind}"
    if kind == "xlsx":
        book = openpyxl.Workbook()
        sheet = book.active
        sheet.title = "Results"
        sheet.append(["comments"])
        sheet.append(["mean", "mean"])
        sheet.append([1, 2])
        book.save(path)
    else:
        path.write_text("mean\tmean\n1\t2\n")
    with pytest.raises(StudyValidationError) as error:
        read_table(path, "Results" if kind == "xlsx" else None, 100)
    assert error.value.report.issues[0].code == "duplicate_column"


def test_canonical_shape_errors_report_full_count(valid_bundle):
    from copy import deepcopy

    output = valid_bundle.study["outputset"]["outputs"][0]
    valid_bundle.study["outputset"]["outputs"] = [
        dict(deepcopy(output), unknown_field=True) for _ in range(150)
    ]
    with pytest.raises(StudyValidationError) as error:
        parse_bundle(valid_bundle)
    assert error.value.report.error_count == 150
    assert len(error.value.report.issues) == 100
    assert error.value.report.truncated


def test_nonfinite_in_memory_bundle_reports_source(valid_bundle):
    valid_bundle.study["outputset"]["outputs"][0]["mean"] = float("inf")
    with pytest.raises(StudyValidationError) as error:
        parse_bundle(valid_bundle)
    issue = error.value.report.issues[0]
    assert issue.code == "invalid_number"
    assert issue.source is not None
    assert issue.source.path == ("outputset", "outputs", 0, "mean")
    assert error.value.report.error_count == 1


def test_external_characteristic_alias_preserves_values_and_source(valid_bundle):
    from copy import deepcopy

    from pkdb.importers.folder import parse_bundle

    original = parse_bundle(valid_bundle)
    changed = valid_bundle.model_copy(deep=True)
    group = changed.study["groupset"]["groups"][0]
    group["characteristica_ex"] = group.pop("characteristica")
    before = deepcopy(changed.study)
    actual = parse_bundle(changed)
    assert actual.groups == original.groups
    assert actual.source_digest != original.source_digest
    assert changed.study == before
