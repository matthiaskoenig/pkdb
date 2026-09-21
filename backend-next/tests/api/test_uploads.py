import json

from sqlalchemy import func, select

from pkdb.db.models.studies import Study


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
