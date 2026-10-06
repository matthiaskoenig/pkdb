import json

from digitize_fixtures import GOOD, png, project

from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.load import load_study
from pkdb.studyformat.sources import source_view, study_sources


def test_study_sources_lists_every_source(valid_study):
    (valid_study / "Example_Tab2.tsv").write_text("cmax\t2.5 ± 0.5\n")
    summaries = {s.source: s for s in study_sources(load_study(valid_study))}
    assert list(summaries) == ["Fig1", "Fig2", "Tab1", "Tab2", "TabA", "Text"]
    assert (
        summaries["Tab2"].raw == "Example_Tab2.tsv"
        and summaries["Tab2"].raw_kind == "table"
    )
    assert summaries["Tab1"].tables == ("subjects.tsv", "characteristica.tsv")
    assert summaries["Text"].image is None


def test_table_source_view(valid_study):
    (valid_study / "Example_Tab2.tsv").write_text("cmax\t2.5 ± 0.5\n")
    view = source_view(load_study(valid_study), "Tab2")
    assert view.raw_grid == (("cmax", "2.5 ± 0.5"),)
    assert [table.file for table in view.mapped] == ["outputs_Tab2.tsv"]
    assert view.overlay == ()


def test_figure_overlay_in_pixels(make_study, valid_files):
    files = {
        **valid_files,
        "Example_Fig1.png": png(100, 100),
        "Example_Fig1.wpd.json": json.dumps(project(GOOD)),
    }
    folder = make_study(files)
    assert format_folder(folder).ok
    view = source_view(load_study(folder), "Fig1")
    assert view.image_size == (100, 100)
    mapped = [(p.px, p.py) for p in view.overlay if p.role == "mapped"]
    raw = [(p.px, p.py) for p in view.overlay if p.role == "raw"]
    assert mapped == [(0.0, 100.0), (10.0, 80.0), (20.0, 90.0)] == raw
    assert {p.line for p in view.overlay if p.role == "mapped"} == {2, 3, 4}
    assert view.unmatched == ()


def test_figure_without_digitization_lists_unmatched_series(valid_study):
    view = source_view(load_study(valid_study), "Fig1")
    assert view.digitization is None and view.unmatched == ("drug_plasma",)


def test_unknown_source_raises(valid_study):
    import pytest

    with pytest.raises(KeyError):
        source_view(load_study(valid_study), "Tab9")
