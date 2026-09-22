import pytest


@pytest.mark.anyio
async def test_only_explicit_tools_are_exposed(mcp_http, mcp_connect):
    _, url, token = mcp_http
    async with mcp_connect(url, token) as client:
        result = await client.list_tools()
        assert {tool.name for tool in result.tools} == {
            "search_studies",
            "get_study",
            "validate_study",
            "replace_study",
        }


@pytest.mark.anyio
async def test_tools_share_rest_validation_and_atomic_publication(
    mcp_http, mcp_connect, valid_bundle
):
    import json

    import httpx

    _, url, token = mcp_http
    bundle = {"study": valid_bundle.study, "reference": valid_bundle.reference}
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=url, headers=headers) as rest:
        response = await rest.post(
            "/api/v2/studies/validate",
            data={
                "study": json.dumps(bundle["study"]),
                "reference": json.dumps(bundle["reference"]),
            },
        )
        assert response.status_code == 200
        async with mcp_connect(url, token) as client:
            report = await client.call_tool("validate_study", {"bundle": bundle})
            assert not report.isError
            assert report.structuredContent == response.json()
            published = await client.call_tool(
                "replace_study", {"sid": valid_bundle.study["sid"], "bundle": bundle}
            )
            assert not published.isError
            assert published.structuredContent["created"] is True
            study = await client.call_tool(
                "get_study", {"sid": valid_bundle.study["sid"]}
            )
            assert not study.isError
            assert (
                study.structuredContent
                == (
                    await rest.get("/api/v2/studies/" + valid_bundle.study["sid"])
                ).json()
            )
            matches = await client.call_tool(
                "search_studies", {"query": {"entity": "studies"}}
            )
            assert matches.structuredContent["count"] == 1
            before = study.structuredContent
            bundle["study"]["outputset"]["outputs"] = False
            report = await client.call_tool(
                "replace_study", {"sid": valid_bundle.study["sid"], "bundle": bundle}
            )
            assert report.structuredContent["valid"] is False
            assert report.structuredContent["error_count"] == 1
            assert (
                await client.call_tool("get_study", {"sid": valid_bundle.study["sid"]})
            ).structuredContent == before


@pytest.mark.anyio
async def test_transport_requires_current_bearer_token(mcp_http, session_factory):
    from datetime import UTC, datetime

    import httpx
    from sqlalchemy import update

    from pkdb.db.models.users import Token

    _, url, token = mcp_http
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1"},
        },
    }
    async with httpx.AsyncClient(
        base_url=url, headers={"Accept": "application/json, text/event-stream"}
    ) as client:
        assert (await client.post("/mcp/", json=payload)).status_code == 401
        assert (
            await client.post(
                "/mcp/", json=payload, headers={"Authorization": f"Token {token}"}
            )
        ).status_code == 401
        assert (
            await client.post(
                "/mcp/", json=payload, headers={"Authorization": f"Bearer {token}"}
            )
        ).status_code == 200
        initialized = await client.post(
            "/mcp/", json=payload, headers={"Authorization": f"Bearer {token}"}
        )
        session_id = initialized.headers["mcp-session-id"]
        with session_factory.begin() as session:
            session.execute(update(Token).values(revoked_at=datetime.now(UTC)))
        response = await client.post(
            "/mcp/",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            headers={"Authorization": f"Bearer {token}", "Mcp-Session-Id": session_id},
        )
        assert response.status_code == 401
        assert (
            await client.post(
                "/mcp/", json=payload, headers={"Authorization": f"Bearer {token}"}
            )
        ).status_code == 401


@pytest.mark.anyio
async def test_staged_handles_require_owner_and_never_accept_paths(
    mcp_http, mcp_connect, valid_bundle, session_factory
):
    import httpx

    from pkdb.db.models.users import User
    from pkdb.services.authentication import issue_token

    _, url, token = mcp_http
    async with httpx.AsyncClient(
        base_url=url, headers={"Authorization": f"Bearer {token}"}
    ) as rest:
        response = await rest.post(
            "/api/v2/files", files={"file": ("figure.png", b"image bytes")}
        )
        assert response.status_code == 201
        staged = response.json()
        assert set(staged) == {"id", "name", "size", "sha256", "expires_at"}
    bundle = {
        "study": valid_bundle.study,
        "reference": valid_bundle.reference,
        "handles": [staged["id"]],
    }
    with session_factory.begin() as session:
        other = User(username="other", role="curator", active=True)
        session.add(other)
        session.flush()
        other_token = issue_token(other, session)
    async with mcp_connect(url, other_token) as client:
        response = await client.call_tool("validate_study", {"bundle": bundle})
        assert response.isError
        assert "Action not permitted" in response.content[0].text
    async with mcp_connect(url, token) as client:
        response = await client.call_tool(
            "replace_study", {"sid": valid_bundle.study["sid"], "bundle": bundle}
        )
        assert not response.isError
        study = await client.call_tool("get_study", {"sid": valid_bundle.study["sid"]})
        assert study.structuredContent["attachments"][0]["name"] == "figure.png"
        response = await client.call_tool(
            "validate_study", {"bundle": {**bundle, "handles": ["/etc/passwd"]}}
        )
        assert response.isError
        response = await client.call_tool(
            "validate_study", {"bundle": {**bundle, "files": {"secret": "/etc/passwd"}}}
        )
        assert response.isError


@pytest.mark.anyio
async def test_blocking_scientific_work_keeps_http_responsive(
    mcp_http, mcp_connect, valid_bundle, monkeypatch
):
    import asyncio
    import threading

    import anyio
    import httpx

    app, url, token = mcp_http
    entered, release = threading.Event(), threading.Event()
    original = app.state.ingestion.validate

    def blocked(*args):
        entered.set()
        assert release.wait(timeout=5)
        return original(*args)

    monkeypatch.setattr(app.state.ingestion, "validate", blocked)
    async with mcp_connect(url, token) as client:
        task = asyncio.create_task(
            client.call_tool(
                "validate_study",
                {
                    "bundle": {
                        "study": valid_bundle.study,
                        "reference": valid_bundle.reference,
                    }
                },
            )
        )
        try:
            assert await anyio.to_thread.run_sync(entered.wait, 2)
            async with httpx.AsyncClient(base_url=url, timeout=1) as rest:
                assert (await rest.get("/health/live")).status_code == 200
        finally:
            release.set()
        assert not (await task).isError


@pytest.mark.anyio
async def test_concurrent_calls_keep_principals_separate(
    mcp_http, mcp_connect, valid_bundle, session_factory
):
    import asyncio

    from sqlalchemy import select

    from pkdb.db.models.users import User
    from pkdb.schemas.security import Principal
    from pkdb.services.authentication import issue_token

    app, url, token = mcp_http
    with session_factory.begin() as session:
        other = User(username="other", role="curator", active=True)
        session.add(other)
        session.flush()
        other_token = issue_token(other, session)
        other_principal = Principal(
            user_id=other.id, username=other.username, role=other.role
        )
    valid_bundle.study["access"] = "private"
    with session_factory() as session:
        owner = session.scalars(select(User).where(User.username == "curator")).one()
        owner_principal = Principal(
            user_id=owner.id, username=owner.username, role=owner.role
        )
    app.state.ingestion.replace(valid_bundle, owner_principal)
    second = valid_bundle.model_copy(deep=True)
    second.study.update(
        sid="SECOND",
        name="Second",
        reference="R2",
        creator="other",
        curators=[],
        collaborators=[],
    )
    second.reference.update(sid="R2", name="R2")
    app.state.ingestion.replace(second, other_principal)
    async with (
        mcp_connect(url, token) as first,
        mcp_connect(url, other_token) as second_client,
    ):
        results = await asyncio.gather(
            first.call_tool("search_studies", {"query": {"entity": "studies"}}),
            second_client.call_tool("search_studies", {"query": {"entity": "studies"}}),
        )
        assert [
            [row["sid"] for row in result.structuredContent["items"]]
            for result in results
        ] == [[valid_bundle.study["sid"]], ["SECOND"]]
        assert (await first.call_tool("get_study", {"sid": "SECOND"})).isError


@pytest.mark.anyio
async def test_cancelled_validation_releases_capacity_and_shuts_down(
    mcp_http, mcp_connect, valid_bundle, monkeypatch, session_factory
):
    import asyncio
    import threading

    import anyio
    from sqlalchemy import func, select

    from pkdb.db.models.studies import Study

    app, url, token = mcp_http
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    original = app.state.ingestion.validate

    def blocked(*args):
        entered.set()
        assert release.wait(timeout=5)
        try:
            return original(*args)
        finally:
            finished.set()

    monkeypatch.setattr(app.state.ingestion, "validate", blocked)
    async with mcp_connect(url, token) as client:
        task = asyncio.create_task(
            client.call_tool(
                "validate_study",
                {
                    "bundle": {
                        "study": valid_bundle.study,
                        "reference": valid_bundle.reference,
                    }
                },
            )
        )
        try:
            assert await anyio.to_thread.run_sync(entered.wait, 2)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        finally:
            release.set()
        assert await anyio.to_thread.run_sync(finished.wait, 2)
        assert len((await client.list_tools()).tools) == 4
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Study)) == 0


@pytest.mark.anyio
async def test_staged_file_integrity_is_checked(
    mcp_http, mcp_connect, valid_bundle, session_factory
):
    from uuid import UUID

    import httpx

    from pkdb.db.models.files import StoredFile

    app, url, token = mcp_http
    async with httpx.AsyncClient(
        base_url=url, headers={"Authorization": f"Bearer {token}"}
    ) as client:
        response = await client.post(
            "/api/v2/files", files={"file": ("figure.png", b"original")}
        )
        handle = response.json()["id"]
    with session_factory() as session:
        row = session.get(StoredFile, UUID(handle))
        app.state.file_store.path(row.storage_key).write_bytes(b"corrupt!")
    async with mcp_connect(url, token) as client:
        response = await client.call_tool(
            "validate_study",
            {
                "bundle": {
                    "study": valid_bundle.study,
                    "reference": valid_bundle.reference,
                    "handles": [handle],
                }
            },
        )
        assert response.structuredContent["valid"] is False
        assert response.structuredContent["issues"][0]["code"] == "source_changed"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "case,code",
    [("duplicate", "invalid_handles"), ("size", "file_limit"), ("expired", None)],
)
async def test_handle_limits_and_expiry(
    mcp_http, mcp_connect, valid_bundle, session_factory, case, code
):
    from datetime import UTC, datetime, timedelta
    from uuid import UUID

    import httpx

    from pkdb.db.models.files import StoredFile

    app, url, token = mcp_http
    async with httpx.AsyncClient(
        base_url=url, headers={"Authorization": f"Bearer {token}"}
    ) as rest:
        response = await rest.post(
            "/api/v2/files", files={"file": ("figure.png", b"bytes")}
        )
        handle = response.json()["id"]
    handles = [handle]
    if case == "duplicate":
        handles *= 2
    elif case == "size":
        app.state.ingestion.settings.upload_max_bytes = 4
    else:
        with session_factory.begin() as session:
            session.get(StoredFile, UUID(handle)).expires_at = datetime.now(
                UTC
            ) - timedelta(seconds=1)
    async with mcp_connect(url, token) as client:
        response = await client.call_tool(
            "validate_study",
            {
                "bundle": {
                    "study": valid_bundle.study,
                    "reference": valid_bundle.reference,
                    "handles": handles,
                }
            },
        )
        if code:
            assert response.structuredContent["valid"] is False
            assert response.structuredContent["issues"][0]["code"] == code
        else:
            assert response.isError
