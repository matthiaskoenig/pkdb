"""Hold shared leases until the final streaming response bytes are sent."""

import asyncio
import logging

from pkdb.schemas.security import Principal
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse

from pkdb_server.services.authentication import AuthenticationFailed
from pkdb_server.services.authorization import AuthorizationDenied
from pkdb_server.services.quotas import QuotaExceeded


class RequestQuotas:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # MCP holds streaming connections open; its tool executor accounts for
        # individual operations and leases instead of transport connections.
        path = scope.get("path", "")
        if (
            scope["type"] != "http"
            or not path.startswith(
                ("/api/", "/accounts/", "/api-token-auth/", "/media/")
            )
            or scope["method"] == "OPTIONS"
        ):
            return await self.app(scope, receive, send)
        request = Request(scope)
        quotas = request.app.state.quotas

        def acquire():
            try:
                principal = request.app.state.principal(request, required=False)
            except AuthenticationFailed, AuthorizationDenied:
                principal = Principal()
            operation = "read"
            if request.method not in {"GET", "HEAD"} and (
                "studies" in path or "upload" in path or "files" in path
            ):
                operation = "upload"
            elif "export" in path or "download" in path:
                operation = "export"
            elif "login" in path or "api-token-auth" in path:
                operation = "login"
            elif any(
                word in path
                for word in ("register", "password-reset", "resend-verification")
            ):
                operation = "register"
            ip = request.client.host if request.client else "unknown"
            quotas.charge(principal, ip, operation)
            return quotas.acquire(principal, ip, operation)

        try:
            identifier = await run_in_threadpool(acquire)
        except QuotaExceeded as exc:
            return await JSONResponse(
                {"detail": "Request quota exceeded", "code": "rate_limit"},
                status_code=429,
                headers={"Retry-After": str(exc.retry_after)},
            )(scope, receive, send)
        except SQLAlchemyError as error:
            logging.getLogger(__name__).error(
                "Quota storage unavailable (%s)", type(error).__name__
            )
            return await JSONResponse(
                {"detail": "Request capacity unavailable"},
                status_code=503,
                headers={"Retry-After": "5"},
            )(scope, receive, send)

        async def heartbeat():
            while True:
                await asyncio.sleep(30)
                await run_in_threadpool(quotas.renew, identifier)

        task = asyncio.create_task(heartbeat())
        try:
            await self.app(scope, receive, send)
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            await asyncio.shield(run_in_threadpool(quotas.release, identifier))
