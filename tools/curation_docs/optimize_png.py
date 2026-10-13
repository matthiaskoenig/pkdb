"""Shrink screenshots of the curation app: quantize each PNG to 256 colors without dithering.

    uv run --project python python tools/curation_docs/optimize_png.py <png> ...

A screenshot of the app has a few thousand colors, most of them at the edges of text. With 256
colors and no dithering it usually looks the same and takes less than half the bytes. The
quantized version is faithful only when no channel of any pixel differs from the original by more
than TOLERANCE: a median cut drops the hue of thin colored bars, which would contradict the
guide. It tries each quantizer, keeps the smallest faithful result that is smaller than the
file, and leaves the file as it is when there is none.
"""

import sys
from pathlib import Path

from PIL import Image, ImageChops

TOLERANCE = 12
METHODS = (Image.Quantize.MEDIANCUT, Image.Quantize.FASTOCTREE)


def faithful(original: Image.Image, quantized: Image.Image) -> bool:
    """Whether no channel of any pixel differs by more than TOLERANCE."""
    difference = ImageChops.difference(original, quantized.convert("RGB"))
    return all(high <= TOLERANCE for _, high in difference.getextrema())


def optimize(path: Path) -> None:
    """Replace the PNG `path` by its smallest faithful quantized version when that is smaller."""
    with Image.open(path) as image:
        original = image.convert("RGB")
    best = path.stat().st_size
    candidate = path.with_name(f".{path.name}")
    kept = path.with_name(f".kept.{path.name}")
    kept.unlink(missing_ok=True)
    for method in METHODS:
        quantized = original.quantize(
            colors=256, method=method, dither=Image.Dither.NONE
        )
        if not faithful(original, quantized):
            continue
        quantized.save(candidate, format="PNG", optimize=True)
        if candidate.stat().st_size < best:
            best = candidate.stat().st_size
            candidate.replace(kept)
    candidate.unlink(missing_ok=True)
    if kept.exists():
        kept.replace(path)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: optimize_png.py <png> ...")
    for name in sys.argv[1:]:
        optimize(Path(name))


if __name__ == "__main__":
    main()
