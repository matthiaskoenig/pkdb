"""Explicit unchanged-client HTTP gate; client interpreter/root must be supplied."""

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import uvicorn
from sqlalchemy import select

from pkdb.app import create_app
from pkdb.config import Settings
from pkdb.db.bootstrap import bootstrap
from pkdb.db.models.users import User
from pkdb.importers.folder import load_folder, parse_bundle
from pkdb.services.authentication import issue_token

CLIENT_SCRIPT = r"""
import json, multiprocessing, sys
from pathlib import Path
from urllib.parse import urlparse
sys.dont_write_bytecode = True
config = json.load(sys.stdin)
sys.path.insert(0, config['client_root'])
import requests
from pkdb_data.management import upload_studies
from pkdb_data.management.envs import Environment
upload_studies.get_environment = lambda: Environment(
    api_base=config['url'], user='replay', password='unused')
original = requests.sessions.Session.request
def local_request(self, method, url, *args, **kwargs):
    if urlparse(url).netloc != urlparse(config['url']).netloc:
        raise RuntimeError('Replay forbids external requests')
    kwargs.setdefault('timeout', 90)
    return original(self, method, url, *args, **kwargs)
requests.sessions.Session.request = local_request
client = upload_studies.UploadClient(
    api_url=config['url'] + '/api/v1',
    auth_headers={'Authorization': 'Token ' + config['token']}, client=None)
assert client.upload_study(Path(config['folder']))
for child in multiprocessing.active_children():
    child.join(100)
    assert not child.is_alive() and child.exitcode == 0
"""


def digest_tree(folder):
    return {
        str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in folder.rglob("*")
        if path.is_file()
    }


def test_unchanged_frost_uploader_publishes_complete_study(session_factory, tmp_path):
    source = Path(os.environ["PKDB_STUDY_CORPUS"]) / "apixaban/Frost2014"
    client_python = os.environ["PKDB_LEGACY_CLIENT_PYTHON"]
    client_root = os.environ["PKDB_LEGACY_CLIENT_ROOT"]
    before = digest_tree(source)
    folder = tmp_path / source.name
    shutil.copytree(source, folder)
    study = parse_bundle(load_folder(source))
    usernames = {
        study.metadata.creator,
        *[c.user for c in study.metadata.curators],
        *study.metadata.collaborators,
    }
    (tmp_path / "users.json").write_text(
        json.dumps([{"username": username, "role": "admin"} for username in usernames])
    )
    shutil.copy(Path(__file__).parents[1] / "bootstrap/vocabulary.json", tmp_path)
    with session_factory.begin() as session:
        assert not bootstrap(tmp_path, session).errors
        owner = session.scalar(
            select(User).where(User.username == study.metadata.creator)
        )
        assert owner is not None
        owner.active = True
        token = issue_token(owner, session)
    app = create_app(
        Settings(
            database_url=session_factory.kw["bind"].url.render_as_string(
                hide_password=False
            ),
            file_root=tmp_path / "files",
        )
    )
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    url = f"http://127.0.0.1:{sock.getsockname()[1]}"
    server = uvicorn.Server(
        uvicorn.Config(
            app, log_level="critical", lifespan="on", timeout_graceful_shutdown=5
        )
    )
    thread = threading.Thread(
        target=server.run, kwargs={"sockets": [sock]}, daemon=True
    )
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started
        result = subprocess.run(
            [client_python, "-c", CLIENT_SCRIPT],
            input=json.dumps(
                dict(client_root=client_root, url=url, token=token, folder=str(folder))
            ),
            capture_output=True,
            text=True,
            timeout=180,
        )
        output = (result.stdout + result.stderr).replace(token, "[redacted]")
        assert result.returncode == 0, output
        with httpx.Client(
            base_url=url, headers={"Authorization": f"Token {token}"}, timeout=30
        ) as client:
            response = client.get(f"/api/v2/studies/{study.sid}")
            assert response.status_code == 200, output + response.text
            published = response.json()
            assert len(published["measurements"]) == 782
            assert len(published["individuals"]) == 70
            assert len(published["timecourses"]) == 8
            assert (
                sum(
                    course["points"][0]["origin"] == "normalized"
                    for course in published["timecourses"]
                )
                == 4
            )
            assert published["metadata"]["name"] == study.metadata.name
        report_path = tmp_path / "rebuild.json"
        rebuild_script = (
            Path(__file__).parents[2] / "tools/backend_migration/rebuild.py"
        )
        for resumed in (False, True):
            rebuild = subprocess.run(
                [
                    sys.executable,
                    str(rebuild_script),
                    "--corpus",
                    str(source),
                    "--api-url",
                    url,
                    "--report",
                    str(report_path),
                ],
                env={**os.environ, "PKDB_API_TOKEN": token},
                capture_output=True,
                text=True,
                timeout=180,
            )
            assert rebuild.returncode == 0, (rebuild.stdout + rebuild.stderr).replace(
                token, "[redacted]"
            )
            report = json.loads(report_path.read_text())
            assert report["complete"]
            assert report["results"][0]["status"] == "published"
            assert report["results"][0]["resumed"] is resumed
        assert digest_tree(source) == before
    finally:
        server.should_exit = True
        thread.join(10)
        sock.close()
        assert not thread.is_alive()
