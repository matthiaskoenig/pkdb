import pytest


@pytest.mark.anyio
async def test_only_explicit_tools_are_exposed(mcp_http, mcp_connect):
    _, url, token = mcp_http
    async with mcp_connect(url, token) as client:
        result = await client.list_tools()
        assert {tool.name for tool in result.tools} == {
            "search_studies",
            "get_study",
            "query_data",
        }
        assert all(tool.annotations.read_only_hint for tool in result.tools)
        assert all(tool.annotations.destructive_hint is False for tool in result.tools)


@pytest.mark.anyio
async def test_read_tools_match_rest_and_removed_tools_cannot_write(
    mcp_http, mcp_connect, valid_bundle, ingestion_context, session_factory
):
    import httpx2
    from sqlalchemy import func, select

    from pkdb_server.db.models.studies import Study

    app, url, token = mcp_http
    _, principal = ingestion_context
    app.state.ingestion.replace(valid_bundle, principal)
    sid = valid_bundle.study["sid"]
    async with (
        httpx2.AsyncClient(
            base_url=url, headers={"Authorization": f"Bearer {token}"}
        ) as rest,
        mcp_connect(url, token) as client,
    ):
        before = (await rest.get(f"/api/v2/studies/{sid}")).json()
        study = await client.call_tool("get_study", {"sid": sid})
        assert not study.is_error
        assert study.structured_content == before
        matches = await client.call_tool(
            "search_studies", {"query": {"entity": "studies"}}
        )
        assert matches.structured_content["count"] == 1
        data = await client.call_tool(
            "query_data", {"query": {"entity": "measurements"}}
        )
        assert not data.is_error
        assert data.structured_content["total"] >= 1
        assert data.structured_content["page"] == 1
        bundle = {"study": valid_bundle.study, "reference": valid_bundle.reference}
        bundle["study"]["name"] = "Must not be saved"
        for tool, arguments in (
            ("validate_study", {"bundle": bundle}),
            ("replace_study", {"sid": sid, "bundle": bundle}),
            ("replace_study", {"sid": "NEW", "bundle": bundle}),
        ):
            response = await client.call_tool(tool, arguments)
            assert response.is_error
        assert (await rest.get(f"/api/v2/studies/{sid}")).json() == before
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Study)) == 1


@pytest.mark.anyio
async def test_transport_requires_current_bearer_token(mcp_http, session_factory):
    from datetime import UTC, datetime

    import httpx2
    from sqlalchemy import update

    from pkdb_server.db.models.users import Token

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
    async with httpx2.AsyncClient(
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
async def test_blocking_query_keeps_http_responsive(mcp_http, mcp_connect, monkeypatch):
    import asyncio
    import threading

    import anyio
    import httpx2

    app, url, token = mcp_http
    entered, release = threading.Event(), threading.Event()
    original = app.state.queries.search

    def blocked(*args):
        entered.set()
        assert release.wait(timeout=5)
        return original(*args)

    monkeypatch.setattr(app.state.queries, "search", blocked)
    async with mcp_connect(url, token) as client:
        task = asyncio.create_task(
            client.call_tool(
                "search_studies",
                {"query": {"entity": "studies"}},
            )
        )
        try:
            assert await anyio.to_thread.run_sync(entered.wait, 2)
            async with httpx2.AsyncClient(base_url=url, timeout=1) as rest:
                assert (await rest.get("/health/live")).status_code == 200
        finally:
            release.set()
        assert not (await task).is_error


@pytest.mark.anyio
async def test_concurrent_calls_keep_principals_separate(
    mcp_http, mcp_connect, valid_bundle, session_factory
):
    import asyncio

    from sqlalchemy import select

    from pkdb.schemas.security import Principal
    from pkdb_server.db.models.users import User
    from pkdb_server.services.authentication import issue_token

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
            [row["sid"] for row in result.structured_content["items"]]
            for result in results
        ] == [[valid_bundle.study["sid"]], ["SECOND"]]
        assert (await first.call_tool("get_study", {"sid": "SECOND"})).is_error
        for client, expected in (
            (first, valid_bundle.study["sid"]),
            (second_client, "SECOND"),
        ):
            data = await client.call_tool(
                "query_data", {"query": {"entity": "studies"}}
            )
            assert [row["sid"] for row in data.structured_content["items"]] == [
                expected
            ]


@pytest.mark.anyio
async def test_cancelled_query_shuts_down(
    mcp_http, mcp_connect, monkeypatch, session_factory
):
    import asyncio
    import threading

    import anyio
    from sqlalchemy import func, select

    from pkdb_server.db.models.studies import Study

    app, url, token = mcp_http
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    original = app.state.queries.search

    def blocked(*args):
        entered.set()
        assert release.wait(timeout=5)
        try:
            return original(*args)
        finally:
            finished.set()

    monkeypatch.setattr(app.state.queries, "search", blocked)
    async with mcp_connect(url, token) as client:
        task = asyncio.create_task(
            client.call_tool(
                "search_studies",
                {"query": {"entity": "studies"}},
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
        assert len((await client.list_tools()).tools) == 3
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Study)) == 0
