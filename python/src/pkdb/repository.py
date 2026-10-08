"""A pkdb_data checkout: its root folder and its study folders."""

from pathlib import Path

from pkdb.studyformat.text import natural_key

STUDIES = "studies"


def repository_root(path: Path) -> Path:
    """The folder that contains `studies/`, found by walking up from `path`."""
    path = Path(path).resolve()
    for folder in (path, *path.parents):
        if (folder / STUDIES).is_dir():
            return folder
    raise ValueError(f"No folder above {path} contains a studies folder")


def subfolders(folder: Path) -> list[Path]:
    """Folders below `folder`, without hidden folders and symbolic links."""
    return [
        path
        for path in folder.iterdir()
        if not path.name.startswith(".") and path.is_dir(follow_symlinks=False)
    ]


def location(folder: Path) -> str:
    """The `<substance>/<name>` of a study folder."""
    return f"{folder.parent.name}/{folder.name}"


def study_folders(root: Path) -> list[Path]:
    """Every `studies/<substance>/<name>` folder of the checkout, in natural order."""
    folders = [
        study
        for substance in subfolders(root / STUDIES)
        for study in subfolders(substance)
    ]
    return sorted(folders, key=lambda folder: natural_key(location(folder)))


def substances(root: Path) -> list[str]:
    """The substance folder names of the checkout, in natural order."""
    return sorted(
        (folder.name for folder in subfolders(root / STUDIES)), key=natural_key
    )
