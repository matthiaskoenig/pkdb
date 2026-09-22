"""Browser token authentication works only for explicitly configured origins."""

from fastapi.testclient import TestClient

from pkdb.app import create_app
from pkdb.config import Settings


def test_explicit_browser_origin_can_send_authorization(
    ingestion_context, session_factory
):
    ingestion, _ = ingestion_context
    settings = Settings(
        database_url=session_factory.kw["bind"].url.render_as_string(
            hide_password=False
        ),
        file_root=ingestion.file_store.root,
        cors_origins=["http://localhost:8080"],
    )
    with TestClient(create_app(settings)) as client:
        response = client.options(
            "/api/v1/studies/",
            headers={
                "Origin": "http://localhost:8080",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert response.status_code == 200
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:8080"
        )
        assert "access-control-allow-credentials" not in response.headers
        response = client.options(
            "/api/v1/studies/",
            headers={
                "Origin": "https://unconfigured.test",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers
        response = client.get(
            "/api/v1/studies/", headers={"Origin": "http://localhost:8080"}
        )
        assert response.status_code == 200
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:8080"
        )
        response = client.post(
            "/api/v2/studies/validate",
            content=b"{}",
            headers={
                "Origin": "http://localhost:8080",
                "Content-Length": str(settings.upload_max_bytes + 1),
            },
        )
        assert response.status_code == 413
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:8080"
        )


def test_existing_frontend_api_documentation_link_resolves(client):
    response = client.get("/api/v1/swagger/")
    assert response.status_code == 200
    assert "swagger-ui" in response.text
