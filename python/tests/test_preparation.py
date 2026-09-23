"""The public API preserves the existing scientific and source-file contract."""

import json
import subprocess
import sys

import pytest

from pkdb import prepare
from pkdb.domain.validation import prepare_study
from pkdb.importers.folder import load_folder, parse_bundle
from pkdb.schemas.study import CanonicalStudy
from pkdb.schemas.validation import StudyValidationError


def test_legacy_folder_matches_shared_engine_without_source_changes(
    study_folder, vocabulary
):
    before = {p.name: p.read_bytes() for p in study_folder.iterdir()}
    result = prepare(study_folder, vocabulary=vocabulary)
    expected = prepare_study(parse_bundle(load_folder(study_folder)), vocabulary)
    assert isinstance(result.study, CanonicalStudy)
    assert result.prepared == expected
    assert result.report.valid
    assert result.study.reference.sid == "123"
    assert [
        m.statistics.mean for m in result.study.measurements if m.origin == "reported"
    ] == [0, 2]
    assert {p.name: p.read_bytes() for p in study_folder.iterdir()} == before


def test_bad_expression_retains_source_location(study_folder, vocabulary):
    path = study_folder / "study.json"
    study = json.loads(path.read_text())
    study["outputset"]["outputs"][0]["mean"] = "col==missing"
    path.write_text(json.dumps(study))
    with pytest.raises(StudyValidationError) as error:
        prepare(study_folder, vocabulary=vocabulary)
    issue = error.value.report.issues[0]
    assert issue.code == "unknown_column"
    assert issue.source is not None
    assert issue.source.file in {"Example.xlsx", "Results.tsv"}
    assert issue.source.row in {2, 3}


def test_row_limit_is_applied_to_folder(study_folder, vocabulary):
    with pytest.raises(StudyValidationError) as error:
        prepare(study_folder, vocabulary=vocabulary, max_rows=1)
    assert error.value.report.issues[0].code == "row_limit"


def test_public_import_does_not_load_server_or_database():
    code = """
import sys
from pkdb import Client, Vocabulary, prepare
assert not any(name == 'pkdb_server' or name.startswith('pkdb_server.') for name in sys.modules)
assert not any(name == 'sqlalchemy' or name.startswith('sqlalchemy.') for name in sys.modules)
"""
    subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, text=True
    )


def test_serialized_hashes_do_not_mutate_preparation(study_folder, vocabulary):
    prepared = prepare(study_folder, vocabulary=vocabulary)
    before = dict(prepared.file_hashes)
    artifact = prepared.model_dump()
    artifact["file_hashes"].clear()
    assert prepared.file_hashes == before
