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


def observation_source(location: SourceLocation, image: str | None, study: str) -> str:
    """The source of a row of an outputs, timecourses or scatters table, which names its file."""
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


def curator_source(location: SourceLocation, image: str | None, study: str) -> str:
    """The `source` column of subjects, interventions and characteristica: curator data."""
    sheet = sheet_of(location, study)
    if sheet is not None and SOURCE_PATTERN.fullmatch(sheet):
        return sheet
    source = image_source(image, study)
    if source is not None and SOURCE_PATTERN.fullmatch(source):
        return source
    return TEXT_SOURCE if sheet is None else ""


def copy_images(v1: Path, target: Path, study: str, used: set[str]) -> list[Decision]:
    """Write `<study>_<source>.png` for each used source; JPG images are converted."""
    decisions = []
    for source in sorted(used - {TEXT_SOURCE, ""}):
        name = image_file(study, source)
        candidates = {
            path.suffix.lower(): path
            for path in v1.glob(f"{study}_{source}.*")
            if path.stem == f"{study}_{source}"
        }
        if ".png" in candidates:
            shutil.copyfile(candidates[".png"], target / name)
        elif jpg := candidates.get(".jpg") or candidates.get(".jpeg"):
            try:
                with Image.open(jpg) as image:
                    if image.mode not in PNG_MODES:
                        image = image.convert("RGB")
                    image.save(target / name, format="PNG")
            except OSError as error:
                raise NotConverted(
                    "image_unreadable", f"The image {jpg.name} cannot be read: {error}"
                ) from error
            decisions.append(
                Decision(kind="image_converted", detail=f"{jpg.name} to {name}")
            )
        elif candidates:
            found = ", ".join(sorted(path.name for path in candidates.values()))
            raise NotConverted(
                "image_type", f"The image of {source} is {found}; convert it to PNG"
            )
        else:
            raise NotConverted("missing_image", f"No image {name} for source {source}")
    return decisions
