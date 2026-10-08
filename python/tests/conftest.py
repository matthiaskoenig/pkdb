"""Legacy pkdb_data layout, without a database or an external study corpus."""

import json
from pathlib import Path
from types import SimpleNamespace

import openpyxl
import pytest

from pkdb.domain.vocabulary import MeasurementRule, SubstanceDefinition, Vocabulary
from pkdb.studyformat.jsonio import dump_json
from pkdb.studyformat.tables import TABLES
from pkdb.studyformat.text import render_tsv

# Show a structural diff when a contract fixture is stale.
pytest.register_assert_rewrite("curation_contract")


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path_factory, monkeypatch):
    """Keep the user's cache and PK-DB identity out of every test."""
    monkeypatch.setenv("PKDB_CACHE_DIR", str(tmp_path_factory.mktemp("cache")))
    monkeypatch.delenv("PKDB_USER", raising=False)


@pytest.fixture
def account_server(monkeypatch):
    """A fake PK-DB server whose API key belongs to `server.username`.

    It replaces `pkdb.client.Client`. `server.failure`, when set, is raised by the identity
    check instead, and `server.calls` records the endpoint, key, user and transport of each
    client.
    """
    from pkdb import client as client_module

    server = SimpleNamespace(calls=[], username="curator", failure=None)

    class Client:
        def __init__(self, endpoint, api_key=None, *, user=None, transport=None, **_):
            server.calls.append((endpoint, api_key, user, transport))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def identity(self):
            if server.failure is not None:
                raise server.failure
            return SimpleNamespace(username=server.username, can_upload=True)

    monkeypatch.setattr(client_module, "Client", Client)
    return server


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
    (root / "reference.json").write_text(
        json.dumps({"sid": 123, "name": "Example", "pmid": "123"})
    )
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


@pytest.fixture
def sf_vocabulary():
    return Vocabulary(
        version="studyformat-test",
        measurements=(
            MeasurementRule(
                name="species", dtype="categorical", choices=("Homo sapiens",)
            ),
            MeasurementRule(name="healthy", dtype="boolean", choices=("Y", "N")),
            MeasurementRule(name="sex", dtype="categorical", choices=("M", "F", "NR")),
            MeasurementRule(name="age", units=("yr",)),
            MeasurementRule(name="concentration", units=("mg/l",), time_required=True),
            MeasurementRule(name="cmax", units=("mg/l",)),
            MeasurementRule(name="dosing", units=("mg",)),
            # Numeric in the bundled vocabulary, but used without a dose.
            MeasurementRule(name="qualitative dosing", units=("mg", "NO_UNIT")),
            MeasurementRule(name="fasting", dtype="boolean", choices=("Y", "N")),
            MeasurementRule(name="kinetics", dtype="abstract"),
            MeasurementRule(
                name="medication", dtype="boolean", choices=("Y", "N", "NR")
            ),
            MeasurementRule(name="change", units=("mg/l",), can_negative=True),
            MeasurementRule(name="old_measure", units=("mg/l",), deprecated=True),
            # Pharmacokinetic parameters that postprocessing derives from timecourses.
            MeasurementRule(name="auc_end", units=("g/l*hr", "mol/l*hr")),
            MeasurementRule(name="auc_inf", units=("g/l*hr", "mol/l*hr")),
            MeasurementRule(name="clearance", units=("l/hr", "l/hr/kg")),
            MeasurementRule(name="kel", units=("1/min",)),
            MeasurementRule(name="thalf", units=("hr",)),
            MeasurementRule(name="tmax", units=("hr",)),
            MeasurementRule(name="vd", units=("l", "l/kg")),
            MeasurementRule(name="vd_ss", units=("l", "l/kg")),
        ),
        substances=(SubstanceDefinition(name="drug", sid="drug", mass=500),),
        tissues=("plasma",),
        methods=("HPLC",),
        routes=("oral",),
        forms=("tablet",),
        applications=(
            "single dose",
            "multiple dose",
            "constant infusion",
            "variable infusion",
        ),
        calculation_types=("calculation", "geometric mean", "sample mean"),
    )


@pytest.fixture
def make_study(tmp_path):
    def make(files, *, name="Example", substance="caffeine") -> Path:
        folder = tmp_path / substance / name
        folder.mkdir(parents=True)
        for file, content in files.items():
            path = folder / file
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                path.write_text(content, encoding="utf-8", newline="")
        return folder

    return make


@pytest.fixture
def tsv():
    def render(kind, *rows):
        spec = TABLES[kind]
        for row in rows:
            unknown = set(row) - set(spec.names)
            assert not unknown, f"unknown columns {sorted(unknown)} for {kind}"
        return render_tsv(
            spec.names,
            [tuple(row.get(name, "") for name in spec.names) for row in rows],
        )

    return render


@pytest.fixture
def valid_files(tsv):
    """A complete, valid study before formatting (owned columns still empty)."""
    timecourse = {
        "label": "drug_plasma",
        "subjects": "all",
        "interventions": "D1",
        "measurement": "concentration",
        "substance": "drug",
        "tissue": "plasma",
        "time_unit": "h",
        "unit": "mg/l",
    }
    point = {
        "name": "age_vs_cmax",
        "x_measurement": "age",
        "x_unit": "yr",
        "y_interventions": "D1",
        "y_measurement": "cmax",
        "y_substance": "drug",
        "y_tissue": "plasma",
        "y_unit": "mg/l",
    }
    return {
        "study.json": dump_json(
            {
                "format": 2,
                "reference": {"pmid": "123"},
                "creator": "curator",
                "curators": [{"user": "curator", "rating": 3}],
                "licence": "open",
                "access": "private",
            }
        ),
        "reference.json": dump_json(
            {"sid": "123", "name": "Example", "pmid": "123", "title": "Example study"}
        ),
        "review.json": dump_json({"status": "draft"}),
        "subjects.tsv": tsv(
            "subjects",
            {"name": "all", "count": "2", "source": "Tab1"},
            {"name": "S1", "parent": "all", "count": "1", "source": "TabA"},
            {"name": "S2", "parent": "all", "count": "1", "source": "TabA"},
        ),
        "interventions.tsv": tsv(
            "interventions",
            {
                "source": "Text",
                "name": "D1",
                "measurement": "dosing",
                "substance": "drug",
                "route": "oral",
                "form": "tablet",
                "application": "single dose",
                "time": "0",
                "time_unit": "h",
                "mean": "100",
                "unit": "mg",
            },
        ),
        "characteristica.tsv": tsv(
            "characteristica",
            {
                "source": "Tab1",
                "subjects": "all",
                "measurement": "species",
                "choice": "Homo sapiens",
            },
            {
                "source": "Tab1",
                "subjects": "all",
                "measurement": "healthy",
                "choice": "Y",
            },
            {"source": "Tab1", "subjects": "all", "measurement": "sex", "choice": "M"},
            {
                "source": "TabA",
                "subjects": "S1",
                "measurement": "age",
                "mean": "30",
                "unit": "yr",
            },
            {
                "source": "TabA",
                "subjects": "S2",
                "measurement": "age",
                "mean": "40",
                "unit": "yr",
            },
        ),
        "outputs_Tab2.tsv": tsv(
            "outputs",
            {
                "subjects": "all",
                "interventions": "D1",
                "measurement": "cmax",
                "substance": "drug",
                "tissue": "plasma",
                "mean": "2.5",
                "sd": "0.5",
                "unit": "mg/l",
            },
        ),
        "timecourses_Fig1.tsv": tsv(
            "timecourses",
            *(
                {**timecourse, "time": t, "mean": m}
                for t, m in (("0", "0"), ("1", "2"), ("2", "1"))
            ),
        ),
        "scatters_Fig2.tsv": tsv(
            "scatters",
            {**point, "subjects": "S1", "x_mean": "30", "y_mean": "2"},
            {**point, "subjects": "S2", "x_mean": "40", "y_mean": "3"},
        ),
        "Example.pdf": b"%PDF",
        "Example_Tab1.png": b"png",
        "Example_TabA.png": b"png",
        "Example_Tab2.png": b"png",
        "Example_Fig1.png": b"png",
        "Example_Fig2.png": b"png",
    }


@pytest.fixture
def valid_study(make_study, valid_files):
    from pkdb.studyformat.formatter import format_folder

    folder = make_study(valid_files)
    assert format_folder(folder).ok
    return folder
