"""Read-only study discovery and one atomic request per study."""

import json
from contextlib import ExitStack
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import httpx2

from pkdb.importers.folder import load_folder
from pkdb.schemas.validation import StudyValidationError


def api_root(value):
    url = urlsplit(value)
    if (
        url.scheme not in {"http", "https"}
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise ValueError(
            "API URL must be an HTTP(S) server URL without credentials, query, or fragment"
        )
    path = url.path.rstrip("/")
    if path.endswith(("/api/v1", "/api/v2")):
        path = path[:-7]
    return urlunsplit((url.scheme, url.netloc, path + "/api/v2", "", ""))


def study_folders(path: Path):
    if not path.is_dir():
        raise ValueError("Study path must be a directory")
    if (path / "study.json").is_file():
        return [path]
    folders = sorted(file.parent for file in path.rglob("study.json"))
    if not folders:
        raise ValueError("No study.json files found")
    return folders


def send_folder(path, *, client, api_url, token, validate=False):
    record = {"path": str(path), "ok": False}
    try:
        bundle = load_folder(path)
        sid = bundle.study.get("sid")
        if type(sid) not in (str, int):
            raise ValueError("Study SID must be text or an integer")
        sid = str(sid)
        if not sid or sid in {".", ".."}:
            raise ValueError("Study SID must be a nonempty identifier")
        record["sid"] = sid
        url = api_url + (
            "/studies/validate" if validate else "/studies/" + quote(sid, safe="")
        )
        with ExitStack() as stack:
            # JSON is sent as multipart parts even when there are no attachments.
            parts = [
                ("study", (None, json.dumps(bundle.study))),
                ("reference", (None, json.dumps(bundle.reference))),
            ]
            parts.extend(
                (
                    "files",
                    (
                        name,
                        stack.enter_context(file.open("rb")),
                        "application/octet-stream",
                    ),
                )
                for name, file in bundle.files.items()
            )
            response = client.request(
                "POST" if validate else "PUT",
                url,
                headers={
                    "Authorization": (
                        f"Bearer {token}"
                        if token.startswith("pkdb_live_")
                        else f"Token {token}"
                    )
                },
                files=parts,
            )
        record["status"] = response.status_code
        record["ok"] = response.status_code in ({200} if validate else {200, 201})
        try:
            body = response.json()
        except ValueError:
            body = None
        if not isinstance(body, dict):
            record.update(ok=False, error="Server returned an invalid JSON response")
        elif record["ok"]:
            if validate and body.get("valid") is not True:
                record.update(ok=False, error="Validation was not confirmed")
            elif not validate and body.get("sid") != sid:
                record.update(ok=False, error="Publication SID was not confirmed")
            if not validate and isinstance(body.get("digest"), str):
                record["digest"] = body["digest"]
        else:
            # Do not echo arbitrary response bodies (e.g. proxy/debug output).
            record["error"] = "Server rejected the study bundle"
            if isinstance(body.get("issues"), list):
                record["issues"] = body["issues"]
    except StudyValidationError as error:
        record["error"] = "Invalid source bundle"
        record["issues"] = error.report.legacy_dict()["issues"]
    except OSError, ValueError:
        record["error"] = "Unable to read a valid source bundle"
    except httpx2.RequestError:
        record["error"] = (
            "Request failed; publication outcome may be unknown. Retry the complete bundle."
        )
    return record
