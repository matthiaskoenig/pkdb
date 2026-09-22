"""Create all choices.

Stores JSON files for database upload.
"""

import argparse
import collections
import json
import logging
import time
from datetime import timedelta
from pathlib import Path
from typing import Any, Final

import requests
from pymetadata.console import console

from pkdb_data import RESOURCES_DIR
from pkdb_data.management import api
from pkdb_data.management.envs import DEFAULT_USER_PASSWORD
from pkdb_data.management.query import (
    check_json_response,
    requests_with_client,
    sid_exists,
)
from pkdb_data.management.upload_studies import _log_step
from pkdb_data.management.users import USER_GROUPS_DATA, USERS_DATA
from pkdb_data.management.utils import read_json

logger = logging.getLogger(__name__)

JSON_PATH: Final = RESOURCES_DIR / "json"
JSON_PATH.mkdir(parents=True, exist_ok=True)


class InfoUploader:
    """Posting created choices JSONs to database."""

    @classmethod
    def setup_database(
        cls,
        api_url: str,
        auth_headers: dict[str, str],
        client: Any = None,
        json_path: Path = JSON_PATH,
    ) -> None:
        """Create core information in database.

        Uploads information from JSON file.
        """
        console.print(f"upload info nodes: [blue]{api_url}[/]")

        json_paths = {
            key: json_path / f"{key[1:]}.json"
            for key in [
                api.USER_GROUPS,
                api.USERS,
                api.INFO_NODES,
            ]
        }
        success: bool = True

        for api_path, path in json_paths.items():
            data_json = read_json(path)
            if data_json:
                # inject default password
                if api_path == "_users":
                    for k, item in enumerate(data_json):
                        item["password"] = DEFAULT_USER_PASSWORD
                        data_json[k] = item

                if api_path in ["_users", "_user_groups"]:
                    success = cls._upload_info(
                        api_url, api_path, auth_headers, data_json, client
                    )

                if api_path in ["_info_nodes"]:
                    cls.check_for_duplicates(data_json, path)
                    success = cls._upload_info(
                        api_url, api_path, auth_headers, data_json, client
                    )
            else:
                success = False
        if success:
            console.print("[green bold]SUCCESSFULLY UPLOADED INFO NODES[/]")
        else:
            console.print("[red bold]UPLOAD OF INFO NODES FAILED[/]")

    @staticmethod
    def check_for_duplicates(data_json: list[dict], path: Path) -> None:
        """Check for duplicates."""
        a = [v["sid"] for v in data_json]
        for item, count in collections.Counter(a).items():
            if count > 1:
                logger.warning(
                    "The JSON file <%s> has duplicate entries. The instance with sid = "
                    "%s exists %s times.",
                    path,
                    item,
                    count,
                )

    @staticmethod
    def _upload_info(
        api_url: str,
        choice: str,
        auth_headers: dict[str, str],
        data_json: dict[str, Any],
        client: Any = None,
    ) -> bool:
        """Upload single choice."""
        start_time = time.time()
        if choice == "_info_nodes":
            response = requests_with_client(
                client,
                requests,
                f"{api_url}/{choice}/",
                method="post",
                data=data_json,
                headers=auth_headers,
            )

            success = check_json_response(response)
            if not success:
                logger.error("%s upload failed", choice)
                return False
            upload_time: float = time.time() - start_time
            upload_time = timedelta(seconds=upload_time).total_seconds()
            _log_step(f"Upload {choice[1:]}", time=upload_time)
            return success

        success = True
        for instance in data_json:
            response = requests_with_client(
                client,
                requests,
                f"{api_url}/{choice}/",
                method="post",
                data=instance,
                headers=auth_headers,
            )
            if choice == "_info_nodes":
                if sid_exists(response):
                    sid: str = instance["sid"]  # type: ignore
                    response = requests_with_client(
                        client,
                        requests,
                        f"{api_url}/{choice}/{sid}/",
                        method="patch",
                        data=instance,
                        headers=auth_headers,
                    )
                success = check_json_response(response)

            if not success:
                logger.error("%s upload failed: %s ", choice, instance)
                return False

        upload_time = time.time() - start_time
        upload_time = timedelta(seconds=upload_time).total_seconds()
        _log_step(f"Upload {choice[1:]}", time=upload_time)
        return success


def create_info_nodes(args: argparse.Namespace) -> None:
    """Create all JSON files for info nodes upload."""
    console.print("[blue]collect info nodes[/]")
    # local import to avoid warnings
    from pkdb_data.info_nodes.nodes import collect_nodes

    info_nodes = collect_nodes()

    console.print("[blue]serialize info nodes[/]")
    info = {
        "info_nodes": [node.serialize(info_nodes) for node in info_nodes],
        "user_groups": USER_GROUPS_DATA,
        "users": USERS_DATA,
    }

    for key, data in info.items():
        path = JSON_PATH / f"{key}.json"
        console.print(f"[blue]write {path}[/]")
        with open(path, "w") as fp:
            json.dump(data, fp, indent=2)

    console.log("[green bold]SUCCESSFULLY CREATED INFO_NODES JSON[/]")
