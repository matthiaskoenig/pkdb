"""Small scientific fixtures without network, database, or source-corpus dependencies."""

import pytest

from pkdb.domain.vocabulary import MeasurementRule, SubstanceDefinition, Vocabulary
from pkdb.schemas.study import CanonicalStudy


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
            MeasurementRule(name="sex", dtype="categorical", choices=("M", "F", "NR")),
            MeasurementRule(name="healthy", dtype="boolean", choices=("Y", "N")),
        ),
        substances=(SubstanceDefinition(name="drug", sid="drug", mass=500.0),),
        tissues=("plasma",),
        methods=("LC-MS",),
        routes=("oral",),
        forms=("tablet",),
        applications=("single dose",),
    )


@pytest.fixture
def valid_study():
    return CanonicalStudy.model_validate(
        {
            "sid": "TEST1",
            "metadata": {
                "name": "Example",
                "creator": "curator",
                "curators": [{"user": "curator"}],
            },
            "reference": {"sid": "REF1", "name": "Example"},
            "source_digest": "test",
            "groups": [
                {
                    "key": "all",
                    "name": "all",
                    "count": 4,
                    "characteristica": [
                        {
                            "key": "c1",
                            "measurement_type": "species",
                            "choice": "Homo sapiens",
                        },
                        {"key": "c2", "measurement_type": "sex", "choice": "NR"},
                        {"key": "c3", "measurement_type": "healthy", "choice": "Y"},
                    ],
                }
            ],
            "interventions": [
                {
                    "key": "dose",
                    "name": "dose",
                    "measurement_type": "dosing",
                    "substance": "drug",
                    "statistics": {"value": 10.0},
                    "unit": "mg",
                    "time": 0.0,
                    "time_unit": "h",
                    "route": "oral",
                    "form": "tablet",
                    "application": "single dose",
                }
            ],
            "measurements": [
                {
                    "key": "m1",
                    "measurement_type": "concentration",
                    "substance": "drug",
                    "group": "all",
                    "interventions": ["dose"],
                    "statistics": {"mean": 2.0},
                    "unit": "mg/l",
                    "time": 0.0,
                    "time_unit": "h",
                    "tissue": "plasma",
                }
            ],
        }
    )


pytest_plugins = ["tests.db_fixtures"]
