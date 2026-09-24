from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from starlette.concurrency import run_in_threadpool

from pkdb.schemas.data import DataPage, DataQuery, ScientificRecord
from pkdb.schemas.queries import QuerySpec
from pkdb_server.db.read import read_study
from pkdb_server.mcp.authentication import DatabaseTokenVerifier
from pkdb_server.services.authentication import AuthenticationFailed
from pkdb_server.services.authorization import AuthorizationDenied
from pkdb_server.services.quotas import QuotaExceeded, QuotaService


def create_mcp(queries, session_factory, settings):
    authentication = DatabaseTokenVerifier(session_factory)
    server = FastMCP("PK-DB", auth=authentication, mask_error_details=True)

    def execute(operation, *args):
        from threading import Event, Thread

        quotas = QuotaService(session_factory, settings)
        lease = None
        stop = Event()
        heartbeat = None
        try:
            principal = authentication.current_principal()
            if settings.rate_limits_enabled:
                quotas.charge(principal, "mcp", "read")
                lease = quotas.acquire(principal, "mcp", "read")

            def renew():
                while not stop.wait(30):
                    quotas.renew(lease)

            if lease:
                heartbeat = Thread(target=renew, daemon=True)
                heartbeat.start()
            return operation(principal, *args)
        except QuotaExceeded as error:
            raise ToolError(
                f"Request quota exceeded; retry after {error.retry_after} seconds"
            ) from None
        except AuthenticationFailed, AuthorizationDenied:
            raise ToolError("Action not permitted") from None
        except LookupError:
            raise ToolError("Not found") from None
        except ValueError:
            raise ToolError("Invalid request") from None
        finally:
            stop.set()
            if heartbeat:
                heartbeat.join()
            if lease:
                quotas.release(lease)

    def search(principal, query):
        if query.entity != "studies":
            raise ValueError("Only study search is available")
        return queries.search(query, principal).model_dump(mode="json")

    def query_entities(principal, query):
        page = queries.search(query, principal)
        return DataPage[ScientificRecord].from_page(page, query).model_dump(mode="json")

    def get(principal, sid):
        return read_study(sid, principal, session_factory).model_dump(mode="json")

    @server.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    async def search_studies(query: QuerySpec) -> dict:
        """Search authorized studies with bounded predicates and pagination."""
        return await run_in_threadpool(execute, search, query)

    @server.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    async def get_study(sid: str) -> dict:
        """Read the complete canonical definition of an authorized study."""
        return await run_in_threadpool(execute, get, sid)

    @server.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    async def query_data(query: DataQuery) -> dict:
        """Query authorized measurements, studies and related entities."""
        return await run_in_threadpool(execute, query_entities, query)

    return server
