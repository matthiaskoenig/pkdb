"""The substances that a format 2 study names in its tables, and the substance folders.

`pkdb issues sync` labels the issue of a study, and the Substance filter of `pkdb curate`
finds the study, with the same rule: the substance of the study folder first, then every
other substance folder that the interventions and the data of the study name, ignoring
case and spelled as the folder.
"""

from collections.abc import Iterable, Mapping
from pathlib import Path

from pkdb.studyformat.layout import scan_folder
from pkdb.studyformat.load import load_table

# The tables whose substances count: what the subjects were given and the data; the
# baseline values of characteristica are not about a substance.
SUBSTANCE_COLUMNS = {
    "interventions": ("substance",),
    "outputs": ("substance",),
    "timecourses": ("substance",),
    "scatters": ("x_substance", "y_substance"),
}


def study_substances(folder: Path) -> tuple[str, ...]:
    """The substances that the interventions and the data of a study name, sorted.

    Names that differ only in case count once, in their first spelling. A folder or a
    table that cannot be read names none; validation reports it.
    """
    try:
        layout = scan_folder(folder)
    except OSError:
        return ()
    found: dict[str, str] = {}
    for table_file in layout.tables:
        columns = SUBSTANCE_COLUMNS.get(table_file.spec.kind, ())
        if not columns:
            continue
        try:
            with (layout.folder / table_file.name).open("rb") as stream:
                table, _ = load_table(
                    table_file.name,
                    stream,
                    table_file.spec,
                    table_file.source,
                    study=layout.study,
                )
        except OSError:
            continue
        for row in table.rows if table is not None else ():
            for column in columns:
                if substance := row.cells.get(column, "").strip():
                    found.setdefault(substance.casefold(), substance)
    return tuple(sorted(found.values(), key=str.casefold))


def folder_index(names: Iterable[str]) -> dict[str, str]:
    """The substance folder names by their case-folded name."""
    return {name.casefold(): name for name in names}


def folder_substances(
    substance: str, named: Iterable[str], folders: Mapping[str, str]
) -> list[str]:
    """The substance of the study folder, then the other folders that `named` names.

    `folders` is the `folder_index` of the substance folders. The others are sorted
    ignoring case and spelled as their folders; a name without a folder, such as a
    metabolite, is left out.
    """
    own = substance.casefold()
    others = {
        folders[key]
        for name in named
        if (key := name.casefold()) in folders and key != own
    }
    return [substance, *sorted(others, key=str.casefold)]
