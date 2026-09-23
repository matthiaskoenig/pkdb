"""Legacy DRF JSON suffix aliases reuse the exact endpoint and dependencies."""

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute


def include_legacy_router(app: FastAPI, router: APIRouter) -> None:
    # Register suffixes first: /studies/{sid}/ otherwise consumes SID.json/.
    for route in router.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/v1/"):
            continue
        for ending in (".json", ".json/"):
            app.add_api_route(
                route.path.rstrip("/") + ending,
                route.endpoint,
                methods=sorted(route.methods) if route.methods else None,
                status_code=route.status_code,
                response_model=route.response_model,
                response_class=route.response_class,
                dependencies=route.dependencies,
                responses=route.responses,
                include_in_schema=False,
                response_model_include=route.response_model_include,
                response_model_exclude=route.response_model_exclude,
                response_model_by_alias=route.response_model_by_alias,
                response_model_exclude_unset=route.response_model_exclude_unset,
                response_model_exclude_defaults=route.response_model_exclude_defaults,
                response_model_exclude_none=route.response_model_exclude_none,
            )
    app.include_router(router)
