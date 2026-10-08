"""Shrink screenshots of the curation app: quantize each PNG to 256 colors without dithering.

    uv run --project python python tools/curation_docs/optimize_png.py <png> ...

A screenshot of the app has a few thousand colors, most of them at the edges of text. With 256
colors and no dithering it looks the same and takes less than half the bytes. A file whose
quantized version is not smaller stays as it is.
"""

import sys
from pathlib import Path

from PIL import Image


def optimize(path: Path) -> None:
    """Replace the PNG `path` by its quantized version when that is smaller."""
    with Image.open(path) as image:
        quantized = image.convert("RGB").quantize(
            colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
        )
    smaller = path.with_name(f".{path.name}")
    quantized.save(smaller, format="PNG", optimize=True)
    if smaller.stat().st_size < path.stat().st_size:
        smaller.replace(path)
    else:
        smaller.unlink()


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: optimize_png.py <png> ...")
    for name in sys.argv[1:]:
        optimize(Path(name))


if __name__ == "__main__":
    main()
