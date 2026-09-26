import json

import openpyxl
import pytest
from pydantic import TypeAdapter, ValidationError

from pkdb.domain.vocabulary import Vocabulary
from pkdb.importers.osp.workbook import identity, import_workbook, statistics
from pkdb.preparation import prepare
from pkdb.schemas.provenance import ManualCuration, StudyProvenance


def test_acquisition_discriminator():
    adapter = TypeAdapter(StudyProvenance)
    assert isinstance(
        adapter.validate_python({"kind": "manual_curation"}), ManualCuration
    )
    with pytest.raises(ValidationError):
        adapter.validate_python({"kind": "data_import", "source_key": "osp"})
    with pytest.raises(ValidationError):
        adapter.validate_python({"kind": "manual_curation", "source_key": ""})
    auto = adapter.validate_python(
        dict(
            kind="automatic_curation",
            source_key="extractor",
            method="literature extraction",
            version="1",
            run_id="run1",
            assets=[dict(url="https://example.org/paper", sha256="0" * 64)],
        )
    )
    assert auto.kind == "automatic_curation"


def test_statistics_do_not_invent_arithmetic_errors_or_individual_means():
    warnings = []
    assert statistics(
        10, "geom. Mean", 20, "%", "geomCV", "mg/l", False, warnings, {}
    ) == {"mean": 10.0, "calculation_type": "geometric mean"}
    assert warnings[-1]["code"] == "uncertainty_retained_in_source"
    assert statistics(10, "mean", None, None, None, "mg/l", True, warnings, {}) is None
    assert statistics(10, None, None, None, None, "mg/l", False, warnings, {}) is None


def test_release_checksum_is_mandatory(tmp_path):
    path = tmp_path / "wrong.xlsx"
    path.write_bytes(b"not the release")
    with pytest.raises(ValueError, match="checksum"):
        import_workbook(path, tmp_path / "out", creator="curator")


def test_workbook_preserves_rows_groups_publications_and_validates(tmp_path):
    book = openpyxl.Workbook()
    book.remove(book.active)
    widths = {
        "Studies": 71,
        "PK-Profiles": 16,
        "PK-Parameter": 30,
        "DDI": 50,
        "Analyte": 2,
        "Projects": 2,
    }
    for name, width in widths.items():
        sheet = book.create_sheet(name)
        if name == "Studies":
            sheet.append(["source title"])
        sheet.append([f"column{i}" for i in range(width)])
    for identifier, ref in [
        ("A", "https://pubmed.ncbi.nlm.nih.gov/12345/"),
        ("B", "https://www.ncbi.nlm.nih.gov/pubmed/12345"),
    ]:
        row = [None] * 71
        for i, value in {
            0: identifier,
            1: "Example 2000",
            2: ref,
            4: "caffeine",
            5: "plasma",
            6: "Aggregated",
            25: "Human",
        }.items():
            row[i] = value
        book["Studies"].append(row)
    for time in [0, 1]:
        book["PK-Profiles"].append(
            [
                "A",
                "Example 2000",
                "https://pubmed.ncbi.nlm.nih.gov/12345/",
                None,
                "caffeine",
                "plasma",
                time,
                "h",
                time + 1,
                "mg/l",
                "arith. Mean",
                None,
                None,
                None,
                None,
                "original note",
            ]
        )
    book["Analyte"].append(["caffeine", 194.19])
    book["Projects"].append(["A", "Original project"])
    path = tmp_path / "fixture.xlsx"
    book.save(path)
    book.close()
    output = tmp_path / "out"
    report = import_workbook(path, output, creator="curator", verify=False)
    assert report["study_count"] == 1
    assert report["mapped_measurements"]["PK-Profiles"] == 2
    folder = next((output / "studies").iterdir())
    prepared = prepare(folder, vocabulary=Vocabulary.load(output / "vocabulary.json"))
    assert prepared.study.reference.pmid == "12345"
    assert len(prepared.study.groups) == 2
    assert all(g.count is None for g in prepared.study.groups)
    assert prepared.study.metadata.provenance.kind == "data_import"
    raw = json.loads((folder / "osp-source.json").read_text())
    assert raw["records"]["PK-Profiles"][0]["values"][-1] == "original note"
    assert len(raw["records"]["Studies"]) == 2
    assert identity("https://doi.org/10.1234/ABC", "example")[0] == "doi:10.1234/abc"
    with pytest.raises(ValueError, match="empty"):
        import_workbook(path, output, creator="curator", verify=False)


def test_geometric_uncertainty_is_not_completed_as_arithmetic(study_folder, vocabulary):
    path = study_folder / "study.json"
    data = json.loads(path.read_text())
    data["outputset"]["outputs"][0].update(calculation_type="geometric mean", se=1)
    path.write_text(json.dumps(data))
    vocabulary = vocabulary.model_copy(
        update={"calculation_types": ("geometric mean",)}
    )
    result = prepare(study_folder, vocabulary=vocabulary)
    normalized = [m for m in result.study.measurements if m.origin == "normalized"]
    assert normalized
    assert all(m.statistics.sd is None and m.statistics.cv is None for m in normalized)
