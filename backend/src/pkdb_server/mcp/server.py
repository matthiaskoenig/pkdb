from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from starlette.concurrency import run_in_threadpool

from pkdb.schemas.bundle import StagedBundle
from pkdb.schemas.queries import QuerySpec
from pkdb.schemas.validation import StudyValidationError, fail
from pkdb_server.db.read import read_study
from pkdb_server.mcp.authentication import DatabaseTokenVerifier
from pkdb_server.services.authentication import AuthenticationFailed
from pkdb_server.services.authorization import AuthorizationDenied
from pkdb_server.services.bundles import materialize_bundle
from pkdb_server.services.quotas import QuotaExceeded, QuotaService


def create_mcp(ingestion, queries, file_store, session_factory):
    authentication = DatabaseTokenVerifier(session_factory)
    server = FastMCP("PK-DB", auth=authentication, mask_error_details=True)

    def execute(operation, *args):
        from threading import Event, Thread

        quotas = QuotaService(session_factory, ingestion.settings)
        lease = None
        stop = Event()
        heartbeat = None
        try:
            principal = authentication.current_principal()
            category = "upload" if operation in {validate, replace} else "read"
            if ingestion.settings.rate_limits_enabled:
                quotas.charge(principal, "mcp", category)
                lease = quotas.acquire(principal, "mcp", category)

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
        except StudyValidationError as error:
            return {**error.report.legacy_dict(), "valid": False}
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

    def get(principal, sid):
        return read_study(sid, principal, session_factory)

    def validate(principal, bundle):
        with materialize_bundle(
            bundle, principal, file_store, ingestion.settings
        ) as source:
            prepared = ingestion.validate(source, principal)
        return {**prepared.report.legacy_dict(), "valid": True}

    def replace(principal, sid, bundle):
        if str(bundle.study.get("sid")) != sid:
            fail("sid_mismatch", "Tool SID must match study SID")
        with materialize_bundle(
            bundle, principal, file_store, ingestion.settings
        ) as source:
            result = ingestion.replace(source, principal)
            return {
                **result.model_dump(mode="json"),
                "warnings": [issue.legacy_dict() for issue in result.warnings],
            }

    @server.tool
    async def search_studies(query: QuerySpec) -> dict:
        """Search authorized studies with bounded predicates and pagination."""
        return await run_in_threadpool(execute, search, query)

    @server.tool
    async def get_study(sid: str) -> dict:
        """Read the complete canonical definition of an authorized study."""
        return await run_in_threadpool(execute, get, sid)

    @server.tool
    async def validate_study(bundle: StagedBundle) -> dict:
        """Validate a complete study using owned staged handles; publish nothing."""
        return await run_in_threadpool(execute, validate, bundle)

    @server.tool
    async def replace_study(sid: str, bundle: StagedBundle) -> dict:
        """Atomically replace a study; invalid uploads retain its prior publication."""
        return await run_in_threadpool(execute, replace, sid, bundle)

    return server
