import json

import pytest
from sqlalchemy import func, select

from pkdb_server.db.models.studies import Study


def multipart(bundle):
    return {
        "files": {
            "study": (None, json.dumps(bundle.study), "application/json"),
            "reference": (None, json.dumps(bundle.reference), "application/json"),
        }
    }


def test_validation_does_not_publish(
    client, creator_headers, valid_bundle, session_factory
):
    response = client.post(
        "/api/v2/studies/validate", headers=creator_headers, **multipart(valid_bundle)
    )
    assert response.status_code == 200, response.text
    assert response.json()["valid"] is True
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Study)) == 0


def test_create_replace_and_read(client, creator_headers, valid_bundle):
    url = "/api/v2/studies/" + valid_bundle.study["sid"]
    assert (
        client.put(url, headers=creator_headers, **multipart(valid_bundle)).status_code
        == 201
    )
    assert (
        client.put(url, headers=creator_headers, **multipart(valid_bundle)).status_code
        == 200
    )
    response = client.get(url, headers=creator_headers)
    assert response.status_code == 200
    assert response.json()["sid"] == valid_bundle.study["sid"]


def test_missing_credentials_is_unauthorized(client, valid_bundle):
    assert (
        client.post("/api/v2/studies/validate", **multipart(valid_bundle)).status_code
        == 401
    )


def test_sid_mismatch_is_rejected(client, creator_headers, valid_bundle):
    response = client.put(
        "/api/v2/studies/WRONG", headers=creator_headers, **multipart(valid_bundle)
    )
    assert response.status_code == 422


def test_bad_json_is_structured_error(client, creator_headers):
    response = client.post(
        "/api/v2/studies/validate",
        headers=creator_headers,
        files={
            "study": (None, "{invalid", "application/json"),
            "reference": (None, "{}", "application/json"),
        },
    )
    assert response.status_code == 422
    assert response.json()["valid"] is False


def test_health_checks(client):
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200


def test_workbook_attachment_keeps_its_format(client, creator_headers, valid_bundle):
    import io

    import openpyxl

    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Results"
    sheet.append(["comment"])
    sheet.append(["mean"])
    sheet.append([2.0])
    source = io.BytesIO()
    book.save(source)
    valid_bundle.study["outputset"]["outputs"][0].update(
        source="Results", mean="col==mean"
    )
    response = client.post(
        "/api/v2/studies/validate",
        headers=creator_headers,
        files=[
            ("study", (None, json.dumps(valid_bundle.study), "application/json")),
            (
                "reference",
                (None, json.dumps(valid_bundle.reference), "application/json"),
            ),
            (
                "files",
                (
                    "Example.xlsx",
                    source.getvalue(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            ),
        ],
    )
    assert response.status_code == 200, response.text


@pytest.mark.parametrize(
    "path,value",
    [
        (
            ("dataset",),
            {"data": [{"name": "bad", "data_type": "scatter", "subsets": None}]},
        ),
        (
            ("dataset",),
            {"data": [{"name": "bad", "data_type": "scatter", "subsets": [None]}]},
        ),
        (("groupset", "groups", 0, "characteristica"), [None]),
        (("groupset", "groups", 0, "name"), []),
        (("outputset", "outputs", 0, "image"), {"name": "bad"}),
        (("outputset", "outputs", 0, "subset"), 3),
        (("curators",), 1),
        (("comments",), 1),
        (("descriptions",), "not a list"),
        (("name",), []),
        (("groupset",), []),
        (("outputset", "outputs"), False),
        (("outputset", "outputs", 0, "mean"), float("inf")),
    ],
)
def test_malformed_nested_upload_is_structured_and_keeps_publication(
    client, creator_headers, valid_bundle, path, value
):
    url = "/api/v2/studies/" + valid_bundle.study["sid"]
    assert (
        client.put(url, headers=creator_headers, **multipart(valid_bundle)).status_code
        == 201
    )
    before = client.get(url, headers=creator_headers).json()
    target = valid_bundle.study
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    response = client.put(url, headers=creator_headers, **multipart(valid_bundle))
    assert response.status_code == 422
    report = response.json()
    assert report["valid"] is False
    assert report["error_count"] >= 1
    assert report["issues"]
    assert client.get(url, headers=creator_headers).json() == before


def test_json_recursion_is_a_validation_error(client, creator_headers):
    response = client.post(
        "/api/v2/studies/validate",
        headers=creator_headers,
        files={
            "study": (None, '{"nested":' + "[" * 2000 + "0" + "]" * 2000 + "}"),
            "reference": (None, "{}"),
        },
    )
    assert response.status_code == 422
    assert response.json()["error_count"] == 1


@pytest.mark.parametrize("field", ["study_sid", "reference_sid", "group_name"])
def test_oversized_identifiers_are_validation_errors(
    client, creator_headers, valid_bundle, field
):
    original_sid = valid_bundle.study["sid"]
    assert (
        client.put(
            f"/api/v2/studies/{original_sid}",
            headers=creator_headers,
            **multipart(valid_bundle),
        ).status_code
        == 201
    )
    old = client.get(f"/api/v2/studies/{original_sid}", headers=creator_headers).json()
    value = "x" * 513
    if field == "study_sid":
        valid_bundle.study["sid"] = value
    elif field == "reference_sid":
        valid_bundle.study["reference"] = value
        valid_bundle.reference["sid"] = value
    else:
        valid_bundle.study["groupset"]["groups"][0]["name"] = value
        valid_bundle.study["outputset"]["outputs"][0]["group"] = value
    response = client.put(
        f"/api/v2/studies/{valid_bundle.study['sid']}",
        headers=creator_headers,
        **multipart(valid_bundle),
    )
    assert response.status_code == 422
    assert (
        client.get(f"/api/v2/studies/{original_sid}", headers=creator_headers).json()
        == old
    )


def test_normalized_key_overflow_is_a_validation_error(
    client, creator_headers, valid_bundle
):
    name = "x" * 502
    valid_bundle.study["interventionset"]["interventions"][0]["name"] = name
    valid_bundle.study["outputset"]["outputs"][0]["interventions"] = [name]
    response = client.put(
        f"/api/v2/studies/{valid_bundle.study['sid']}",
        headers=creator_headers,
        **multipart(valid_bundle),
    )
    assert response.status_code == 422


def test_negotiated_report_create_replace_and_reject(
    client, creator_headers, valid_bundle
):
    headers = {**creator_headers, "X-PKDB-Report-Version": "2"}
    url = "/api/v2/studies/" + valid_bundle.study["sid"]
    assert client.get("/api/v2/capabilities").json()["upload_report_versions"] == [1, 2]
    for status, persistence in ((201, "created"), (200, "replaced")):
        response = client.put(url, headers=headers, **multipart(valid_bundle))
        assert response.status_code == status
        body = response.json()
        assert body["report_version"] == 2
        assert body["request_id"] == response.headers["X-Request-ID"]
        assert body["persistence"] == persistence
        assert body["result"]["sid"] == valid_bundle.study["sid"]
    response = client.put(
        "/api/v2/studies/WRONG", headers=headers, **multipart(valid_bundle)
    )
    assert response.status_code == 422
    assert response.json()["persistence"] == "not_saved"
    assert response.json()["report"]["issues"][0]["code"] == "sid_mismatch"


def test_negotiated_compatibility_report(client, creator_headers, valid_bundle):
    response = client.put(
        "/api/v2/studies/" + valid_bundle.study["sid"],
        headers={
            **creator_headers,
            "X-PKDB-Report-Version": "2",
            "X-PKDB-Processing-Version": "old-version",
        },
        **multipart(valid_bundle),
    )
    assert response.status_code == 409
    body = response.json()
    assert body["stage"] == "compatibility"
    assert body["versions"]["client_processing_version"] == "old-version"
    assert body["versions"]["server_processing_version"]
    assert body["report"]["issues"][0]["code"] == "processing_version_mismatch"


def test_negotiated_authentication_report_and_cors(client, session_factory, tmp_path):
    response = client.put(
        "/api/v2/studies/TEST", headers={"X-PKDB-Report-Version": "2"}
    )
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["report"]["issues"][0]["code"] == "authentication_required"
    from starlette.testclient import TestClient

    from pkdb_server.app import create_app
    from pkdb_server.config import Settings

    cors_client = TestClient(
        create_app(
            Settings(
                cors_origins=["http://localhost:8080"],
                database_url=session_factory.kw["bind"].url.render_as_string(
                    hide_password=False
                ),
                file_root=tmp_path,
            )
        )
    )
    preflight = cors_client.options(
        "/api/v2/studies/TEST",
        headers={
            "Origin": "http://localhost:8080",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "X-PKDB-Report-Version",
        },
    )
    assert preflight.status_code == 200
