"""Explicit Linux/Docker runtime gate; a configured image is required."""

import asyncio
import json
import os
import socket
import subprocess
import time
from uuid import uuid4

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from pkdb.db.models.users import User
from pkdb.services.authentication import issue_token


def test_container_nonroot_upload_and_graceful_shutdown(
    ingestion_context, session_factory, valid_bundle
):
    image = os.environ["PKDB_TEST_IMAGE"]
    expected_python = os.environ["PKDB_TEST_IMAGE_PYTHON"]
    _, actor = ingestion_context
    with session_factory.begin() as session:
        token = issue_token(session.get(User, actor.user_id), session)
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
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=30) as client:
            deadline = time.monotonic() + 30
            while True:
                try:
                    ready = client.get("/health/ready")
                    if ready.status_code == 200:
                        break
                except httpx.ConnectError:
                    pass
                assert time.monotonic() < deadline, "Container did not become ready"
                time.sleep(0.1)
            response = client.put(
                f"/api/v2/studies/{valid_bundle.study['sid']}",
                headers={"Authorization": f"Token {token}"},
                data={
                    "study": json.dumps(valid_bundle.study),
                    "reference": json.dumps(valid_bundle.reference),
                },
                files={"files": ("notes.txt", b"container attachment")},
            )
            assert response.status_code == 201, response.text
            response = client.get(
                f"/api/v2/studies/{valid_bundle.study['sid']}",
                headers={"Authorization": f"Token {token}"},
            )
            assert response.status_code == 200
            assert len(response.json()["measurements"]) == 2
            response = client.get(
                f"/api/v1/studies/{valid_bundle.study['sid']}/",
                headers={"Authorization": f"Token {token}"},
            )
            assert response.status_code == 200
            file_url = response.json()["files"][0]["file"]
            assert client.get(file_url).status_code == 403
            assert (
                client.get(
                    file_url, headers={"Authorization": f"Token {token}"}
                ).content
                == b"container attachment"
            )

        async def check_mcp():
            async with httpx.AsyncClient(
                headers={"Authorization": f"Bearer {token}"}, timeout=30
            ) as transport:
                async with streamable_http_client(
                    f"http://127.0.0.1:{port}/mcp/", http_client=transport
                ) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        assert len((await session.list_tools()).tools) == 4
                        result = await session.call_tool(
                            "get_study", {"sid": valid_bundle.study["sid"]}
                        )
                        assert not result.isError
                        assert result.structuredContent is not None
                        assert (
                            result.structuredContent["sid"] == valid_bundle.study["sid"]
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
                "from pkdb_analysis.pk import pharmacokinetics; "
                "assert os.getuid() == 10001 and sys._is_gil_enabled(); "
                "from pkdb.domain.units import ureg; import math; "
                "t=numpy.array([0,1,2,3,4,6,8]); "
                "course=pharmacokinetics.TimecoursePKNoDosing(substance='test', "
                "time=ureg.Quantity(t,'h'), "
                "concentration=ureg.Quantity(8*numpy.exp(-0.5*t),'mg/l'), ureg=ureg); "
                "assert math.isclose(course.pk.thalf.to('h').magnitude,math.log(2)/0.5,rel_tol=1e-9); "
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
