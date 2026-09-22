import pytest


@pytest.mark.parametrize(
    "path,payload,expected",
    [
        (
            "/api-token-auth/",
            {},
            {
                "username": ["This field is required."],
                "password": ["This field is required."],
            },
        ),
        (
            "/api-token-auth/",
            {"username": "", "password": ""},
            {
                "username": ["This field may not be blank."],
                "password": ["This field may not be blank."],
            },
        ),
        (
            "/accounts/register/",
            {},
            {
                "username": ["This field is required."],
                "email": ["This field is required."],
                "password": ["This field is required."],
            },
        ),
        (
            "/accounts/register/",
            {"username": "sample", "password": "Sample-only-42!", "email": "invalid"},
            {"email": ["Enter a valid email address."]},
        ),
        (
            "/accounts/request-password-reset/",
            {},
            {"email": ["This field is required."]},
        ),
    ],
)
def test_legacy_account_validation_matches_captured_responses(
    client, path, payload, expected
):
    response = client.post(path, json=payload)
    assert response.status_code == 400
    assert response.json() == expected
    assert "Sample-only-42!" not in response.text


def test_legacy_admin_validation_uses_field_errors(client, admin_headers):
    response = client.post(
        "/api/v1/_users/",
        headers=admin_headers,
        json={"password": "Never-echo-this-42!"},
    )
    assert response.status_code == 400
    assert response.json()["username"] == ["This field is required."]
    assert "Never-echo-this-42!" not in response.text


def test_unrelated_validation_keeps_its_existing_format(client):
    response = client.get("/api/v1/outputs/not-an-integer/")
    # This adapter is scoped to accounts; public-read path contracts are separate.
    assert response.status_code == 422


def test_admin_permission_check_precedes_field_validation(client, creator_headers):
    for headers, status in (({}, 401), (creator_headers, 403)):
        response = client.post("/api/v1/_users/", headers=headers, json={})
        assert response.status_code == status


@pytest.mark.parametrize(
    "path", ["/accounts/emails/", "/api/v1/_users/", "/api/v1/_users.json"]
)
def test_protected_account_malformed_json_checks_authentication_first(client, path):
    response = client.post(
        path, content="{", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_malformed_admin_json_checks_role_first(client, creator_headers, admin_headers):
    headers = {"Content-Type": "application/json"}
    denied = client.post(
        "/api/v1/_users/", content="{", headers=headers | creator_headers
    )
    assert denied.status_code == 403
    allowed = client.post(
        "/api/v1/_users/", content="{", headers=headers | admin_headers
    )
    assert allowed.status_code == 400
    assert "non_field_errors" in allowed.json()


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/accounts/emails/"),
        ("patch", "/accounts/emails/1/"),
        ("put", "/accounts/emails/not-an-integer/"),
    ],
)
def test_email_authentication_precedes_field_validation(client, method, path):
    response = getattr(client, method)(path, json={})
    assert response.status_code == 401
