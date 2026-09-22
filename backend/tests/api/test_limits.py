import asyncio

import pytest

from pkdb.api.limits import UploadLimits


@pytest.mark.parametrize("path", ["/api/v2/studies/TEST", "/mcp/"])
def test_counted_chunks_reject_a_body_without_content_length(path):
    messages = iter(
        [
            {"type": "http.request", "body": b"1234", "more_body": True},
            {"type": "http.request", "body": b"5678", "more_body": False},
        ]
    )
    sent = []

    async def receive():
        return next(messages)

    async def send(message):
        sent.append(message)

    async def consume(scope, receive, send):
        while (await receive()).get("more_body"):
            pass

    middleware = UploadLimits(consume, max_bytes=6, concurrency=1)
    asyncio.run(
        middleware(
            {"type": "http", "method": "POST", "path": path, "headers": []},
            receive,
            send,
        )
    )
    assert sent[0]["status"] == 413
    assert middleware.slots.acquire(blocking=False)


def test_admission_limit_rejects_without_reading_body():
    sent = []

    async def unexpected(*args):
        pytest.fail("Over-capacity request must not reach application or read body")

    async def send(message):
        sent.append(message)

    middleware = UploadLimits(unexpected, max_bytes=100, concurrency=1)
    middleware.slots.acquire()
    asyncio.run(
        middleware({"type": "http", "method": "PUT", "headers": []}, unexpected, send)
    )
    assert sent[0]["status"] == 503
    assert (b"retry-after", b"1") in sent[0]["headers"]


@pytest.mark.parametrize("path", ["/mcp", "/mcp/"])
def test_mcp_discovery_does_not_compete_for_upload_slots(path):
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"{}"}

    async def send(message):
        sent.append(message)

    async def consume(scope, receive, send):
        assert (await receive())["body"] == b"{}"
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = UploadLimits(consume, max_bytes=100, concurrency=1)
    middleware.slots.acquire()
    asyncio.run(
        middleware(
            {"type": "http", "method": "POST", "path": path, "headers": []},
            receive,
            send,
        )
    )
    assert sent[0]["status"] == 204
    assert not middleware.slots.acquire(blocking=False)


def test_cancelled_request_releases_admission_slot():
    async def cancelled(*args):
        raise asyncio.CancelledError

    middleware = UploadLimits(cancelled, max_bytes=100, concurrency=1)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            middleware(
                {"type": "http", "method": "POST", "headers": []}, cancelled, cancelled
            )
        )
    assert middleware.slots.acquire(blocking=False)
