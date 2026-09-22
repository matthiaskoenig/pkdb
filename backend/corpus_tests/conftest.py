import json
from pathlib import Path

import pytest

from pkdb.domain.vocabulary import MeasurementRule, SubstanceDefinition, Vocabulary


@pytest.fixture(scope="session")
def full_vocabulary():
    data = json.loads(
        (Path(__file__).parents[1] / "bootstrap/vocabulary.json").read_text()
    )
    nodes = data["nodes"]
    return Vocabulary(
        version=data["version"],
        measurements=tuple(
            MeasurementRule(**node["definition"], name=node["name"], sid=node["sid"])
            for node in nodes
            if node["kind"] == "measurement"
        ),
        substances=tuple(
            SubstanceDefinition(
                **node["definition"], name=node["name"], sid=node["sid"]
            )
            for node in nodes
            if node["kind"] == "substance"
        ),
        **{
            field: tuple(node["name"] for node in nodes if node["kind"] == kind)
            for field, kind in [
                ("tissues", "tissue"),
                ("methods", "method"),
                ("routes", "route"),
                ("forms", "form"),
                ("applications", "application"),
                ("calculation_types", "calculation_type"),
            ]
        },
    )
