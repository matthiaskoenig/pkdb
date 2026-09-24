"""Exercise the public CLI against a disposable server and read-only corpus."""

import hashlib
import json
import os
import secrets
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path

import httpx2
import openpyxl
from sqlalchemy.engine import make_url

from pkdb.cache import VocabularyCache
from pkdb.client import Client
from pkdb.importers.folder import load_folder
from pkdb.preparation import study_folders
from pkdb.schemas.validation import StudyValidationError
from pkdb_server.app import create_app
from pkdb_server.commands.admin import create_admin
from pkdb_server.commands.bootstrap import bootstrap_study
from pkdb_server.commands.user_import import import_roster
from pkdb_server.config import Settings
from pkdb_server.db.session import make_session_factory

ROOT = Path("/studies")
EVIDENCE = Path("/tmp/upload-evidence")
ENDPOINT = "http://127.0.0.1:8000"


def digest():
    result = hashlib.sha256()
    for path in sorted(ROOT.rglob("*")):
        if path.is_file():
            result.update(str(path.relative_to(ROOT)).encode())
            result.update(path.read_bytes())
    return result.hexdigest()


def main():
    settings = Settings()
    url = make_url(settings.database_url)
    assert (url.database, url.username, url.host) == (
        "pkdb_upload_test",
        "pkdb_upload_test",
        "db",
    ), "Only the isolated database is permitted"
    EVIDENCE.mkdir(exist_ok=True)
    before = digest()
    factory = make_session_factory(settings.database_url)
    password = secrets.token_urlsafe(32)
    create_admin(factory, "mkoenig", "upload-test@example.org", password)
    imported = import_roster(
        "/app/bootstrap/curator-roster.json",
        factory,
        apply=True,
        file_root=settings.file_root,
        avatar_root="/app/frontend/public",
    )
    assert imported["ok"], imported
    for folder in study_folders(ROOT):
        print(f"Bootstrap attribution: {folder.name}", flush=True)
        try:
            bootstrap_study(folder, factory)
        except StudyValidationError:
            pass  # Invalid source studies cannot be uploaded; roster still imported.
    app = create_app(settings)
    _, principal = app.state.credentials.login("mkoenig", password)
    key = app.state.credentials.create_key(
        principal,
        "Disposable upload verification",
        scopes=("read", "studies:write"),
        lifetime_days=1,
    )["secret"]
    readonly_key = app.state.credentials.create_key(
        principal, "Disposable read only key", scopes=("read",), lifetime_days=1
    )["secret"]
    with Client(ENDPOINT) as public_client:
        fault_capabilities = public_client.capabilities()
    faults = []
    for label, headers, expected in [
        ("missing_credentials", {}, 401),
        ("missing_write_scope", {"Authorization": f"Bearer {readonly_key}"}, 403),
        (
            "unsupported_report_version",
            {"Authorization": f"Bearer {key}", "X-PKDB-Report-Version": "999"},
            400,
        ),
    ]:
        fault_source = load_folder(ROOT / "Frost2014")
        with ExitStack() as stack:
            parts = [
                (name, (None, json.dumps(value)))
                for name, value in (
                    ("study", fault_source.study),
                    ("reference", fault_source.reference),
                )
            ]
            parts.extend(
                (
                    "files",
                    (
                        name,
                        stack.enter_context(path.open("rb")),
                        "application/octet-stream",
                    ),
                )
                for name, path in fault_source.files.items()
            )
            response = httpx2.put(
                ENDPOINT + "/api/v2/studies/PKDB01110",
                headers={
                    "X-PKDB-Report-Version": "2",
                    "X-PKDB-Vocabulary-Hash": fault_capabilities.vocabulary_hash,
                    "X-PKDB-Processing-Version": fault_capabilities.processing_version,
                    **headers,
                },
                files=parts,
                timeout=120,
            )
        assert response.status_code == expected, (
            label,
            response.status_code,
            response.text,
        )
        body = response.json()
        assert body["report_version"] == 2
        assert body["persistence"] == "not_saved"
        faults.append(
            {"scenario": label, "http_status": response.status_code, "body": body}
        )
    (EVIDENCE / "faults.json").write_text(json.dumps(faults, indent=2))
    env = {
        **os.environ,
        "PKDB_ENDPOINT": ENDPOINT,
        "PKDB_API_KEY": key,
        "NO_COLOR": "1",
    }
    cache = EVIDENCE / "cache"

    def cli(name, *args):
        result = subprocess.run(
            [sys.executable, "-m", "pkdb.cli", *args, "--cache-dir", str(cache)],
            env=env,
            capture_output=True,
            text=True,
        )
        assert key not in result.stdout + result.stderr
        (EVIDENCE / f"{name}.stdout").write_text(result.stdout)
        (EVIDENCE / f"{name}.stderr").write_text(result.stderr)
        print(f"{name}: exit {result.returncode}", flush=True)
        return result

    assert cli("sync", "vocabulary", "sync").returncode == 0
    validation = cli(
        "validation", "validate", str(ROOT), "--offline", "--format", "json"
    )
    first = cli(
        "created",
        "upload",
        str(ROOT),
        "--format",
        "human",
        "--report",
        str(EVIDENCE / "created.json"),
    )
    second = cli(
        "replaced",
        "upload",
        str(ROOT),
        "--format",
        "json",
        "--report",
        str(EVIDENCE / "replaced.json"),
    )
    assert validation.returncode == first.returncode == second.returncode == 1
    created = json.loads((EVIDENCE / "created.json").read_text())
    replaced = json.loads((EVIDENCE / "replaced.json").read_text())
    assert created["summary"]["discovered"] == 30
    assert created["summary"]["attempted"] == 30
    assert replaced["summary"]["replaced"] == created["summary"]["created"]
    assert replaced["summary"]["created"] == 0
    assert replaced["summary"]["unknown"] == 0
    assert replaced["summary"]["failed"] == created["summary"]["failed"]
    by_sid = {row["sid"]: row for row in created["results"] if row["ok"]}
    direct = []
    verified = []
    coordinates = []
    with Client(ENDPOINT, api_key=key, cache=VocabularyCache(cache)) as client:
        capabilities = client.capabilities()
        for folder in study_folders(ROOT):
            source = load_folder(folder)
            sid = source.study["sid"]
            with ExitStack() as stack:
                parts = [
                    (name, (None, json.dumps(value)))
                    for name, value in (
                        ("study", source.study),
                        ("reference", source.reference),
                    )
                ]
                parts.extend(
                    (
                        "files",
                        (
                            name,
                            stack.enter_context(path.open("rb")),
                            "application/octet-stream",
                        ),
                    )
                    for name, path in source.files.items()
                )
                response = httpx2.put(
                    ENDPOINT + f"/api/v2/studies/{sid}",
                    files=parts,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "X-PKDB-Report-Version": "2",
                        "X-PKDB-Vocabulary-Hash": capabilities.vocabulary_hash,
                        "X-PKDB-Processing-Version": capabilities.processing_version,
                    },
                    timeout=120,
                )
            body = response.json()
            (EVIDENCE / f"server-{folder.name}.json").write_text(
                json.dumps(body, indent=2)
            )
            assert body["report_version"] == 2, body
            assert body["request_id"] == response.headers["X-Request-ID"]
            direct.append(
                {"name": folder.name, "http_status": response.status_code, "body": body}
            )
            if response.is_success:
                study = client.studies.get(sid)
                assert study.sid == sid
                assert body["result"]["counts"] == by_sid[sid]["counts"]
                assert body["result"]["digest"] == by_sid[sid]["digest"]
                verified.append(sid)
            else:
                assert response.status_code == 422, body
                assert body["persistence"] == "not_saved", body
                absent = httpx2.get(
                    ENDPOINT + f"/api/v2/studies/{sid}",
                    headers={"Authorization": f"Bearer {key}"},
                )
                assert absent.status_code == 404
                # Independently inspect real workbook cells, rather than trusting
                # the parser's own coordinates. Check each distinct error class.
                seen = set()
                for issue in body["report"]["issues"]:
                    source_location = issue.get("source") or {}
                    cell = source_location.get("cell")
                    filename = source_location.get("file", "")
                    if (
                        not cell
                        or not filename.endswith(".xlsx")
                        or issue["code"] in seen
                    ):
                        continue
                    seen.add(issue["code"])
                    workbook = openpyxl.load_workbook(
                        folder / filename, read_only=True, data_only=True
                    )
                    actual = workbook[source_location["sheet"]][cell].value
                    workbook.close()
                    if "actual" in issue and issue["actual"] is not None:
                        assert actual == issue["actual"], (folder.name, issue, actual)
                    coordinates.append(
                        {
                            "study": folder.name,
                            "code": issue["code"],
                            "source": source_location,
                            "workbook_value": actual,
                        }
                    )
    assert before == digest(), "Source corpus changed"
    (EVIDENCE / "direct-server.json").write_text(json.dumps(direct, indent=2))
    metadata = {
        "source_digest": before,
        "capabilities": capabilities.model_dump(),
        "verified_sids": verified,
        "studies": len(direct),
        "verified_coordinates": coordinates,
    }
    (EVIDENCE / "metadata.json").write_text(json.dumps(metadata, indent=2))
    print(
        json.dumps(
            {
                "verified_persisted": len(verified),
                "server_rejected": len(direct) - len(verified),
                "source_unchanged": True,
            }
        )
    )


if __name__ == "__main__":
    main()
