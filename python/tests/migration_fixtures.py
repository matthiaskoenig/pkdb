"""Synthetic format 1 studies for the migration tests."""

import json
from pathlib import Path
from typing import Any

import openpyxl

# study.json of the twin; Any lets tests derive variants from its nested parts.
STUDY: dict[str, Any] = {
    "sid": "Example",
    "name": "Example",
    "reference": "123",
    "creator": "curator",
    "curators": [["curator", 3]],
    "licence": "open",
    "access": "private",
    "groupset": {
        "groups": [
            {
                "name": "all",
                "count": 2,
                "image": "Tab1",
                "characteristica": [
                    {
                        "measurement_type": "species",
                        "choice": "Homo sapiens",
                        "image": "Tab1",
                    },
                    {"measurement_type": "healthy", "choice": "Y", "image": "Tab1"},
                    {"measurement_type": "sex", "choice": "M", "image": "Tab1"},
                ],
            }
        ]
    },
    "individualset": {
        "individuals": [
            {
                "name": name,
                "group": "all",
                "image": "TabA",
                "characteristica": [
                    {
                        "measurement_type": "age",
                        "value": age,
                        "unit": "yr",
                        "image": "TabA",
                    }
                ],
            }
            for name, age in (("S1", 30), ("S2", 40))
        ]
    },
    "interventionset": {
        "interventions": [
            {
                "name": "D1",
                "measurement_type": "dosing",
                "substance": "drug",
                "route": "oral",
                "form": "tablet",
                "application": "single dose",
                "time": 0,
                "time_unit": "h",
                "value": 100,
                "unit": "mg",
            }
        ]
    },
    "outputset": {
        "outputs": [
            {
                "source": "Tab2",
                "image": "Tab2",
                "output_type": "output",
                "group": "all",
                "interventions": ["D1"],
                "measurement_type": "cmax",
                "substance": "drug",
                "tissue": "plasma",
                "mean": "col==mean",
                "sd": "col==sd",
                "unit": "mg/l",
            },
            {
                "source": "Fig1",
                "image": "Fig1",
                "output_type": "timecourse",
                "label": "drug_plasma",
                "group": "all",
                "interventions": ["D1"],
                "measurement_type": "concentration",
                "substance": "drug",
                "tissue": "plasma",
                "time": "col==time",
                "time_unit": "h",
                "mean": "col==mean",
                "unit": "mg/l",
            },
        ]
    },
}
SHEETS = {
    "Tab2": [["mean", "sd"], [2.5, 0.5]],
    "Fig1": [["time", "mean"], [0, 0], [1, 2], [2, 1]],
}
IMAGES = ("Tab1", "TabA", "Tab2", "Fig1")


def write_sheets(folder: Path, name: str, sheets: dict, *, workbook: bool) -> None:
    """Format 1 tables: a workbook with a notes row above the header, or hidden TSVs.

    Both give the same rows: the importer reads the header of a sheet from its
    second row and the header of a TSV from its first line.
    """
    if not sheets:
        return
    if workbook:
        book = openpyxl.Workbook()
        book.remove(book.active)
        for title, rows in sheets.items():
            sheet = book.create_sheet(title)
            sheet.append(["Curator notes"])
            for row in rows:
                sheet.append(row)
        book.save(folder / f"{name}.xlsx")
        book.close()
    else:
        for title, rows in sheets.items():
            text = "".join("\t".join(str(c) for c in row) + "\n" for row in rows)
            (folder / f".{name}_{title}.tsv").write_text(text, encoding="utf-8")


def v1_study(
    root: Path,
    study: dict,
    sheets: dict,
    images: tuple[str, ...],
    *,
    substance: str = "caffeine",
    workbook: bool = True,
    reference: dict | None = None,
) -> Path:
    """A format 1 study folder at `root/studies/<substance>/<name>`."""
    name = study["name"]
    folder = root / "studies" / substance / name
    folder.mkdir(parents=True)
    (folder / "study.json").write_text(json.dumps(study), encoding="utf-8")
    (folder / "reference.json").write_text(
        json.dumps(
            reference
            or {"sid": "123", "name": name, "pmid": "123", "title": "Example study"}
        ),
        encoding="utf-8",
    )
    write_sheets(folder, name, sheets, workbook=workbook)
    (folder / f"{name}.pdf").write_bytes(b"%PDF")
    for source in images:
        (folder / f"{name}_{source}.png").write_bytes(b"png")
    return folder


def v1_example(root: Path, *, workbook: bool = True) -> Path:
    """The format 1 twin of the `valid_files` fixture, without its scatters."""
    return v1_study(root, STUDY, SHEETS, IMAGES, workbook=workbook)
