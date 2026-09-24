import httpx2

from pkdb.curation.github import GitHubAssignments


def test_read_only_users_assignments_and_cache_on_failure():
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == "GET"
        if request.url.path.endswith("assignees"):
            return httpx2.Response(403, json={})
        return httpx2.Response(
            200,
            json=[
                {
                    "number": 1,
                    "title": "drug/Study",
                    "state": "open",
                    "labels": [{"name": "curate"}],
                    "assignees": [
                        {"id": 7, "login": "curator", "type": "User"},
                        {"id": 8, "login": "bot", "type": "Bot"},
                    ],
                },
                {"number": 2, "pull_request": {}, "assignees": []},
            ],
        )

    provider = GitHubAssignments("owner/data", transport=httpx2.MockTransport(handler))
    data = provider.refresh()
    assert data["limited"]
    assert [u["login"] for u in data["users"]] == ["curator"]
    assert [i["number"] for i in data["issues"]] == [1]
    assert data["issues"][0]["html_url"] == "https://github.com/owner/data/issues/1"
    provider.transport = httpx2.MockTransport(lambda request: httpx2.Response(503))
    result = provider.refresh()
    assert result["status"] == "unavailable"
    assert result["issues"] == data["issues"]
    assert len(calls) == 2


def test_paginates_users_and_issues():
    calls = []

    def handler(request):
        calls.append((request.url.path, request.url.params["page"]))
        if request.url.path.endswith("assignees"):
            users = [{"id": i, "login": f"u{i}", "type": "User"} for i in range(100)]
            return httpx2.Response(
                200, json=users if request.url.params["page"] == "1" else []
            )
        return httpx2.Response(200, json=[])

    data = GitHubAssignments(
        "owner/data", transport=httpx2.MockTransport(handler)
    ).refresh()
    assert len(data["users"]) == 100
    assert ("/repos/owner/data/assignees", "2") in calls
