"""The source of each converted row, and the images of the sources."""

import shutil
from pathlib import Path

from PIL import Image

from pkdb.migration.model import Decision, NotConverted
from pkdb.schemas.source import SourceLocation
from pkdb.studyformat.tables import (
    SOURCE_PATTERN,
    STUDY_JSON,
    TEXT_SOURCE,
    image_file,
)

PNG_MODES = ("1", "L", "LA", "P", "RGB", "RGBA", "I", "I;16")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg")


def sheet_of(location: SourceLocation, study: str) -> str | None:
    """The workbook sheet or TSV file of a format 1 row; None for an entity of study.json."""
    if location.file == STUDY_JSON:
        return None
    if location.sheet is not None:
        return location.sheet
    stem = location.file.removesuffix(".tsv")
    hidden = f".{study}_"
    return stem.removeprefix(hidden) if stem.startswith(hidden) else stem


def image_source(image: str | None, study: str) -> str | None:
    """`Fig1` of `<study>_Fig1.png`; None for another name."""
    if not image:
        return None
    stem = Path(image).stem
    prefix = f"{study}_"
    source = stem.removeprefix(prefix) if stem.startswith(prefix) else ""
    return source or None


def observation_source(
    location: SourceLocation, image: str | None, study: str, images: frozenset[str]
) -> str:
    """The source of a row of an outputs, timecourses or scatters table, which names its file.

    Format 2 names the paper table or figure that a row comes from, so the
    source of the row's image comes first when the v1 folder holds that image
    (`images`); otherwise the sheet, else `Text` for an entity of study.json.
    """
    source = image_source(image, study)
    if source is not None and source in images and SOURCE_PATTERN.fullmatch(source):
        return source
    sheet = sheet_of(location, study)
    if sheet is not None:
        if not SOURCE_PATTERN.fullmatch(sheet):
            raise NotConverted(
                "sheet_name",
                f"Sheet {sheet} is not a source name such as Tab2 or Fig3A; rename it",
            )
        return sheet
    if image is None:
        return TEXT_SOURCE
    source = image_source(image, study)
    if source is None or not SOURCE_PATTERN.fullmatch(source):
        raise NotConverted(
            "image_name",
            f"Image {image} is not named {study}_<source> with a source such as Fig3A",
        )
    return source


def curator_source(
    location: SourceLocation, image: str | None, study: str, images: frozenset[str]
) -> str:
    """The `source` column of subjects, interventions and characteristica: curator data.

    Format 2 needs `<study>_<source>.png` for every source but `Text`, so the
    sheet, else the source of the row's image, is the source only when the v1
    folder holds its image (`images`); otherwise the source is `Text`.
    """
    sheet = sheet_of(location, study)
    for source in (sheet, image_source(image, study)):
        if source is not None and source in images and SOURCE_PATTERN.fullmatch(source):
            return source
    return TEXT_SOURCE


def image_sources(v1: Path, study: str) -> frozenset[str]:
    """The sources that have an image `<study>_<source>` in the v1 folder."""
    return frozenset(
        source
        for path in v1.iterdir()
        if path.is_file()
        and path.suffix.lower() in IMAGE_SUFFIXES
        and (source := image_source(path.name, study)) is not None
    )


def copy_images(v1: Path, target: Path, study: str, used: set[str]) -> list[Decision]:
    """Write `<study>_<source>.png` for each used source; JPG images are converted."""
    decisions = []
    for source in sorted(used - {TEXT_SOURCE, ""}):
        name = image_file(study, source)
        candidates = sorted(
            path
            for path in v1.glob(f"{study}_{source}.*")
            if path.stem == f"{study}_{source}"
        )
        images = [path for path in candidates if path.suffix.lower() in IMAGE_SUFFIXES]
        if len(images) > 1:
            # Neither image may silently replace the other.
            found = ", ".join(path.name for path in images)
            raise NotConverted(
                "image_conflict",
                f"Source {source} has more than one image: {found}; keep one",
            )
        if not images:
            if candidates:
                found = ", ".join(path.name for path in candidates)
                raise NotConverted(
                    "image_type", f"The image of {source} is {found}; convert it to PNG"
                )
            raise NotConverted("missing_image", f"No image {name} for source {source}")
        [image] = images
        if image.suffix.lower() == ".png":
            shutil.copyfile(image, target / name)
            continue
        try:
            with Image.open(image) as picture:
                if picture.mode not in PNG_MODES:
                    picture = picture.convert("RGB")
                picture.save(target / name, format="PNG")
        except OSError as error:
            raise NotConverted(
                "image_unreadable", f"The image {image.name} cannot be read: {error}"
            ) from error
        decisions.append(
            Decision(kind="image_converted", detail=f"{image.name} to {name}")
        )
    return decisions
