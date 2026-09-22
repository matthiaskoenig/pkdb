import socket
import threading
import time
from contextlib import asynccontextmanager

import httpx
import pytest
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from pkdb.app import create_app
from pkdb.config import Settings
from pkdb.db.models.users import User
from pkdb.services.authentication import issue_token


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mcp_http(ingestion_context, session_factory):
    ingestion, principal = ingestion_context
    app = create_app(
        Settings(
            database_url=session_factory.kw["bind"].url.render_as_string(
                hide_password=False
            ),
            file_root=ingestion.file_store.root,
        )
    )
    with session_factory.begin() as session:
        token = issue_token(session.get(User, principal.user_id), session)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    url = f"http://127.0.0.1:{sock.getsockname()[1]}"
    server = uvicorn.Server(
        uvicorn.Config(
            app, log_level="critical", lifespan="on", timeout_graceful_shutdown=5
        )
    )
    thread = threading.Thread(
        target=server.run, kwargs={"sockets": [sock]}, daemon=True
    )
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started
        yield app, url, token
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        assert not thread.is_alive(), "MCP HTTP server did not shut down"


@asynccontextmanager
async def connect(url, token):
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, timeout=15
    ) as http:
        async with streamable_http_client(url + "/mcp/", http_client=http) as (
            read,
            write,
            _,
        ):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session


@pytest.fixture
def mcp_connect():
    return connect
