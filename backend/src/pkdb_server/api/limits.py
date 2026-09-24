"""Bound streamed request bytes and admit only a fixed number of uploads."""

from threading import BoundedSemaphore

from starlette.responses import JSONResponse


class BodyLimitExceeded(Exception):
    pass


class UploadLimits:
    def __init__(
        self, app, max_bytes: int, concurrency: int, admission_enabled: bool = True
    ):
        self.app = app
        self.admission_enabled = admission_enabled
        self.max_bytes = max_bytes
        self.slots = BoundedSemaphore(concurrency)

    async def __call__(self, scope, receive, send):
        upload = scope["type"] == "http" and scope["method"] in {"POST", "PUT", "PATCH"}
        if not upload:
            await self.app(scope, receive, send)
            return
        # MCP uses POST for discovery and reads as well as uploads. Its tool
        # executor holds operation-specific quota leases; transport requests
        # must not compete for upload slots, but still need the byte limit.
        path = scope.get("path", "")
        admission = (
            self.admission_enabled
            and not scope.get("state", {}).get("authenticated_unthrottled", False)
            and not (path == "/mcp" or path.startswith("/mcp/"))
        )
        if admission and not self.slots.acquire(blocking=False):
            await JSONResponse(
                {"detail": "Upload capacity reached"},
                status_code=503,
                headers={"Retry-After": "1"},
            )(scope, receive, send)
            return
        size = 0

        async def bounded_receive():
            nonlocal size
            message = await receive()
            if message["type"] == "http.request":
                size += len(message.get("body", b""))
                if size > self.max_bytes:
                    scope.setdefault("state", {}).update(
                        upload_limit_actual=size, upload_limit_maximum=self.max_bytes
                    )
                    raise BodyLimitExceeded
            return message

        try:
            headers = dict(scope.get("headers", []))
            if b"content-length" in headers:
                try:
                    length = int(headers[b"content-length"])
                except ValueError:
                    length = -1
                if length < 0:
                    await JSONResponse(
                        {"detail": "Invalid content length"}, status_code=400
                    )(scope, receive, send)
                    return
                if length > self.max_bytes:
                    scope.setdefault("state", {}).update(
                        upload_limit_actual=length, upload_limit_maximum=self.max_bytes
                    )
                    raise BodyLimitExceeded
            await self.app(scope, bounded_receive, send)
        except BodyLimitExceeded:
            await JSONResponse(
                {"detail": "Upload exceeds configured byte limit"}, status_code=413
            )(scope, receive, send)
        finally:
            if admission:
                self.slots.release()
