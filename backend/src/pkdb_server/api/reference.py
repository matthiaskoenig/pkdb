"""Task-oriented researcher reference and a complete deployment reference."""

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

TAGS = [
    {
        "name": "Data",
        "description": "Find studies, query measurements, and download data.",
    },
    {
        "name": "Curation",
        "description": "Validate and atomically upload studies through REST.",
    },
    {"name": "Vocabulary", "description": "Scientific terms and external annotations."},
    {"name": "Authentication", "description": "Sign in, register, and recover access."},
    {
        "name": "My account",
        "description": "Profile, email addresses, sessions, and API keys.",
    },
    {"name": "System", "description": "Server capabilities and deployment health."},
    {
        "name": "Administration",
        "description": "Manage accounts, roles, and study access.",
    },
    {
        "name": "Browser support",
        "description": "First-party browser search and presentation contracts.",
    },
    {
        "name": "Legacy compatibility",
        "description": "Deprecated routes, enabled only by PKDB_LEGACY_API_ENABLED.",
    },
]


def category(path: str, method: str) -> str:
    if path.startswith(("/accounts/", "/api-token-auth", "/api/v1/_")):
        return "Legacy compatibility"
    if path.startswith("/api/v1/admin/"):
        return "Administration"
    if path.startswith("/api/v1/auth/"):
        return "Authentication"
    if path.startswith("/api/v1/me"):
        return "My account"
    if path == "/api/v2/vocabulary":
        return "Vocabulary"
    if path.startswith("/health/") or path == "/api/v2/capabilities":
        return "System"
    if path.startswith("/api/v2/studies") and method in {"put", "post"}:
        return "Curation"
    if path.startswith("/api/v2/"):
        return "Data"
    return "Browser support"


def install_reference(app: FastAPI) -> None:
    @app.get("/docs/all", include_in_schema=False)
    def full_reference():
        return get_swagger_ui_html(
            openapi_url="/openapi/all.json", title="PK-DB complete REST API"
        )

    @app.get("/openapi/all.json", include_in_schema=False)
    def full_schema():
        return schema(full=True)

    def schema(*, full=False):
        result = get_openapi(
            title=app.title,
            version=app.version,
            description="Researcher REST API. MCP exposes read tools only at /mcp/. See /docs/all for browser and administration operations.",
            routes=app.routes,
            tags=TAGS if full else TAGS[:6],
        )
        paths = {}
        for path, operations in result["paths"].items():
            selected = {}
            for method, operation in operations.items():
                tag = category(path, method)
                if not full and (
                    tag in {"Browser support", "Administration", "Legacy compatibility"}
                    or path.startswith("/health/")
                ):
                    continue
                operation["tags"] = [tag]
                if tag == "Legacy compatibility":
                    operation["deprecated"] = True
                selected[method] = operation
            if selected:
                paths[path] = selected
        result["paths"] = paths
        return result

    def researcher_schema():
        if app.openapi_schema is None:
            app.openapi_schema = schema()
        return app.openapi_schema

    # FastAPI documents assigning a custom zero-argument OpenAPI callable.
    app.openapi = researcher_schema  # ty: ignore[invalid-assignment]
