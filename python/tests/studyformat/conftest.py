"""Fixtures for study format 2 tests."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from pkdb.domain.vocabulary import MeasurementRule, SubstanceDefinition, Vocabulary
from pkdb.studyformat.jsonio import dump_json
from pkdb.studyformat.tables import TABLES
from pkdb.studyformat.text import render_tsv


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


@pytest.fixture
def libreoffice_resave(tmp_path_factory):
    """Re-save a workbook with headless LibreOffice Calc, as a curator's save would.

    Tests using it skip when `soffice` is missing, and fail instead when the
    environment variable PKDB_REQUIRE_LIBREOFFICE is 1, as on the Linux CI job.
    """
    soffice = shutil.which("soffice")
    if soffice is None:
        message = "LibreOffice (soffice) is not installed"
        if os.environ.get("PKDB_REQUIRE_LIBREOFFICE") == "1":
            pytest.fail(f"{message}, but PKDB_REQUIRE_LIBREOFFICE=1 requires it")
        pytest.skip(message)
    # A fresh profile, so that parallel runs and the user's profile do not interfere.
    work = tmp_path_factory.mktemp("libreoffice")
    profile = (work / "lo-profile").as_uri()

    def resave(path: Path) -> Path:
        output = tmp_path_factory.mktemp("resaved")
        completed = subprocess.run(
            [
                soffice,
                f"-env:UserInstallation={profile}",
                "--headless",
                "--calc",
                "--convert-to",
                "xlsx:Calc MS Excel 2007 XML",
                "--outdir",
                str(output),
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        saved = output / path.name
        if completed.returncode != 0 or not saved.is_file():
            output_text = f"{completed.stdout}{completed.stderr}".strip()
            pytest.fail(
                f"LibreOffice could not re-save {path.name} "
                f"(exit {completed.returncode}): {output_text}"
            )
        return saved

    return resave
