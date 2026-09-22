import math

from fastapi import APIRouter, HTTPException, Request

from pkdb.api.reads import query_spec
from pkdb.db.analysis import ENTITIES

router = APIRouter(prefix="/api/v1")


@router.get("/pkdata/{entity}/")
def analysis_rows(entity: str, request: Request):
    if entity not in ENTITIES:
        raise HTTPException(404, "Not found")
    actor = request.app.state.principal(request, required=False)
    query = query_spec(request, ENTITIES[entity], analysis=True)
    try:
        spec, actor = saved_selection(request, actor)
        page = request.app.state.analysis.search(entity, query, actor, filter_spec=spec)
    except ValueError:
        raise HTTPException(400, "Invalid query parameters") from None
    if query.page > 1 and not page.items:
        raise HTTPException(404, "Invalid page")
    return {
        "current_page": query.page,
        "last_page": max(1, math.ceil(page.count / query.page_size)),
        "next_page_url": str(request.url.include_query_params(page=page.next))
        if page.next
        else None,
        "prev_page_url": str(request.url.include_query_params(page=page.previous))
        if page.previous
        else None,
        "data": {"count": page.count, "data": page.items},
    }


def saved_selection(request, actor):
    from uuid import UUID

    from pkdb.schemas.filters import FilterSpec
    from pkdb.services.authorization import AuthorizationDenied

    raw = request.query_params.get("uuid")
    if raw is None:
        return None, actor
    try:
        identifier = UUID(raw)
        service = request.app.state.exports
        with service.session_factory() as session:
            spec, current = service.load_filter(identifier, actor, session)
        if not isinstance(spec, FilterSpec):
            raise ValueError("Expected multi-entity filter")
        return spec, current
    except ValueError:
        raise HTTPException(400, "Invalid saved filter") from None
    except LookupError:
        raise HTTPException(404, "Saved filter unavailable") from None
    except AuthorizationDenied:
        raise HTTPException(403, "Saved filter unavailable") from None


@router.get("/filter/")
def filter_studies(request: Request):
    from urllib.parse import urlencode

    from pkdb.schemas.filters import FilterSpec

    actor = request.app.state.principal(request, required=False)
    params = request.query_params
    if params.get("format", "json") != "json":
        raise HTTPException(404, "Unsupported response format")
    concise = params.get("concise", "true")
    if concise not in {"true", "false"} or params.get("download", "false") not in {
        "true",
        "false",
    }:
        raise HTTPException(400, "Invalid filter options")
    entities = {
        "studies",
        "groups",
        "individuals",
        "interventions",
        "outputs",
        "subsets",
    }
    for key in params:
        if key in {"concise", "download", "format"}:
            continue
        prefix, separator, field = key.partition("__")
        if prefix not in entities or not separator or not field:
            raise HTTPException(400, "Invalid filter parameters")
    queries = {}
    for entity in entities:
        values = [
            (key[len(entity) + 2 :], value)
            for key, value in params.multi_items()
            if key.startswith(entity + "__")
        ]
        if values:
            scope = {**request.scope, "query_string": urlencode(values).encode()}
            queries[entity] = query_spec(Request(scope), entity)
    spec = FilterSpec.model_validate({"queries": queries, "concise": concise == "true"})
    try:
        identifier = request.app.state.exports.create_filter(spec, actor)
        if params.get("download") == "true":
            return download_response(request.app.state.exports, identifier, actor)
        return request.app.state.exports.overview(identifier, actor)
    except ValueError:
        raise HTTPException(400, "Invalid filter parameters") from None


def download_response(service, identifier, actor):
    from starlette.concurrency import run_in_threadpool

    from pkdb.api.streaming import ClosingStreamingResponse
    from pkdb.services.exports import ExportBusy, ExportLimit

    iterator = service.stream_export(identifier, "zip", actor)
    try:
        first = next(iterator)
    except ExportBusy:
        raise HTTPException(
            503, "Export capacity reached", headers={"Retry-After": "1"}
        ) from None
    except ExportLimit as error:
        raise HTTPException(413, str(error)) from None

    async def chunks():
        yield first
        while (chunk := await run_in_threadpool(next, iterator, None)) is not None:
            yield chunk

    return ClosingStreamingResponse(
        chunks(),
        close=iterator.close,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": "attachment; filename=pkdata.zip"},
    )
