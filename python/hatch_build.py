"""Refuse to build a release package without the curation app assets."""

import os
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

INDEX = Path("src", "pkdb", "curation", "static", "index.html")
# Set to 1 for packages that never run `pkdb curate`, such as the server image.
OPT_OUT = "PKDB_BUILD_WITHOUT_CURATION_APP"


def check_assets(root: Path, target: str, version: str) -> None:
    """Raise RuntimeError when a wheel or sdist would ship without the curation app.

    Editable installs skip the check at build time: they serve the assets from the source
    folder, which still needs the built app at run time (`pkdb curate` exits without it).
    """
    if target in {"wheel", "sdist"} and version == "standard":
        if not (root / INDEX).is_file():
            raise RuntimeError(
                "The curation app assets are missing in src/pkdb/curation/static. "
                "Run npm ci and npm run build:curation in frontend/ before building "
                "the package."
            )


class CustomBuildHook(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version, build_data):
        if os.environ.get(OPT_OUT) != "1":
            check_assets(Path(self.root), self.target_name, version)
