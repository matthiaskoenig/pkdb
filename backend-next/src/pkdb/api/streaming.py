"""Close owned resources even when the body iterator never starts."""

from anyio import CancelScope
from starlette.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse


class ClosingStreamingResponse(StreamingResponse):
    def __init__(self, content, *, close, **kwargs):
        super().__init__(content, **kwargs)
        self.close_resource = close

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            with CancelScope(shield=True):
                await run_in_threadpool(self.close_resource)
