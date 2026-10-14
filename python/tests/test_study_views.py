"""The documents of the study page that the curation app and the website share (#963)."""

import json
import shutil
from pathlib import Path

import pytest

from pkdb.curation.engine import CurationEngine
from pkdb.curation.metadata import profile
from pkdb.studyformat.load import load_study
from pkdb.studyformat.views import (
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
