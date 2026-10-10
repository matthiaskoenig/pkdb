import io

import pytest
from migration_fixtures import tiny_png
from PIL import Image

from pkdb.migration.model import NotConverted
from pkdb.migration.sources import (
    copy_images,
    curator_source,
    image_source,
    image_sources,
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


IMAGES = frozenset({"Fig1", "Fig3", "Tab2", "figure"})


def test_observation_rows_take_their_image_then_the_sheet_or_text():
    assert observation_source(WORKBOOK, "Example_Tab2.png", "Example", IMAGES) == "Tab2"
    assert observation_source(WORKBOOK, None, "Example", IMAGES) == "Fig1"
    # An image that the folder lacks or that names no source leaves the sheet.
    assert observation_source(WORKBOOK, "Example_Fig9.png", "Example", IMAGES) == "Fig1"
    assert (
        observation_source(WORKBOOK, "Example_figure.png", "Example", IMAGES) == "Fig1"
    )
    assert observation_source(INLINE, "Example_Fig3.png", "Example", IMAGES) == "Fig3"
    assert observation_source(INLINE, None, "Example", IMAGES) == "Text"


def test_a_sheet_outside_the_source_pattern_refuses_the_study():
    with pytest.raises(NotConverted) as error:
        observation_source(PLAIN, None, "Example", IMAGES)
    assert error.value.code == "sheet_name"
    assert "Results" in error.value.message
    # The image of the row names its source instead.
    assert observation_source(PLAIN, "Example_Tab2.png", "Example", IMAGES) == "Tab2"


def test_an_inline_image_outside_the_naming_refuses_the_study():
    with pytest.raises(NotConverted) as error:
        observation_source(INLINE, "figure.png", "Example", IMAGES)
    assert error.value.code == "image_name"


def test_a_curator_sheet_is_the_source_only_when_it_has_an_image():
    sheet = SourceLocation(file="Example.xlsx", sheet="TabGroups", row=3)
    tab1 = frozenset({"Tab1"})
    assert curator_source(sheet, None, "Example", frozenset()) == "Text"
    assert curator_source(sheet, "Example_Tab1.png", "Example", tab1) == "Tab1"
    assert (
        curator_source(sheet, None, "Example", frozenset({"TabGroups"})) == "TabGroups"
    )


def test_a_curator_row_takes_an_existing_image_then_text():
    groups = SourceLocation(file="Example.xlsx", sheet="Groups", row=3)
    images = frozenset({"Groups", "Tab1"})
    assert curator_source(groups, "Example_Tab1.png", "Example", images) == "Tab1"
    assert curator_source(groups, "Example_Tab2.png", "Example", images) == "Text"
    assert curator_source(groups, None, "Example", images) == "Text"
    assert curator_source(WORKBOOK, None, "Example", frozenset({"Fig1"})) == "Fig1"
    assert curator_source(INLINE, "Example_Tab1.png", "Example", images) == "Tab1"
    assert curator_source(INLINE, "Example_Tab2.png", "Example", images) == "Text"
    assert curator_source(INLINE, None, "Example", images) == "Text"


def test_the_sources_that_have_an_image(tmp_path):
    names = ["Example_Tab1.png", "Example_Fig2.JPG", "Example_Fig3.jpeg"]
    names += ["Example_Fig4.svg", "Other_Fig5.png", "Example.pdf", "Example_.png"]
    for name in names:
        (tmp_path / name).write_bytes(b"")
    (tmp_path / "Example_Fig6.png").mkdir()
    assert image_sources(tmp_path, "Example") == {"Tab1", "Fig2", "Fig3"}


def test_images_are_copied_and_jpg_becomes_png(tmp_path):
    v1, target = tmp_path / "v1", tmp_path / "v2"
    v1.mkdir()
    target.mkdir()
    (v1 / "Example_Fig1.png").write_bytes(tiny_png())
    Image.new("RGB", (4, 3), "red").save(v1 / "Example_Tab1.jpg")
    decisions = copy_images(v1, target, "Example", {"Fig1", "Tab1", "Text"})
    assert (target / "Example_Fig1.png").read_bytes() == tiny_png()
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


@pytest.mark.parametrize(
    "twin", ["Example_Tab2.jpg", "Example_Tab2.JPEG", "Example_Tab2.PNG"]
)
def test_a_source_with_two_images_refuses_the_study(tmp_path, twin, request):
    # Neither image may silently replace the other.
    if twin.lower() == "example_tab2.png":
        request.getfixturevalue("case_sensitive")
    v1, target = tmp_path / "v1", tmp_path / "v2"
    v1.mkdir()
    target.mkdir()
    (v1 / "Example_Tab2.png").write_bytes(tiny_png())
    Image.new("RGB", (4, 3), "red").save(v1 / twin, format="JPEG")
    assert image_sources(v1, "Example") == {"Tab2"}
    with pytest.raises(NotConverted) as error:
        copy_images(v1, target, "Example", {"Tab2"})
    assert error.value.code == "image_conflict"
    assert error.value.message == (
        f"Source Tab2 has more than one image: {', '.join(sorted(['Example_Tab2.png', twin]))}; "
        "keep one"
    )
    assert not list(target.iterdir())


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


def folders(tmp_path):
    v1, target = tmp_path / "v1", tmp_path / "v2"
    v1.mkdir()
    target.mkdir()
    return v1, target


@pytest.mark.parametrize("study", ["Ex[ab]mple", "Ex[mple"])
def test_a_study_name_with_glob_characters_matches_only_its_images(tmp_path, study):
    v1, target = folders(tmp_path)
    (v1 / f"{study}_Fig1.png").write_bytes(tiny_png())
    # Other files that the name would match as a pattern.
    for other in (
        "Exa_Fig1.png",
        "Exb_Fig1.jpg",
        "Example_Fig1.png",
        "Exmple_Fig1.png",
    ):
        (v1 / other).write_bytes(b"not an image")
    decisions = copy_images(v1, target, study, {"Fig1"})
    assert decisions == []
    assert (target / f"{study}_Fig1.png").read_bytes() == tiny_png()
    with pytest.raises(NotConverted) as missing:
        copy_images(v1, target, study, {"Fig2"})
    assert missing.value.code == "missing_image"


def test_a_jpg_is_turned_upright_and_keeps_its_color_profile(tmp_path):
    v1, target = folders(tmp_path)
    picture = Image.new("RGB", (4, 2), "red")
    exif = Image.Exif()
    exif[0x0112] = 6  # rotated 90 degrees: the stored picture lies on its side
    profile = b"profile-bytes"
    picture.save(v1 / "Example_Fig1.jpg", exif=exif, icc_profile=profile)
    decisions = copy_images(v1, target, "Example", {"Fig1"})
    with Image.open(target / "Example_Fig1.png") as image:
        assert image.size == (2, 4)
        assert image.info["icc_profile"] == profile
        assert 0x0112 not in image.getexif()
    assert [d.detail for d in decisions] == [
        "Example_Fig1.jpg to Example_Fig1.png (turned upright by its EXIF orientation)"
    ]


def test_a_jpg_without_orientation_is_not_rotated(tmp_path):
    v1, target = folders(tmp_path)
    Image.new("RGB", (4, 2), "red").save(v1 / "Example_Fig1.jpg")
    decisions = copy_images(v1, target, "Example", {"Fig1"})
    with Image.open(target / "Example_Fig1.png") as image:
        assert image.size == (4, 2)
    assert decisions[0].detail == "Example_Fig1.jpg to Example_Fig1.png"


def test_a_cmyk_jpg_becomes_rgb_without_its_profile(tmp_path):
    v1, target = folders(tmp_path)
    Image.new("CMYK", (4, 2)).save(v1 / "Example_Fig1.jpg", icc_profile=b"cmyk")
    copy_images(v1, target, "Example", {"Fig1"})
    with Image.open(target / "Example_Fig1.png") as image:
        assert image.mode == "RGB"
        assert "icc_profile" not in image.info


@pytest.mark.parametrize("damage", ["garbage", "truncated"])
def test_a_corrupt_png_refuses_the_study(tmp_path, damage):
    v1, target = folders(tmp_path)
    buffer = io.BytesIO()
    Image.effect_noise((64, 64), 80).save(buffer, format="PNG")
    data = b"garbage" if damage == "garbage" else buffer.getvalue()[:-40]
    (v1 / "Example_Fig1.png").write_bytes(data)
    with pytest.raises(NotConverted) as error:
        copy_images(v1, target, "Example", {"Fig1"})
    assert error.value.code == "image_unreadable"
    assert "Example_Fig1.png" in error.value.message
    assert not (target / "Example_Fig1.png").exists()


@pytest.mark.parametrize("suffix", ["png", "jpg"])
def test_a_write_failure_is_not_blamed_on_the_image(tmp_path, suffix, monkeypatch):
    v1, target = folders(tmp_path)
    if suffix == "png":
        (v1 / "Example_Fig1.png").write_bytes(tiny_png())
    else:
        Image.new("RGB", (4, 2)).save(v1 / "Example_Fig1.jpg")

    def full_disk(*args, **kwargs):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr("shutil.copyfile", full_disk)
    monkeypatch.setattr(Image.Image, "save", full_disk)
    with pytest.raises(NotConverted) as error:
        copy_images(v1, target, "Example", {"Fig1"})
    assert error.value.code == "image_write"
    assert "cannot be read" not in error.value.message
    assert "No space left" in error.value.message


@pytest.mark.parametrize("orientation", [0, 9])
def test_an_unknown_orientation_is_not_reported(tmp_path, orientation):
    v1, target = folders(tmp_path)
    exif = Image.Exif()
    exif[0x0112] = orientation
    Image.new("RGB", (4, 2)).save(v1 / "Example_Fig1.jpg", exif=exif)
    decisions = copy_images(v1, target, "Example", {"Fig1"})
    assert decisions[0].detail == "Example_Fig1.jpg to Example_Fig1.png"


@pytest.mark.parametrize("format", ["JPEG", "GIF"])
def test_another_image_format_named_png_is_converted(tmp_path, format):
    v1, target = folders(tmp_path)
    Image.new("RGB", (4, 2), "red").save(v1 / "Example_Fig1.png", format=format)
    decisions = copy_images(v1, target, "Example", {"Fig1"})
    with Image.open(target / "Example_Fig1.png") as image:
        assert image.format == "PNG"
    assert [d.kind for d in decisions] == ["image_converted"]


def test_the_reason_of_an_unreadable_image_names_no_absolute_path(tmp_path):
    v1, target = folders(tmp_path)
    (v1 / "Example_Fig1.png").write_bytes(b"garbage")
    with pytest.raises(NotConverted) as error:
        copy_images(v1, target, "Example", {"Fig1"})
    assert error.value.code == "image_unreadable"
    assert str(tmp_path) not in error.value.message
    assert "Example_Fig1.png" in error.value.message
