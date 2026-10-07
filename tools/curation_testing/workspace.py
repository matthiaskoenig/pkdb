"""Copy the curation app test fixture into a new workspace folder and create its workbook.

    uv run --project python python tools/curation_testing/workspace.py <target>

The target must not exist or be empty. caffeine/Demo2020 gets its workbook, generated from its
tables with the bundled vocabulary, so the app starts with the tables in sync; caffeine/Draft2021
keeps none.
"""

import shutil
import sys
from pathlib import Path

from pkdb.cache import bundled_vocabulary
from pkdb.studyformat.sync import sync_study

FIXTURE = Path(__file__).resolve().parent / "fixture"
WITH_WORKBOOK = ("caffeine/Demo2020",)


def create(target: Path) -> Path:
    """Copy the fixture to `target` and create the workbooks; the workspace folder."""
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"{target} is not empty")
    shutil.copytree(FIXTURE, target, dirs_exist_ok=True)
    vocabulary = bundled_vocabulary()
    for study in WITH_WORKBOOK:
        result = sync_study(target / study, vocabulary)
        if not result.ok:
            raise SystemExit(
                f"The workbook of {study} was not created: {result.issues}"
            )
    return target


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: workspace.py <target>")
    print(create(Path(sys.argv[1]).resolve()))


if __name__ == "__main__":
    main()
