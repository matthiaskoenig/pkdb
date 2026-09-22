"""Explicit Linux/Docker runtime gate; a configured image is required."""

import asyncio
import json
import os
import socket
import subprocess
import time
from uuid import uuid4

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from pkdb.db.models.users import EmailAddress, User
from pkdb.services.authentication import password_hash


def test_container_nonroot_upload_and_graceful_shutdown(
    ingestion_context, session_factory, valid_bundle
):
    image = os.environ["PKDB_TEST_IMAGE"]
    expected_python = os.environ["PKDB_TEST_IMAGE_PYTHON"]
    _, actor = ingestion_context
    with session_factory.begin() as session:
        user = session.get(User, actor.user_id)
        user.password_hash = password_hash.hash("Runtime-password-42!")
        session.add(
            EmailAddress(
                user_id=user.id,
                email="runtime@example.org",
                is_primary=True,
                is_verified=True,
            )
        )
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    name = "pkdb-runtime-" + uuid4().hex
    environment = {
        **os.environ,
        "PKDB_DATABASE_URL": session_factory.kw["bind"].url.render_as_string(
            hide_password=False
        ),
    }
    subprocess.run(
        [
            "docker",
            "run",
            "--detach",
            "--pull",
            "never",
            "--name",
            name,
            "--network",
            "host",
            "--env",
            "PKDB_DATABASE_URL",
            "--env",
            "PKDB_FILE_ROOT=/data/files",
            "--env",
            f"PKDB_BROWSER_ORIGIN=http://127.0.0.1:{port}",
            "--env",
            "PKDB_SECURE_COOKIES=false",
            "--tmpfs",
            "/data/files:rw,uid=10001,gid=10001,mode=0700",
            image,
            "uvicorn",
            "pkdb.app:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        with httpx2.Client(base_url=f"http://127.0.0.1:{port}", timeout=30) as client:
            deadline = time.monotonic() + 30
            while True:
                try:
                    ready = client.get("/health/ready")
                    if ready.status_code == 200:
                        break
                except httpx2.ConnectError:
                    pass
                assert time.monotonic() < deadline, "Container did not become ready"
                time.sleep(0.1)
            csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
            browser_headers = {
                "Origin": f"http://127.0.0.1:{port}",
                "X-CSRF-Token": csrf,
            }
            login = client.post(
                "/api/v1/auth/login",
                json={"username": actor.username, "password": "Runtime-password-42!"},
                headers=browser_headers,
            )
            assert login.status_code == 200, login.text
            key = client.post(
                "/api/v1/me/api-keys",
                json={"name": "container runtime", "scopes": ["read", "studies:write"]},
                headers=browser_headers,
            )
            assert key.status_code == 201, key.text
            token = key.json()["secret"]
            assert "secret" not in client.get("/api/v1/me/api-keys").json()[0]
            assert (
                client.post("/api/v1/auth/logout", headers=browser_headers).status_code
                == 204
            )
            client.cookies.clear()
            response = client.put(
                f"/api/v2/studies/{valid_bundle.study['sid']}",
                headers={"Authorization": f"Bearer {token}"},
                data={
                    "study": json.dumps(valid_bundle.study),
                    "reference": json.dumps(valid_bundle.reference),
                },
                files={"files": ("notes.txt", b"container attachment")},
            )
            assert response.status_code == 201, response.text
            response = client.get(
                f"/api/v2/studies/{valid_bundle.study['sid']}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            assert len(response.json()["measurements"]) == 2
            response = client.get(
                f"/api/v1/studies/{valid_bundle.study['sid']}/",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            file_url = response.json()["files"][0]["file"]
            assert client.get(file_url).status_code == 403
            assert (
                client.get(
                    file_url, headers={"Authorization": f"Bearer {token}"}
                ).content
                == b"container attachment"
            )

        async def check_mcp():
            async with httpx2.AsyncClient(
                headers={"Authorization": f"Bearer {token}"}, timeout=30
            ) as transport:
                async with streamable_http_client(
                    f"http://127.0.0.1:{port}/mcp/", http_client=transport
                ) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        assert len((await session.list_tools()).tools) == 4
                        result = await session.call_tool(
                            "get_study", {"sid": valid_bundle.study["sid"]}
                        )
                        assert not result.is_error
                        assert result.structured_content is not None
                        assert (
                            result.structured_content["sid"]
                            == valid_bundle.study["sid"]
                        )

        asyncio.run(check_mcp())
        result = subprocess.run(
            [
                "docker",
                "exec",
                name,
                "python",
                "-c",
                "import os,sys,importlib.util; import numpy,scipy,pandas,pint; "
                "from pkpdutils import Timecourse, nca_single; "
                "assert os.getuid() == 10001 and sys._is_gil_enabled(); "
                "import math; "
                "t=numpy.array([0,1,2,3,4,6,8]); "
                "course=Timecourse(time=t,value=8*numpy.exp(-0.5*t),time_unit='h',unit='mg/l'); "
                "result=nca_single(course); "
                "assert math.isclose(result['thalf'].item(),math.log(2)/0.5,rel_tol=1e-9); "
                'assert importlib.util.find_spec("pkdb_analysis") is None; '
                'assert importlib.util.find_spec("django") is None; '
                'assert importlib.util.find_spec("elasticsearch") is None; '
                'print(str(sys.version_info.major)+"."+str(sys.version_info.minor))',
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip().splitlines()[-1] == expected_python
        subprocess.run(
            ["docker", "stop", "--time", "10", name], check=True, capture_output=True
        )
        result = subprocess.run(
            ["docker", "inspect", name, "--format", "{{.State.ExitCode}}"],
            check=True,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "0"
    finally:
        subprocess.run(
            ["docker", "rm", "--force", name], check=False, capture_output=True
        )
