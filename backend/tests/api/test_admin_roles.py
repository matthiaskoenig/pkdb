import pytest


def test_role_catalogue_matches_legacy_projection(client, admin_headers):
    response = client.get("/api/v1/_user_groups/", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == {
        "current_page": 1,
        "last_page": 1,
        "next_page_url": None,
        "prev_page_url": None,
        "data": {
            "count": 4,
            "data": [
                {"name": name, "permissions": []}
                for name in ("basic", "admin", "reviewer", "curator")
            ],
        },
    }
    page = client.get(
        "/api/v1/_user_groups.json?page_size=2&page=2", headers=admin_headers
    )
    assert page.status_code == 200
    assert page.json()["data"]["data"] == [
        {"name": "reviewer", "permissions": []},
        {"name": "curator", "permissions": []},
    ]
    previous = client.get(page.json()["prev_page_url"], headers=admin_headers)
    assert previous.json()["data"]["data"][0]["name"] == "basic"
    for identifier, name in enumerate(("basic", "admin", "reviewer", "curator"), 1):
        detail = client.get(
            f"/api/v1/_user_groups/{identifier}/", headers=admin_headers
        )
        assert detail.status_code == 200
        assert detail.json() == {"name": name, "permissions": []}


@pytest.mark.parametrize(
    "path", ["/_user_groups/", "/_user_groups/1/", "/_user_groups.json"]
)
def test_role_catalogue_requires_administrator(client, creator_headers, path):
    assert client.get("/api/v1" + path).status_code == 401
    assert client.get("/api/v1" + path, headers=creator_headers).status_code == 403


def test_role_catalogue_rejects_unknown_pages_and_ids(client, admin_headers):
    for path in (
        "/_user_groups/999/",
        "/_user_groups/invalid/",
        "/_user_groups/?page=3&page_size=2",
    ):
        assert client.get("/api/v1" + path, headers=admin_headers).status_code == 404
    assert (
        client.get(
            "/api/v1/_user_groups/?page=last&page_size=2", headers=admin_headers
        ).json()["current_page"]
        == 2
    )


def test_role_catalogue_large_page_size_remains_one_page(client, admin_headers):
    response = client.get(
        "/api/v1/_user_groups/", params={"page_size": "9" * 400}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["last_page"] == 1
