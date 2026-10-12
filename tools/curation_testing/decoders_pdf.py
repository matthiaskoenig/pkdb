"""Write a PDF whose images need the decoders that PDF.js runs as WebAssembly when it may.

Page 1 is a black square as a CCITT fax image, which PDF.js decodes with its JBIG2 module;
page 2 a red square as a JPEG 2000 image (OpenJPEG). The curation app allows no WebAssembly, so
the browser test of the paper sees the JavaScript decoders draw them.

    python tools/curation_testing/decoders_pdf.py <output.pdf>
"""

import sys
from pathlib import Path

from PIL import Image


def main() -> None:
    black = Image.new("1", (120, 120), 0)
    red = Image.new("RGBA", (120, 120), (220, 0, 0, 255))
    black.save(Path(sys.argv[1]), save_all=True, append_images=[red], resolution=72.0)


if __name__ == "__main__":
    main()
