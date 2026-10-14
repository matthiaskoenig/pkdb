"""pkdb-server rebuild-views builds the stored study pages again (#963)."""

import json

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import OperationalError, ProgrammingError

from pkdb.studyformat.views import VIEW_VERSION
from pkdb_server.cli import main
from pkdb_server.commands import views
from pkdb_server.commands.views import rebuild_views, stale_view_count
from pkdb_server.db.models.files import StoredFile, StudyAttachment
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
    assert result == {"rebuilt": ["caffeine/Example"], "failed": [], "error": None}
    with session_factory() as session:
        assert stale_view_count(session) == 0
    assert documents(session_factory) == before
    assert rebuild_views(session_factory, ingestion.file_store, ingestion.settings) == {
        "rebuilt": [],
        "failed": [],
        "error": None,
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
    ) == {"rebuilt": [], "failed": [], "error": None}


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
        "error": None,
    }
    assert documents(session_factory) == before
    assert main(["rebuild-views", "--all"]) == 0
    assert json.loads(capsys.readouterr().out)["rebuilt"] == ["caffeine/Example"]


def test_a_failing_study_does_not_stop_the_others(
    client, creator_headers, tmp_path, session_factory, ingestion_context
):
    for name, pmid in (("Example", "123"), ("Second", "124")):
        folder = write_study(tmp_path / name, name, pmid=pmid)
        response = client.put(
            f"/api/v2/studies/caffeine/{name}",
            headers=creator_headers,
            **multipart(folder),
        )
        assert response.status_code == 201
    ingestion, _ = ingestion_context
    with session_factory() as session:
        keys = list(
            session.scalars(
                select(StoredFile.storage_key)
                .join(StudyAttachment)
                .join(Study, Study.id == StudyAttachment.study_id)
                .where(Study.sid == "caffeine/Example")
            )
        )
    assert keys
    for key in keys:
        ingestion.file_store.path(key).unlink()
    with session_factory.begin() as session:
        session.execute(update(StudyView).values(version=VIEW_VERSION - 1))
    result = rebuild_views(session_factory, ingestion.file_store, ingestion.settings)
    assert result["rebuilt"] == ["caffeine/Second"]
    assert [item["sid"] for item in result["failed"]] == ["caffeine/Example"]
    assert result["failed"][0]["error"]
    with session_factory() as session:
        versions = {
            sid: version
            for sid, version in session.execute(
                select(Study.sid, StudyView.version)
                .join(StudyView, StudyView.study_id == Study.id)
                .where(StudyView.kind == "study")
            )
        }
    assert versions == {
        "caffeine/Example": VIEW_VERSION - 1,
        "caffeine/Second": VIEW_VERSION,
    }


def upload_three(client, creator_headers, tmp_path, session_factory):
    """Three uploaded studies whose stored pages are stale."""
    for name, pmid in (("A", "121"), ("B", "122"), ("C", "123")):
        folder = write_study(tmp_path / name, name, pmid=pmid)
        response = client.put(
            f"/api/v2/studies/caffeine/{name}",
            headers=creator_headers,
            **multipart(folder),
        )
        assert response.status_code == 201, response.text
    with session_factory.begin() as session:
        session.execute(update(StudyView).values(version=VIEW_VERSION - 1))


def failing_for(monkeypatch, sid, error):
    build = views.build_views

    def build_views(folder, **kwargs):
        if "/".join(folder.parts[-2:]) == sid:
            raise error
        return build(folder, **kwargs)

    monkeypatch.setattr(views, "build_views", build_views)


def test_a_builder_error_in_one_study_does_not_stop_the_others(
    client,
    creator_headers,
    tmp_path,
    session_factory,
    ingestion_context,
    monkeypatch,
):
    upload_three(client, creator_headers, tmp_path, session_factory)
    ingestion, _ = ingestion_context
    failing_for(monkeypatch, "caffeine/B", TypeError("unhashable type: 'list'"))
    result = rebuild_views(session_factory, ingestion.file_store, ingestion.settings)
    assert result == {
        "rebuilt": ["caffeine/A", "caffeine/C"],
        "failed": [
            {"sid": "caffeine/B", "error": "TypeError: unhashable type: 'list'"}
        ],
        "error": None,
    }


def test_a_database_error_of_a_study_names_only_its_type(
    client,
    creator_headers,
    tmp_path,
    session_factory,
    ingestion_context,
    monkeypatch,
):
    upload_three(client, creator_headers, tmp_path, session_factory)
    ingestion, _ = ingestion_context
    failing_for(
        monkeypatch,
        "caffeine/B",
        ProgrammingError("SELECT secret", {}, Exception("password=hunter2")),
    )
    result = rebuild_views(session_factory, ingestion.file_store, ingestion.settings)
    assert result["rebuilt"] == ["caffeine/A", "caffeine/C"]
    assert result["failed"] == [{"sid": "caffeine/B", "error": "ProgrammingError"}]


def test_a_lost_database_ends_the_run(
    client,
    creator_headers,
    tmp_path,
    session_factory,
    ingestion_context,
    monkeypatch,
    capsys,
):
    upload_three(client, creator_headers, tmp_path, session_factory)
    ingestion, _ = ingestion_context
    failing_for(
        monkeypatch,
        "caffeine/B",
        OperationalError("SELECT 1", {}, Exception("connection refused")),
    )
    result = rebuild_views(session_factory, ingestion.file_store, ingestion.settings)
    assert result == {
        "rebuilt": ["caffeine/A"],
        "failed": [],
        "error": "OperationalError",
    }
    monkeypatch.setenv(
        "PKDB_DATABASE_URL",
        session_factory.kw["bind"].url.render_as_string(hide_password=False),
    )
    monkeypatch.setenv("PKDB_FILE_ROOT", str(ingestion.file_store.root))
    capsys.readouterr()
    assert main(["rebuild-views", "--all"]) == 1
    output = json.loads(capsys.readouterr().out)
    assert (output["ok"], output["error"]) == (False, "OperationalError")
    assert "connection refused" not in json.dumps(output)


@pytest.mark.parametrize("every", [1, 2])
def test_the_progress_goes_to_stderr(
    client,
    creator_headers,
    tmp_path,
    session_factory,
    ingestion_context,
    monkeypatch,
    capsys,
    every,
):
    upload_three(client, creator_headers, tmp_path, session_factory)
    ingestion, _ = ingestion_context
    monkeypatch.setattr(views, "PROGRESS_EVERY", every)
    capsys.readouterr()
    rebuild_views(session_factory, ingestion.file_store, ingestion.settings)
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err.splitlines() == [
        f"rebuilt {done} of 3" for done in range(every, 4, every)
    ]


def test_the_row_counts_the_warnings_of_the_stored_report(
    client, creator_headers, tmp_path, session_factory, ingestion_context
):
    folder = write_study(tmp_path / "sources")
    assert (
        client.put(URL, headers=creator_headers, **multipart(folder)).status_code == 201
    )
    ingestion, _ = ingestion_context
    with session_factory.begin() as session:
        study = session.scalar(select(Study).where(Study.sid == "caffeine/Example"))
        count = len(study.validation_report["issues"]) + 5
        study.validation_report = {**study.validation_report, "warning_count": count}
    rebuild_views(
        session_factory, ingestion.file_store, ingestion.settings, everything=True
    )
    assert documents(session_factory)[("row", "")]["warnings"] == count
