"""Real dataset publication gate; source corpus stays read-only."""

import json
import os
import shutil
from pathlib import Path

import pytest
from sqlalchemy import select

from pkdb.config import Settings
from pkdb.db.bootstrap import bootstrap
from pkdb.db.models.users import User
from pkdb.db.read import read_study
from pkdb.domain.provenance import comment_authors
from pkdb.files.store import FileStore
from pkdb.importers.folder import load_folder, parse_bundle
from pkdb.schemas.security import Principal
from pkdb.services.ingestion import IngestionService


@pytest.mark.parametrize(
    "name,pairs", [("Abernethy1985a", 78), ("Akinyinka2000", 91), ("Begas2015", 31)]
)
def test_real_scatter_studies_publish(name, pairs, session_factory, tmp_path):
    bundle = load_folder(Path(os.environ["PKDB_STUDY_CORPUS"]) / "caffeine" / name)
    study = parse_bundle(bundle)
    names = {
        study.metadata.creator,
        *study.metadata.collaborators,
        *(curator.user for curator in study.metadata.curators),
        *comment_authors(study),
    }
    (tmp_path / "users.json").write_text(
        json.dumps([{"username": username} for username in names])
    )
    shutil.copy(
        Path(__file__).parents[1] / "bootstrap/vocabulary.json",
        tmp_path / "vocabulary.json",
    )
    with session_factory.begin() as session:
        assert not bootstrap(tmp_path, session).errors
        creator = session.scalar(
            select(User).where(User.username == study.metadata.creator)
        )
        creator.active = True
        actor = Principal(
            user_id=creator.id, username=creator.username, role=creator.role
        )
    settings = Settings(
        database_url="postgresql+psycopg://unused", file_root=tmp_path / "files"
    )
    files = FileStore(settings.file_root, session_factory, settings.upload_max_bytes)
    service = IngestionService(session_factory, files, settings)
    result = service.replace(bundle, actor)
    restored = read_study(result.sid, actor, session_factory)
    assert result.created
    assert (
        sum(
            len(subset.points)
            for dataset in restored.scatters
            if dataset.data_type == "scatter"
            for subset in dataset.subsets
        )
        == pairs
    )
    assert comment_authors(restored) == comment_authors(study)
    assert restored.attachments == study.attachments
