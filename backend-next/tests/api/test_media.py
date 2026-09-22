import io

import pytest

from pkdb.db.models.files import StudyAttachment
from pkdb.db.models.studies import Study


@pytest.mark.parametrize(
    "access,licence,status",
    [
        ("public", "open", 200),
        ("public", "closed", 403),
        ("private", "open", 403),
        ("private", "closed", 403),
    ],
)
def test_public_media_respects_access_and_licence(
    client, ingestion_context, creator_headers, session_factory, access, licence, status
):
    ingestion, principal = ingestion_context
    staged = ingestion.file_store.stage(
        principal, "paper.pdf", io.BytesIO(b"%PDF-test")
    )
    with session_factory.begin() as session:
        study = Study(
            sid="MEDIA",
            name="media",
            access=access,
            licence=licence,
            creator_id=principal.user_id,
        )
        session.add(study)
        session.flush()
        session.add(
            StudyAttachment(study_id=study.id, file_id=staged.id, name="paper.pdf")
        )
    detail_url = "/api/v1/studies/MEDIA/"
    public_detail = client.get(detail_url)
    if access == "private":
        assert public_detail.status_code == 404
    else:
        assert public_detail.status_code == 200
        assert len(public_detail.json()["files"]) == (1 if licence == "open" else 0)
    owner_files = client.get(detail_url, headers=creator_headers).json()["files"]
    assert len(owner_files) == 1
    assert owner_files[0]["name"] == "data/paper.pdf"
    assert owner_files[0]["file"] == f"/media/{staged.id}/paper.pdf"
    url = f"/media/{staged.id}/paper.pdf"
    assert client.get(url).status_code == status
    response = client.get(url, headers=creator_headers)
    assert response.status_code == 200
    assert response.content == b"%PDF-test"
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_draft_media_is_not_public(client, ingestion_context, creator_headers):
    ingestion, principal = ingestion_context
    staged = ingestion.file_store.stage(
        principal, "paper.pdf", io.BytesIO(b"%PDF-test")
    )
    assert client.get(f"/media/{staged.id}/paper.pdf").status_code == 403
    assert (
        client.get(f"/media/{staged.id}/wrong.pdf", headers=creator_headers).status_code
        == 404
    )


def test_media_closes_file_when_headers_cannot_be_sent(
    client, ingestion_context, creator_headers, monkeypatch
):
    import asyncio

    from starlette.requests import Request

    from pkdb.api.media import download

    ingestion, principal = ingestion_context
    staged = ingestion.file_store.stage(
        principal, "paper.pdf", io.BytesIO(b"%PDF-test")
    )
    store = client.app.state.file_store
    original = store.open_authorized
    handles = []

    def opened(*args):
        handle = original(*args)
        handles.append(handle)
        return handle

    monkeypatch.setattr(store, "open_authorized", opened)
    request = Request(
        {
            "type": "http",
            "app": client.app,
            "headers": [(b"authorization", creator_headers["Authorization"].encode())],
        }
    )
    response = download(staged.id, "paper.pdf", request)

    async def send(message):
        raise OSError("disconnected")

    async def receive():
        return {"type": "http.disconnect"}

    with pytest.raises(Exception):
        asyncio.run(
            response({"type": "http", "asgi": {"spec_version": "2.4"}}, receive, send)
        )
    assert handles[0].closed
