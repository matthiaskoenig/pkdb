"""Legacy pkdb_data layout, without a database or an external study corpus."""

import json

import openpyxl
import pytest

from pkdb.domain.vocabulary import MeasurementRule, SubstanceDefinition, Vocabulary


@pytest.fixture
def vocabulary():
    return Vocabulary(
        version="test-v1",
        measurements=(
            MeasurementRule(name="concentration", units=("mg/l",), time_required=True),
            MeasurementRule(name="dosing", units=("mg",)),
            MeasurementRule(
                name="species", dtype="categorical", choices=("Homo sapiens",)
            ),
            MeasurementRule(name="sex", dtype="categorical", choices=("NR",)),
            MeasurementRule(name="healthy", dtype="boolean", choices=("Y", "N")),
        ),
        substances=(SubstanceDefinition(name="drug", sid="drug", mass=500),),
        tissues=("plasma",),
        routes=("oral",),
        forms=("tablet",),
        applications=("single dose",),
    )


@pytest.fixture(params=["xlsx", "tsv"])
def study_folder(tmp_path, request):
    root = tmp_path / "Example"
    root.mkdir()
    source = "Results" if request.param == "xlsx" else "Results.tsv"
    study = {
        "sid": "TEST1",
        "name": "Example",
        "reference": 123,
        "creator": "curator",
        "curators": [["curator", 3]],
        "access": "public",
        "licence": "open",
        "groupset": {
            "groups": [
                {
                    "name": "all",
                    "count": 4,
                    "characteristica": [
                        {"measurement_type": "species", "choice": "Homo sapiens"},
                        {"measurement_type": "sex", "choice": "NR"},
                        {"measurement_type": "healthy", "choice": "Y"},
                    ],
                }
            ]
        },
        "interventionset": {
            "interventions": [
                {
                    "name": "dose",
                    "measurement_type": "dosing",
                    "substance": "drug",
                    "value": 10,
                    "unit": "mg",
                    "time": 0,
                    "time_unit": "h",
                    "route": "oral",
                    "form": "tablet",
                    "application": "single dose",
                }
            ]
        },
        "outputset": {
            "outputs": [
                {
                    "source": source,
                    "output_type": "output",
                    "group": "all",
                    "measurement_type": "concentration",
                    "substance": "drug",
                    "mean": "col==mean",
                    "time": "col==time",
                    "time_unit": "h",
                    "unit": "mg/l",
                    "tissue": "plasma",
                    "interventions": ["dose"],
                }
            ]
        },
    }
    (root / "study.json").write_text(json.dumps(study))
    (root / "reference.json").write_text(json.dumps({"sid": 123, "name": "Example"}))
    if request.param == "xlsx":
        book = openpyxl.Workbook()
        sheet = book.active
        sheet.title = "Results"
        sheet.append(["Curator notes", ""])
        sheet.append(["time", "mean"])
        sheet.append([0, 0])
        sheet.append([1, 2])
        book.save(root / "Example.xlsx")
        book.close()
    else:
        (root / "Results.tsv").write_text("time\tmean\n0\t0\n1\t2\n")
    return root
