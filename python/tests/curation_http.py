"""Requests to a running local curation server and its browser session."""

import json
from http.client import HTTPConnection


def request(server, method, path, body=None, headers=None):
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    defaults = {"Origin": server.origin, "Content-Type": "application/json"}
    defaults.update(headers or {})
    connection.request(
        method,
        path,
        body=json.dumps(body) if body is not None else None,
        headers=defaults,
    )
    response = connection.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    connection.close()
    return result


def authenticate(server):
    status, headers, data = request(
        server, "POST", "/local/session", {"token": server.bootstrap_token}
    )
    assert status == 200
    assert "HttpOnly" in headers["Set-Cookie"]
    assert "SameSite=Strict" in headers["Set-Cookie"]
    return {
        "Cookie": headers["Set-Cookie"].split(";", 1)[0],
        "X-CSRF-Token": json.loads(data)["csrf_token"],
    }
