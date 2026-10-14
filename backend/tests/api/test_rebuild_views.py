"""pkdb-server rebuild-views builds the stored study pages again (#963)."""

import json

from sqlalchemy import delete, select, update

from pkdb.studyformat.views import VIEW_VERSION
from pkdb_server.cli import main
from pkdb_server.commands.views import rebuild_views, stale_view_count
from pkdb_server.db.models.studies import Study
from pkdb_server.db.models.views import StudyView
from tests.fixtures.study_folders import multipart, write_study

URL = "/api/v2/studies/caffeine/Example"


def documents(session_factory):
    with session_factory() as session:
        return {
            (row.kind, row.key): row.document
            for row in session.scalars(select(StudyView))
        }


def test_rebuild_builds_stale_views_again(
    client, creator_headers, tmp_path, session_factory, ingestion_context
):
    folder = write_study(tmp_path / "sources")
    assert (
        client.put(URL, headers=creator_headers, **multipart(folder)).status_code == 201
    )
    ingestion, _ = ingestion_context
    before = documents(session_factory)
    with session_factory.begin() as session:
        session.execute(update(StudyView).values(version=VIEW_VERSION - 1))
    with session_factory() as session:
        assert stale_view_count(session) == 1
    # A stale page is still served until it is rebuilt.
    assert client.get(URL + "/view", headers=creator_headers).status_code == 200
    with session_factory.begin() as session:
        session.execute(update(StudyView).values(document={}))
    result = rebuild_views(session_factory, ingestion.file_store, ingestion.settings)
    assert result == {"rebuilt": ["caffeine/Example"], "failed": []}
    with session_factory() as session:
        assert stale_view_count(session) == 0
    assert documents(session_factory) == before
    assert rebuild_views(session_factory, ingestion.file_store, ingestion.settings) == {
        "rebuilt": [],
        "failed": [],
    }


def test_rebuild_all_and_studies_without_texts(
    client, creator_headers, tmp_path, session_factory, ingestion_context
):
    folder = write_study(tmp_path / "sources")
    assert (
        client.put(URL, headers=creator_headers, **multipart(folder)).status_code == 201
    )
    ingestion, _ = ingestion_context
    result = rebuild_views(
        session_factory, ingestion.file_store, ingestion.settings, everything=True
    )
    assert result["rebuilt"] == ["caffeine/Example"]
    # A study uploaded before the texts were kept cannot be rebuilt; it is not stale either.
    with session_factory.begin() as session:
        session.execute(update(Study).values(study_json=None, reference_json=None))
        session.execute(delete(StudyView))
    with session_factory() as session:
        assert stale_view_count(session) == 0
    assert rebuild_views(
        session_factory, ingestion.file_store, ingestion.settings, everything=True
    ) == {"rebuilt": [], "failed": []}


def test_rebuild_views_command(
    client,
    creator_headers,
    tmp_path,
    session_factory,
    ingestion_context,
    monkeypatch,
    capsys,
):
    folder = write_study(tmp_path / "sources")
    assert (
        client.put(URL, headers=creator_headers, **multipart(folder)).status_code == 201
    )
    ingestion, _ = ingestion_context
    before = documents(session_factory)
    with session_factory.begin() as session:
        session.execute(update(StudyView).values(version=VIEW_VERSION - 1, document={}))
    monkeypatch.setenv(
        "PKDB_DATABASE_URL",
        session_factory.kw["bind"].url.render_as_string(hide_password=False),
    )
    monkeypatch.setenv("PKDB_FILE_ROOT", str(ingestion.file_store.root))
    capsys.readouterr()
    assert main(["rebuild-views"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "ok": True,
        "rebuilt": ["caffeine/Example"],
        "failed": [],
    }
    assert documents(session_factory) == before
    assert main(["rebuild-views", "--all"]) == 0
    assert json.loads(capsys.readouterr().out)["rebuilt"] == ["caffeine/Example"]
