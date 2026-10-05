"""Fixtures for study format 2 tests."""

import pytest

from pkdb.domain.vocabulary import MeasurementRule, SubstanceDefinition, Vocabulary


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
            MeasurementRule(name="change", units=("mg/l",), can_negative=True),
            MeasurementRule(name="old_measure", units=("mg/l",), deprecated=True),
        ),
        substances=(SubstanceDefinition(name="drug", sid="drug", mass=500),),
        tissues=("plasma",),
        methods=("HPLC",),
        routes=("oral",),
        forms=("tablet",),
        applications=("single dose", "multiple dose"),
        calculation_types=("calculation", "geometric mean", "sample mean"),
    )
