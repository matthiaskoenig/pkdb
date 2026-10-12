"""Requests to a running local curation server and its browser session."""

import json
import re
from datetime import datetime
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


#: The fields of every error body of the local API (`describe` in pkdb/curation/errors.py).
ERROR_FIELDS = frozenset({"error", "code", "detail", "action", "request_id", "time"})


def error_body(data):
    """An error body of the local API without the fields that differ by request.

    It checks that the body has every field, an 8 hex character request id and a time with
    its time zone, and drops the request id and the time.
    """
    body = json.loads(data)
    assert ERROR_FIELDS <= set(body), body
    assert re.fullmatch(r"[0-9a-f]{8}", body.pop("request_id"))
    assert datetime.fromisoformat(body.pop("time")).tzinfo is not None
    return body
