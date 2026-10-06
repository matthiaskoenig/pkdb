import json

import pytest

from pkdb.domain.vocabulary import Vocabulary
from pkdb.importers.datasets.common import SUMMARY, Builder
from pkdb.importers.datasets.convert import (
    cvtdb,
    cvtdb_references,
    frdb,
    import_dataset,
    warfarin,
)
from pkdb.preparation import prepare


def test_missing_optional_reader_has_install_instructions(monkeypatch):
    from pkdb.importers.datasets import convert

    def missing_reader(name):
        assert name == "rdata"
        raise ImportError("optional reader is not installed")

    monkeypatch.setattr(convert, "import_module", missing_reader)
    with pytest.raises(ValueError, match=r"pkdb\[imports\]"):
        convert.rda_rows(b"", "warfarin")


def test_r_data_frames_are_read_without_missing_values(request):
    pytest.importorskip("rdata")
    from pkdb.importers.datasets.convert import rda_rows

    payload = (request.path.parent / "data" / "example.rda").read_bytes()
    assert rda_rows(payload, "example") == [
        {"id": 1, "dose": 0.5, "sex": "F", "healthy": True, "name": "a"},
        {"id": None, "dose": None, "sex": None, "healthy": None, "name": None},
        {"id": 3, "dose": 2.0, "sex": "M", "healthy": False, "name": "c"},
    ]


def finish(builder, tmp_path):
    report = builder.write(tmp_path)
    folder = next((tmp_path / "studies").iterdir())
    result = prepare(folder, vocabulary=Vocabulary.load(tmp_path / "vocabulary.json"))
    assert result.report.valid, result.report
    study = json.loads((folder / "study.json").read_text())
    provenance = json.loads((folder / "source-records.json").read_text())
    for entry in provenance["lineage"]:
        target = study
        for token in entry["target"].strip("/").split("/"):
            target = target[int(token)] if isinstance(target, list) else target[token]
        assert target
        assert any(row["row"] == entry["source_row"] for row in provenance["records"])
    return report, study, provenance, result


def test_frdb_unknown_summary_auc_and_raw_context(tmp_path):
    rows = [
        {
            "id": "one",
            "pk_source_uri": "https://pubmed.ncbi.nlm.nih.gov/123/",
            "pk_analyte_unii": "ABC",
            "pk_analyte_pt": "Drug",
            "pk_analyte_mw": "100",
            "pk_population_size": "3-4",
            "pk_species": "Homo sapiens",
            "pk_sex": "MALE",
            "pk_cmax_value": "5",
            "pk_cmax_units": "μg/mL",
            "pk_auc_value": "10",
            "pk_auc_units": "mg*h/L",
            "pk_auc_type": "∞",
            "pk_routes": "ORAL",
        },
        {
            "id": "two",
            "pk_source_uri": "https://www.ncbi.nlm.nih.gov/pubmed/123",
            "pk_analyte_unii": "ABC",
            "pk_analyte_pt": "Drug",
            "pk_cmax_value": "<5",
            "pk_cmax_units": "mg/L",
            "pk_auc_type": "?",
            "pk_auc_value": "2",
        },
    ]
    builder = Builder("frdb", "curator")
    frdb(builder, rows)
    report, study, source, prepared = finish(builder, tmp_path)
    assert report["study_count"] == 1
    assert report["mapped_measurements"] == 2
    assert source["records"][0]["values"] == rows[0]
    assert study["groupset"]["groups"][0]["count"] is None
    assert {x["measurement_type"] for x in study["outputset"]["outputs"]} == {
        "cmax",
        "auc_inf",
    }
    assert all(x["calculation_type"] == SUMMARY for x in study["outputset"]["outputs"])
    assert prepared.study.metadata.provenance.evidence_kind == "unknown"
    assert all(
        x.statistics.mean is not None
        and x.statistics.model_dump(exclude_none=True).keys() <= {"mean", "count"}
        for x in prepared.study.measurements
    )
    assert not any(x.origin == "calculated" for x in prepared.study.measurements)
    assert report["warning_counts"]["missing_censored_or_non_numeric"] == 1


def cvt_row(**changes):
    return {
        "conc_time_id": 1,
        "fk_study_id": 1,
        "fk_subject_id": 1,
        "fk_extraction_document_id": 1,
        "pmid": 123,
        "doi": "10.1234/one",
        "fk_analyzed_chemical_id": 1,
        "analyzed_chem_name_original": "Drug",
        "time_original": "1.123456789012",
        "time_units_original": "h",
        "conc_original": "5.123456789012",
        "conc_units_original": "ug/L",
        "n_subjects_in_series": "NR",
        "species": "rat",
        "sex": "male",
        **changes,
    }


def test_cvt_censoring_precision_and_aliases(tmp_path):
    rows = [
        cvt_row(),
        cvt_row(
            conc_time_id=2, fk_extraction_document_id=2, pmid=None, conc_original="NQ"
        ),
        cvt_row(conc_time_id=3, doi=None, conc_original="ND"),
    ]
    builder = Builder("cvtdb", "curator")
    cvtdb(builder, rows)
    report, study, source, _ = finish(builder, tmp_path)
    assert report["study_count"] == 1
    assert report["mapped_measurements"] == 1
    output = study["outputset"]["outputs"][0]
    assert output["mean"] == 5.123456789012
    assert "value" not in output
    assert output["time"] == 1.123456789012
    assert source["records"][1]["values"]["conc_original"] == "NQ"
    assert report["warning_counts"]["missing_censored_or_non_numeric"] == 2
    fallback = cvtdb_references([cvt_row(pmid=None, doi=None)])
    assert fallback == [("document:1", {})]
    with pytest.raises(ValueError, match="Conflicting publication"):
        cvtdb_references([cvt_row(), cvt_row(pmid=456)])


def test_warfarin_compilation_preserves_duplicate_times_and_placeholders(tmp_path):
    base = dict(id=1, wt=66.7, age=50, sex="male", dvid="cp")
    rows = [
        {**base, "time": 0, "amt": 100, "dv": 0, "evid": 1},
        {**base, "time": 3, "amt": 0, "dv": 6, "evid": 0},
        {**base, "time": 3, "amt": 0, "dv": 7, "evid": 0},
        {**base, "time": 24, "amt": 0, "dv": 44, "evid": 0, "dvid": "pca"},
    ]
    builder = Builder("warfarin", "curator")
    warfarin(builder, rows)
    report, study, source, prepared = finish(builder, tmp_path)
    assert report["mapped_measurements"] == 3
    assert len(study["interventionset"]["interventions"]) == 1
    assert [x["mean"] for x in study["outputset"]["outputs"]] == [6, 7, 44]
    assert [x["mean"] for x in study["interventionset"]["interventions"]] == [100]
    assert prepared.study.reference.pmid is None
    assert prepared.study.reference.doi is None
    assert (
        prepared.study.reference.provenance["publication_attribution"] == "unresolved"
    )
    assert prepared.study.metadata.provenance.reference_scope == "compilation"
    assert len(source["records"]) == 4


@pytest.mark.parametrize("provider", ["frdb", "cvtdb", "warfarin"])
def test_checksum_cannot_be_bypassed(provider, tmp_path):
    artifact = tmp_path / "bad"
    artifact.write_bytes(b"not an upstream artifact")
    with pytest.raises(ValueError, match="checksum"):
        import_dataset(provider, artifact, tmp_path / "out", creator="curator")
    assert not (tmp_path / "out").exists()


def test_existing_import_is_never_overwritten(tmp_path):
    (tmp_path / "keep").write_text("existing")
    with pytest.raises(ValueError, match="new or empty"):
        Builder("frdb", "curator").write(tmp_path)
    assert (tmp_path / "keep").read_text() == "existing"


def test_conflicting_mass_is_not_arbitrarily_used_for_unit_conversion(tmp_path):
    base = {
        "pk_source_uri": "https://pubmed.ncbi.nlm.nih.gov/123",
        "pk_analyte_unii": "ABC",
        "pk_analyte_pt": "Drug",
        "pk_cmax_value": "5",
        "pk_cmax_units": "mg/L",
    }
    rows = [
        {**base, "id": "one", "pk_analyte_mw": "100"},
        {**base, "id": "two", "pk_analyte_mw": "101"},
    ]
    builder = Builder("frdb", "curator")
    frdb(builder, rows)
    report, _, source, _ = finish(builder, tmp_path)
    assert builder.substances["ABC"].mass is None
    assert (
        report["warning_counts"]["conflicting_molecular_mass_retained_in_source"] == 2
    )
    assert source["records"][0]["values"]["pk_analyte_mw"] == "100"
    assert source["records"][1]["values"]["pk_analyte_mw"] == "101"
