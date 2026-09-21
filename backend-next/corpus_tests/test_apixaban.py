"""Explicit corpus gate: absence of the requested corpus is an error, not a skip."""

import os
from pathlib import Path

import pytest

from pkdb.importers.folder import load_folder, parse_bundle

ROOT = Path(os.environ["PKDB_STUDY_CORPUS"]) / "apixaban"
PATHS = sorted(path.parent for path in ROOT.glob("*/study.json"))
assert PATHS, f"No apixaban studies in {ROOT}"


@pytest.mark.parametrize("folder", PATHS, ids=lambda path: path.name)
def test_apixaban_parses_without_source_edits(folder):
    study = parse_bundle(load_folder(folder))
    assert study.sid
    assert study.reference.sid
    assert study.groups
    assert study.interventions
    assert study.measurements
    assert all(record.source is not None for record in study.measurements)
