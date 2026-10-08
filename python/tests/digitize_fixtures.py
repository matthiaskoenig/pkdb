"""Helpers that build a small figure: a PNG image and a WebPlotDigitizer project on it."""

import zlib


def png(width: int, height: int, color: bytes = b"\xff\xff\xff") -> bytes:
    """A PNG image of one RGB color, white by default."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return len(data).to_bytes(4) + body + zlib.crc32(body).to_bytes(4)

    rows = b"".join(b"\x00" + color * width for _ in range(height))
    header = width.to_bytes(4) + height.to_bytes(4) + b"\x08\x02\x00\x00\x00"
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def project(points, *, extra=()):
    """A project on a 100 x 100 image: x 0 to 10 over pixels 0 to 100, y 0 to 10 over pixels 100 to 0."""
    axes = {
        "name": "XY",
        "type": "XYAxes",
        "isLogX": False,
        "isLogY": False,
        "noRotation": False,
        "calibrationPoints": [
            {"px": 0, "py": 100, "dx": "0", "dy": "0", "dz": None},
            {"px": 100, "py": 100, "dx": "10", "dy": "0", "dz": None},
            {"px": 0, "py": 100, "dx": "0", "dy": "0", "dz": None},
            {"px": 0, "py": 0, "dx": "0", "dy": "10", "dz": None},
        ],
    }
    datasets = [
        {
            "name": "drug_plasma",
            "axesName": "XY",
            "data": [{"x": x, "y": y} for x, y in points],
        }
    ]
    datasets += [{"name": name, "axesName": "XY", "data": []} for name in extra]
    return {
        "version": [4, 2],
        "axesColl": [axes],
        "datasetColl": datasets,
        "measurementColl": [],
    }


GOOD = [(0, 100), (10, 80), (20, 90)]
