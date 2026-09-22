from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from starlette.concurrency import run_in_threadpool

from pkdb.db.read import read_study
from pkdb.mcp.authentication import DatabaseTokenVerifier
from pkdb.schemas.bundle import StagedBundle
from pkdb.schemas.queries import QuerySpec
from pkdb.schemas.validation import StudyValidationError, fail
from pkdb.services.authentication import AuthenticationFailed
from pkdb.services.authorization import AuthorizationDenied
from pkdb.services.bundles import materialize_bundle


def create_mcp(ingestion, queries, file_store, session_factory):
    authentication = DatabaseTokenVerifier(session_factory)
    server = FastMCP("PK-DB", auth=authentication, mask_error_details=True)

    def execute(operation, *args):
        try:
            return operation(authentication.current_principal(), *args)
        except StudyValidationError as error:
            return {**error.report.model_dump(mode="json"), "valid": False}
        except AuthenticationFailed, AuthorizationDenied:
            raise ToolError("Action not permitted") from None
        except LookupError:
            raise ToolError("Not found") from None
        except ValueError:
            raise ToolError("Invalid request") from None

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
        return {**prepared.report.model_dump(mode="json"), "valid": True}

    def replace(principal, sid, bundle):
        if str(bundle.study.get("sid")) != sid:
            fail("sid_mismatch", "Tool SID must match study SID")
        with materialize_bundle(
            bundle, principal, file_store, ingestion.settings
        ) as source:
            return ingestion.replace(source, principal).model_dump(mode="json")

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
