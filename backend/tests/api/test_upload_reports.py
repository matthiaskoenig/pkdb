"""Report negotiation also covers failures emitted before endpoint dispatch."""

import json

import pytest
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from pkdb_server.api.upload_reports import UploadReports


def application(status=422, payload=None, headers=None, state=None, crash=False):
    async def app(scope, receive, send):
        scope["state"].update(state or {})
        if crash:
            raise RuntimeError("secret operator traceback")
        await JSONResponse(
            payload or {"detail": "Rejected"}, status_code=status, headers=headers
        )(scope, receive, send)

    return TestClient(UploadReports(app))


@pytest.mark.parametrize("version", [None, "1"])
def test_legacy_response_unchanged(version):
    payload = {
        "issues": [
            {
                "code": "bad",
                "message": "Bad source",
                "source": None,
                "severity": "error",
            }
        ],
        "error_count": 1,
        "truncated": False,
        "valid": False,
    }
    headers = {} if version is None else {"X-PKDB-Report-Version": version}
    response = application(payload=payload).put("/api/v2/studies/TEST", headers=headers)
    assert response.json() == payload
    assert response.headers["X-Request-ID"]


@pytest.mark.parametrize("status", [400, 401, 403, 409, 413, 429, 503])
def test_transport_errors_preserve_status_and_headers(status):
    response = application(
        status=status, headers={"Retry-After": "3", "WWW-Authenticate": "Bearer"}
    ).put("/api/v2/studies/TEST", headers={"X-PKDB-Report-Version": "2"})
    data = response.json()
    assert response.status_code == status
    assert response.headers["Retry-After"] == "3"
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert data["report_version"] == 2
    assert data["request_id"] == response.headers["X-Request-ID"]
    assert data["persistence"] == "not_saved"
    assert data["report"]["error_count"] == 1
    assert data["report"]["complete"] is False
    assert data["report"]["issues"][0]["suggestions"]


def test_unsupported_version_is_structured_before_dispatch():
    response = application(crash=True).put(
        "/api/v2/studies/TEST", headers={"X-PKDB-Report-Version": "9"}
    )
    assert response.status_code == 400
    assert response.json()["report_version"] == 2


def test_validate_never_claims_persistence():
    response = application(status=200, payload={"issues": [], "valid": True}).post(
        "/api/v2/studies/validate", headers={"X-PKDB-Report-Version": "2"}
    )
    assert response.json()["persistence"] == "not_attempted"


@pytest.mark.parametrize("created", [True, False])
def test_confirmed_upload_preserves_result_and_warning_details(created):
    payload = {
        "sid": "TEST",
        "created": created,
        "digest": "abc",
        "counts": {},
        "warnings": [
            {
                "code": "notice",
                "severity": "warning",
                "message": "Inspect source",
                "actual": None,
            }
        ],
    }
    response = application(status=201 if created else 200, payload=payload).put(
        "/api/v2/studies/TEST", headers={"X-PKDB-Report-Version": "2"}
    )
    data = response.json()
    assert {
        key: value for key, value in data["result"].items() if key != "warnings"
    } == {key: value for key, value in payload.items() if key != "warnings"}
    assert data["result"]["warnings"][0]["code"] == "notice"
    assert data["result"]["warnings"][0]["suggestions"]
    assert data["persistence"] == ("created" if created else "replaced")
    assert data["report"]["warning_count"] == 1
    assert data["report"]["issues"][0]["actual"] is None


def test_exception_during_save_reports_unknown_without_leaking_traceback():
    response = application(crash=True, state={"upload_save_started": True}).put(
        "/api/v2/studies/TEST", headers={"X-PKDB-Report-Version": "2"}
    )
    assert response.status_code == 500
    assert response.json()["persistence"] == "unknown"
    assert "secret" not in json.dumps(response.json())


def test_serialization_failure_after_commit_preserves_confirmed_persistence():
    response = application(
        crash=True, state={"upload_save_started": True, "upload_persistence": "created"}
    ).put("/api/v2/studies/TEST", headers={"X-PKDB-Report-Version": "2"})
    assert response.json()["persistence"] == "created"


def test_unregistered_issue_gets_endpoint_guidance_without_inventing_source():
    response = application(
        payload={
            "issues": [
                {
                    "code": "bundle_fields",
                    "message": "Exactly one study and reference are required",
                }
            ]
        },
        state={"upload_stage": "parse"},
    ).put("/api/v2/studies/TEST", headers={"X-PKDB-Report-Version": "2"})
    issue = response.json()["report"]["issues"][0]
    assert issue["category"] == "parsing"
    assert issue["stage"] == "parse"
    assert "exactly one study" in issue["suggestions"][0]["message"]
    assert issue["source"] is None


def test_request_schema_errors_keep_locations_but_never_raw_input():
    response = application(
        payload={
            "detail": [
                {
                    "type": "missing",
                    "loc": ["body", "study", "sid"],
                    "input": {"password": "secret"},
                    "msg": "private content",
                },
                {
                    "type": "string_type",
                    "loc": ["body", "reference", "authors", 0],
                    "input": "secret",
                },
            ]
        }
    ).put("/api/v2/studies/TEST", headers={"X-PKDB-Report-Version": "2"})
    report = response.json()["report"]
    assert report["error_count"] == 2
    assert report["complete"] is False
    by_field = {issue["field"]: issue for issue in report["issues"]}
    assert by_field["sid"]["expected"] == {"required": True}
    assert by_field["0"]["context"]["request_location"] == [
        "body",
        "reference",
        "authors",
        0,
    ]
    assert by_field["0"]["expected"] == {"type": "string"}
    assert all(issue["source"] is None for issue in report["issues"])
    assert "secret" not in response.text
    assert "private content" not in response.text


@pytest.mark.parametrize("status", [429, 503])
def test_retry_guidance_is_available_in_json_and_header(status):
    response = application(status=status, headers={"Retry-After": "30"}).put(
        "/api/v2/studies/TEST", headers={"X-PKDB-Report-Version": "2"}
    )
    issue = response.json()["report"]["issues"][0]
    assert issue["code"] == ("rate_limit" if status == 429 else "capacity_unavailable")
    assert issue["category"] == "limit"
    assert issue["context"]["retry_after"] == response.headers["Retry-After"] == "30"
