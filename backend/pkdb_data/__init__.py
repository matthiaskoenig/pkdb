"""pkdb_data - Python utilities for PK-DB."""

from pathlib import Path

__author__ = "Matthias König"
__version__ = "1.1.1"

program_name: str = "pkdb_data"
RESOURCES_DIR: Path = Path(__file__).parent / "resources"
STUDIES_DIR: Path = Path(__file__).parent.parent.parent / "studies"

CACHE_USE: bool = True
CACHE_PATH: Path = RESOURCES_DIR / "cache"
