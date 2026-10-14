"""The documents of the study page that the curation app and the website share (#963)."""

import json
import shutil
from pathlib import Path

import pytest

from pkdb.curation.engine import CurationEngine
from pkdb.curation.metadata import profile
from pkdb.studyformat.load import load_study
from pkdb.studyformat.models import StudyMetadata
from pkdb.studyformat.views import (
    DOCUMENT_KEYS,
    for_audience,
    people,
    row_view,
    source_document,
    study_view,
    table_view,
)

FIXTURE = Path(__file__).resolve().parents[2] / "tools" / "curation_testing" / "fixture"
DEMO = "caffeine/Demo2020"


def plain(value):
    """A document as JSON gives it back: lists for tuples."""
    return json.loads(json.dumps(value))


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "workspace"
    shutil.copytree(FIXTURE, root)
    return root


@pytest.fixture
def engine(workspace, tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    engine = CurationEngine(workspace, state_dir=state, offline=True, start=False)
    engine.user = "curator"
    yield engine
    engine.close()


def test_study_view_has_the_content_of_the_study_page(workspace):
    folder = workspace / DEMO
    view = plain(study_view(folder, load_study(folder)))
    assert set(view) == {
        "summary",
        "metadata",
        "review",
        "reference",
        "reference_match",
        "acknowledged",
        "sources",
        "files",
        "papers",
        "tables",
        "table_kinds",
        "targets",
        "name_lines",
        "substances",
    }
    assert view["metadata"]["curators"] == [{"user": "curator", "rating": 4}]
    assert view["review"]["status"] == "in_review"
    assert view["papers"] == ["Demo2020.pdf"]
    assert "caffeine" in [name.casefold() for name in view["substances"]]
    assert {entry["kind"] for entry in view["tables"]} >= {"subjects", "raw"}


def test_the_local_study_page_is_built_from_the_same_documents(workspace, engine):
    folder = workspace / DEMO
    study = load_study(folder)
    view = plain(study_view(folder, study))
    detail = engine.study_detail(DEMO)
    for key in ("tables", "table_kinds", "targets", "name_lines", "acknowledged"):
        assert plain(detail[key]) == view[key], key
    assert detail["metadata"]["value"] == view["metadata"]
    assert detail["review"]["value"] == view["review"]
    assert detail["reference"] == view["reference"]
    assert detail["reference_match"] == view["reference_match"]
    assert detail["summary"] == view["summary"]
    assert [p["file"] for p in detail["papers"]] == view["papers"]
    assert (
        plain(
            [
                {key: value for key, value in source.items() if key != "image_url"}
                for source in detail["sources"]
            ]
        )
        == view["sources"]
    )
    assert detail["people"] == people(view["metadata"], view["summary"], profile)


def test_the_local_tables_and_sources_are_the_library_documents(workspace, engine):
    folder = workspace / DEMO
    study = load_study(folder)
    for entry in plain(study_view(folder, study))["tables"]:
        assert engine.study_table(DEMO, entry["file"]) == table_view(
            study, entry["file"]
        )
    for source in plain(study_view(folder, study))["sources"]:
        local = engine.study_source(DEMO, source["source"])
        local.pop("image_url")
        assert plain(local) == plain(source_document(study, source["source"]))


def test_missing_tables_and_sources_have_no_document(workspace):
    study = load_study(workspace / DEMO)
    assert table_view(study, "nothing.tsv") is None
    assert source_document(study, "Fig99") is None


def test_row_view_names_summary_substances_and_warnings(workspace):
    folder = workspace / DEMO
    view = plain(study_view(folder, load_study(folder)))
    assert row_view(view, warnings=3) == {
        "summary": view["summary"],
        "substances": view["substances"],
        "warnings": 3,
    }


@pytest.fixture
def documents(workspace):
    folder = workspace / DEMO
    study = load_study(folder)
    view = plain(study_view(folder, study))
    return study, view


def test_curators_see_every_document_unchanged(documents):
    _, view = documents
    assert for_audience("study", view, "curator") is view


def test_the_public_study_page_has_no_curation(documents):
    _, view = documents
    page = for_audience("study", view, "public")
    assert page is not None
    assert set(page) == set(view)
    assert page["review"] is None
    assert page["acknowledged"] == []
    assert page["targets"] == {}
    assert page["files"] == []
    assert page["papers"] == []
    assert "issue" not in page["metadata"]
    assert all(set(c) == {"user"} for c in page["metadata"]["curators"])
    assert set(page["summary"]) & {"review_status", "open_items", "issue"} == set()
    assert page["summary"]["provenance"] == {
        "kind": view["summary"]["provenance"]["kind"]
    }
    assert all(entry["kind"] != "raw" for entry in page["tables"])
    raw = {entry["file"] for entry in view["tables"] if entry["kind"] == "raw"}
    for source in page["sources"]:
        assert source["image"] is None
        assert source["raw"] is None
        assert source["raw_kind"] is None
        assert source["missing_image"] is None
        assert source["missing_raw"] is None
        assert not set(source["tables"]) & raw
    # The input stays as it was.
    assert view["review"] is not None


def test_the_public_has_no_raw_table(documents):
    study, view = documents
    [raw] = [entry["file"] for entry in view["tables"] if entry["kind"] == "raw"][:1]
    assert for_audience("table", plain(table_view(study, raw)), "public") is None
    table = plain(table_view(study, "subjects.tsv"))
    assert for_audience("table", table, "public") == table


def test_the_public_source_shows_the_plot_without_the_figure(documents):
    study, view = documents
    figure = next(s["source"] for s in view["sources"] if s["image"])
    document = plain(source_document(study, figure))
    public = for_audience("source", document, "public")
    assert public is not None
    assert public["image"] is None
    assert public["image_size"] is None
    assert public["raw_grid"] is None
    assert public["digitization"] is None
    assert public["overlay"] == []
    assert public["unmatched"] == []
    assert public["layout"] == "side_by_side"
    assert public["points"] == document["points"]
    assert public["series"] == document["series"]
    assert all(table["kind"] != "raw" for table in public["mapped"])


def test_the_public_row_has_no_review_and_no_warnings(documents):
    _, view = documents
    row = for_audience("row", row_view(view, warnings=2), "public")
    assert row is not None
    assert row["warnings"] == 0
    assert set(row["summary"]) & {"review_status", "open_items", "issue"} == set()
    assert row["substances"] == view["substances"]


def test_the_public_keeps_only_the_listed_keys(documents):
    study, view = documents
    new = {"future_curation_field": 1}
    extra = {
        **view,
        **new,
        "summary": {**view["summary"], **new},
        "metadata": {**view["metadata"], **new},
        "sources": [{**source, **new} for source in view["sources"]],
    }
    page = for_audience("study", extra, "public")
    assert page is not None
    assert "future_curation_field" not in page
    assert "future_curation_field" not in page["summary"]
    assert "future_curation_field" not in page["metadata"]
    assert all("future_curation_field" not in s for s in page["sources"])
    row = for_audience("row", {**row_view(view, warnings=1), **new}, "public")
    assert row is not None and "future_curation_field" not in row
    table = for_audience(
        "table", {**plain(table_view(study, "subjects.tsv")), **new}, "public"
    )
    assert table is not None and "future_curation_field" not in table
    source = for_audience(
        "source", {**plain(source_document(study, "Fig1")), **new}, "public"
    )
    assert source is not None and "future_curation_field" not in source


def emitted(study, view, name):
    """The documents of the fixture study that the builders emit under `name`."""
    return {
        "study": [view],
        "summary": [view["summary"]],
        "metadata": [view["metadata"]],
        "study_source": view["sources"],
        "row": [row_view(view, warnings=1)],
        "table": [plain(table_view(study, entry["file"])) for entry in view["tables"]],
        "source": [
            plain(source_document(study, source["source"]))
            for source in view["sources"]
        ],
    }[name]


@pytest.mark.parametrize(
    "name",
    ["study", "summary", "metadata", "study_source", "row", "table", "source"],
)
def test_every_key_is_either_public_or_curation(documents, name):
    """A new key of a builder fails here until it is classified for the public."""
    study, view = documents
    keys = DOCUMENT_KEYS[name]
    found = {key for document in emitted(study, view, name) for key in document}
    if name == "metadata":
        # study.json leaves out what it does not state; the model names every key.
        found |= set(StudyMetadata.model_fields)
    assert not set(keys.public) & keys.curation
    assert found == set(keys.public) | keys.curation


@pytest.mark.parametrize("name", ["study", "study_source", "row", "source"])
def test_the_public_documents_have_the_keys_of_the_stored_ones(documents, name):
    study, view = documents
    page = for_audience("study", view, "public")
    assert page is not None
    for document in emitted(study, view, name):
        if name == "study_source":
            public = next(
                source
                for source in page["sources"]
                if source["source"] == document["source"]
            )
        else:
            public = for_audience(name, document, "public")
        assert public is not None
        assert list(public) == list(document)
        for key, neutral in DOCUMENT_KEYS[name].neutral.items():
            assert public[key] == neutral, key


def test_the_public_plot_has_only_the_plotted_series(documents):
    study, _ = documents
    document = plain(source_document(study, "Fig1"))
    digitized = {
        "name": "digitized_only",
        "color": "#000000",
        "dark_color": "#ffffff",
        "x_label": None,
        "y_label": None,
    }
    extra = {**document, "series": [*document["series"], digitized]}
    public = for_audience("source", extra, "public")
    assert public is not None
    plotted = {point["series"] for point in document["points"]}
    assert plotted
    assert [series["name"] for series in public["series"]] == [
        series["name"] for series in document["series"]
    ]
    assert {series["name"] for series in public["series"]} == plotted
    # The curators see the digitized series too.
    assert for_audience("source", extra, "curator") == extra
