import pytest
from PIL import Image

from pkdb.migration.model import NotConverted
from pkdb.migration.sources import (
    copy_images,
    curator_source,
    image_source,
    observation_source,
    sheet_of,
)
from pkdb.schemas.source import SourceLocation

WORKBOOK = SourceLocation(file="Example.xlsx", sheet="Fig1", row=3)
HIDDEN = SourceLocation(file=".Example_Tab2.tsv", row=3)
PLAIN = SourceLocation(file="Results.tsv", row=3)
INLINE = SourceLocation(file="study.json", path=("outputset", "outputs", 0))


def test_the_sheet_of_a_row():
    assert sheet_of(WORKBOOK, "Example") == "Fig1"
    assert sheet_of(HIDDEN, "Example") == "Tab2"
    assert sheet_of(PLAIN, "Example") == "Results"
    assert sheet_of(INLINE, "Example") is None


def test_the_source_of_an_image():
    assert image_source("Example_Fig1.png", "Example") == "Fig1"
    assert image_source("Example_TabS1.jpg", "Example") == "TabS1"
    assert image_source("Other_Fig1.png", "Example") is None
    assert image_source(None, "Example") is None


def test_observation_rows_take_the_sheet_or_the_image_or_text():
    assert observation_source(WORKBOOK, None, "Example") == "Fig1"
    assert observation_source(INLINE, "Example_Fig3.png", "Example") == "Fig3"
    assert observation_source(INLINE, None, "Example") == "Text"


def test_a_sheet_outside_the_source_pattern_refuses_the_study():
    with pytest.raises(NotConverted) as error:
        observation_source(PLAIN, None, "Example")
    assert error.value.code == "sheet_name"
    assert "Results" in error.value.message


def test_an_inline_image_outside_the_naming_refuses_the_study():
    with pytest.raises(NotConverted) as error:
        observation_source(INLINE, "figure.png", "Example")
    assert error.value.code == "image_name"


def test_curator_sources_fall_back_to_the_image_then_empty():
    groups = SourceLocation(file="Example.xlsx", sheet="Groups", row=3)
    assert curator_source(groups, "Example_Tab1.png", "Example") == "Tab1"
    assert curator_source(groups, None, "Example") == ""
    assert curator_source(WORKBOOK, None, "Example") == "Fig1"
    assert curator_source(INLINE, None, "Example") == "Text"


def test_images_are_copied_and_jpg_becomes_png(tmp_path):
    v1, target = tmp_path / "v1", tmp_path / "v2"
    v1.mkdir()
    target.mkdir()
    (v1 / "Example_Fig1.png").write_bytes(b"\x89PNG data")
    Image.new("RGB", (4, 3), "red").save(v1 / "Example_Tab1.jpg")
    decisions = copy_images(v1, target, "Example", {"Fig1", "Tab1", "Text"})
    assert (target / "Example_Fig1.png").read_bytes() == b"\x89PNG data"
    with Image.open(target / "Example_Tab1.png") as image:
        assert (image.format, image.size) == ("PNG", (4, 3))
    assert [(d.kind, d.detail) for d in decisions] == [
        ("image_converted", "Example_Tab1.jpg to Example_Tab1.png")
    ]


def test_a_missing_or_unsupported_image_refuses_the_study(tmp_path):
    v1, target = tmp_path / "v1", tmp_path / "v2"
    v1.mkdir()
    target.mkdir()
    with pytest.raises(NotConverted) as missing:
        copy_images(v1, target, "Example", {"Fig1"})
    assert missing.value.code == "missing_image"
    (v1 / "Example_Fig1.svg").write_text("<svg/>")
    with pytest.raises(NotConverted) as unsupported:
        copy_images(v1, target, "Example", {"Fig1"})
    assert unsupported.value.code == "image_type"


def test_a_cmyk_jpg_is_converted_to_png(tmp_path):
    v1, target = tmp_path / "v1", tmp_path / "v2"
    v1.mkdir()
    target.mkdir()
    Image.new("CMYK", (4, 3)).save(v1 / "Example_Fig1.jpg")
    copy_images(v1, target, "Example", {"Fig1"})
    with Image.open(target / "Example_Fig1.png") as image:
        assert (image.format, image.size) == ("PNG", (4, 3))


def test_a_corrupt_jpg_refuses_the_study(tmp_path):
    v1, target = tmp_path / "v1", tmp_path / "v2"
    v1.mkdir()
    target.mkdir()
    (v1 / "Example_Fig1.jpg").write_bytes(b"not an image")
    with pytest.raises(NotConverted) as error:
        copy_images(v1, target, "Example", {"Fig1"})
    assert error.value.code == "image_unreadable"
    assert "Example_Fig1.jpg" in error.value.message
