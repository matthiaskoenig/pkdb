"""The source of each converted row, and the images of the sources."""

import shutil
from collections.abc import Callable, Collection
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from pkdb.migration.model import Decision, NotConverted
from pkdb.schemas.source import SourceLocation
from pkdb.schemas.study import CanonicalStudy, DataRecord, Observation, Subject
from pkdb.studyformat.raw import missing_source, parse_raw_file
from pkdb.studyformat.tables import (
    SOURCE_PATTERN,
    STUDY_JSON,
    TEXT_SOURCE,
    image_file,
)

PNG_MODES = ("1", "L", "LA", "P", "RGB", "RGBA", "I", "I;16")
PNG_SUFFIX = ".png"
IMAGE_SUFFIXES = (PNG_SUFFIX, ".jpg", ".jpeg")
EXIF_ORIENTATION = 0x0112
# What PIL raises for a file that is no image or ends early.
_UNREADABLE = (OSError, SyntaxError, ValueError, Image.DecompressionBombError)


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
    (`images`, the `documented_sources`); otherwise the sheet, else `Text` for
    an entity of study.json.
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

    Format 2 needs `<study>_<source>.png` for every source but `Text`, or the
    raw table `<study>_<source>.tsv` of a paper table, so the sheet, else the
    source of the row's image, is the source only when the v1 folder holds its
    image or raw table (`images`, the `documented_sources`); otherwise the
    source is `Text`.
    """
    sheet = sheet_of(location, study)
    for source in (sheet, image_source(image, study)):
        if source is not None and source in images and SOURCE_PATTERN.fullmatch(source):
            return source
    return TEXT_SOURCE


def all_records(study: CanonicalStudy) -> list[Observation | Subject | DataRecord]:
    """Every entity of the study that comes from a row of a sheet or of study.json."""
    records: list[Observation | Subject | DataRecord] = []
    for subject in [*study.groups, *study.individuals]:
        records.append(subject)
        records.extend(subject.characteristica)
    records.extend(study.interventions)
    records.extend(study.measurements)
    records.extend(study.scatters)
    return records


def read_files(study: CanonicalStudy) -> frozenset[str]:
    """The files that the entities of the parsed format 1 study were read from."""
    return frozenset(
        record.source.file for record in all_records(study) if record.source is not None
    )


def raw_tables(v1: Path, study: str, read: Collection[str]) -> dict[str, str]:
    """The raw tables of the v1 folder by source: `<study>_<source>.tsv` of a paper table.

    A curator puts the raw table beside the format 1 workbook for data that no
    image shows, such as unpublished data; format 2 keeps it as the raw
    extraction, which is the source of a paper table without an image. A hidden
    format 1 table `.<study>_<sheet>.tsv` is none, and neither is a TSV file that
    study.json reads as a format 1 table (`read`, see `read_files`).
    """
    return {
        source: path.name
        for path in v1.iterdir()
        if path.is_file()
        and path.name not in read
        and (source := parse_raw_file(path.name, study)) is not None
    }


def image_sources(v1: Path, study: str) -> frozenset[str]:
    """The sources that have an image `<study>_<source>` in the v1 folder."""
    return frozenset(
        source
        for path in v1.iterdir()
        if path.is_file()
        and path.suffix.lower() in IMAGE_SUFFIXES
        and (source := image_source(path.name, study)) is not None
    )


def documented_sources(v1: Path, study: str, read: Collection[str]) -> frozenset[str]:
    """The sources that format 2 can name: with an image, or a paper table with its raw table."""
    return image_sources(v1, study) | set(raw_tables(v1, study, read))


def copy_images(
    v1: Path, target: Path, study: str, used: set[str], raw: Collection[str] = ()
) -> list[Decision]:
    """Write `<study>_<source>.png` for each used source; JPG images are converted.

    A paper table without an image whose raw table is in `raw`, the sources of
    `raw_tables`, has its raw table as its source and needs no image.
    """
    decisions = []
    for source in sorted(used - {TEXT_SOURCE, ""}):
        name = image_file(study, source)
        # Exact names: a study name may hold glob characters such as `[`.
        candidates = sorted(
            path
            for path in v1.iterdir()
            if path.stem == f"{study}_{source}"
            and path.suffix
            and path.is_file()
            and parse_raw_file(path.name, study) is None
        )
        images = [path for path in candidates if path.suffix.lower() in IMAGE_SUFFIXES]
        if not images and not candidates and source in raw:
            continue
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
            missing = missing_source(study, source, ())
            raise NotConverted("missing_image", f"No {missing} for source {source}")
        [image] = images
        decision = _copy(image, target / name, name)
        if decision is not None:
            decisions.append(decision)
    return decisions


def _reason(error: Exception) -> str:
    """Why an image cannot be read, without the absolute path that Pillow may name."""
    if isinstance(error, UnidentifiedImageError):
        return "it is not an image file"
    if isinstance(error, OSError) and error.filename is not None:
        return error.strerror or type(error).__name__
    return str(error)


def _write(action: Callable[..., object], *args: Path) -> None:
    """Run a file write; a failure is the target's, not the source image's."""
    try:
        action(*args)
    except OSError as error:
        raise NotConverted(
            "image_write", f"The image could not be written: {_reason(error)}"
        ) from error


def _copy(image: Path, destination: Path, name: str) -> Decision | None:
    """Write `image` as the PNG `destination`; a decision when it was converted.

    The image is decoded completely first. A PNG is copied as it is. Another
    readable format, such as a JPG or a JPEG named `.png`, is written as PNG,
    turned upright by its EXIF orientation and with its ICC profile.
    """
    try:
        with Image.open(image) as picture:
            picture.load()
            if picture.format == "PNG" and image.suffix.lower() == PNG_SUFFIX:
                is_png = True
            else:
                is_png = False
                profile = picture.info.get("icc_profile")
                turned = picture.getexif().get(EXIF_ORIENTATION, 1) in range(2, 9)
                upright = ImageOps.exif_transpose(picture)
    except _UNREADABLE as error:
        raise NotConverted(
            "image_unreadable",
            f"The image {image.name} cannot be read: {_reason(error)}",
        ) from error
    if is_png:
        _write(shutil.copyfile, image, destination)
        return None
    detail = f"{image.name} to {name}"
    if turned:
        detail += " (turned upright by its EXIF orientation)"
    if upright.mode not in PNG_MODES:
        # The profile describes the old color space, such as CMYK.
        upright, profile = upright.convert("RGB"), None
        upright.info.pop("icc_profile", None)
    options = {"icc_profile": profile} if profile else {}
    _write(lambda path: upright.save(path, format="PNG", **options), destination)
    return Decision(kind="image_converted", detail=detail)
