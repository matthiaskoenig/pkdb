"""Convert real studies of pkdb_data, copied first: PKDB_STUDY_CORPUS=<pkdb_data>/studies."""

import os
import shutil
from pathlib import Path

import pytest

from pkdb.migration.run import migrate

CORPUS = Path(os.environ.get("PKDB_STUDY_CORPUS", ""))
STUDIES = (
    "acetaminophen/Abernethy1982",
    "caffeine/Harder1988",
    "albuterol/Guo2016",
    "caffeine/Desmond1980",
    "caffeine/Akinyinka2000",
)
pytestmark = pytest.mark.skipif(
    not os.environ.get("PKDB_STUDY_CORPUS"), reason="PKDB_STUDY_CORPUS is not set"
)


def converter_errors(report):
    return [
        study.study
        for study in report.studies
        if (study.reason or "").startswith("converter_error")
    ]


def test_the_named_studies_convert_without_converter_errors(tmp_path):
    for name in STUDIES:
        shutil.copytree(CORPUS / name, tmp_path / "studies" / name)
    report = migrate(
        [tmp_path / "studies"],
        report=tmp_path / "migration.json",
        registry=None,
        approver=None,
        dry_run=True,
    )
    assert len(report.studies) == len(STUDIES)
    assert converter_errors(report) == []


@pytest.mark.skipif(
    not os.environ.get("PKDB_MIGRATION_FULL"), reason="PKDB_MIGRATION_FULL is not set"
)
def test_the_whole_corpus_converts_without_converter_errors(tmp_path):
    shutil.copytree(CORPUS, tmp_path / "studies")
    report = migrate(
        [tmp_path / "studies"],
        report=tmp_path / "migration.json",
        registry=None,
        approver=None,
        dry_run=True,
    )
    assert converter_errors(report) == []
