"""Helper functions for querying information in PK-DB."""

import json
import logging
from typing import Any
from urllib.parse import urljoin

import requests
from requests import Response

from pkdb_data.management.utils import ordered_dict_no_duplicates

logger = logging.getLogger(__name__)


def get_authentication_headers(
    api_base: str, username: str, password: str
) -> dict[str, str]:
    """Get authentication header with token for given user.

    Returns admin authentication as default.
    """
    auth_token_url = urljoin(api_base, "api-token-auth/")
    try:
        response = requests.post(
            url=auth_token_url, json={"username": username, "password": password}
        )
    except requests.exceptions.ConnectionError as e:
        raise requests.exceptions.InvalidURL(
            f"Error Connecting (probably wrong url <{api_base}>): ", e
        ) from e

    if response.status_code != 200:
        logger.error("Request headers could not be retrieved from: %s", auth_token_url)
        logger.warning(response.text)
        raise requests.exceptions.ConnectionError(response)

    token = response.json().get("token")
    return {"Authorization": f"token {token}"}


def requests_with_client(
    client: Any, request: Any, *args: str, **kwargs: Any
) -> Response:
    """Perform request with client."""
    method = kwargs.pop("method", None)

    if client:
        if kwargs.get("files"):
            kwargs["data"] = kwargs.pop("files", None)
            response = getattr(client, method)(*args, **kwargs)
        else:
            response = getattr(client, method)(*args, **kwargs, format="json")
    else:
        kwargs["json"] = kwargs.pop("data", None)
        response = getattr(request, method)(*args, **kwargs)

    return response


def check_json_response(response: Response) -> bool:
    """Check response and create warning if not valid."""
    if response.status_code not in [200, 201, 204]:
        try:
            json_data = json.loads(
                response.content, object_pairs_hook=ordered_dict_no_duplicates
            )

            msg = json.dumps(json_data, sort_keys=True, indent=2, ensure_ascii=False)
            logger.warning("\n%s", msg)

        except json.decoder.JSONDecodeError as err:
            # something went wrong on the django serializer side
            logger.error(response.status_code)
            logger.error(err)
            logger.warning(response.content)

        return False
    return True


def check_json_response_study(response: Response) -> bool:
    """Check JSON response for study."""
    try:
        json_data = json.loads(
            response.content, object_pairs_hook=ordered_dict_no_duplicates
        )
        if len(json_data.get("warnings", [])) > 0:
            for warning in json_data["warnings"]:
                logger.warning(warning)

    except json.decoder.JSONDecodeError as err:
        # something went wrong on the django serializer side
        logger.error(response.status_code)
        logger.error(err)
        logger.warning(response.content)

    return True


def sid_exists(response: Response) -> bool:
    """Check if sid exists from response."""
    success = False
    try:
        json_data = json.loads(
            response.content, object_pairs_hook=ordered_dict_no_duplicates
        )
        json.dumps(json_data, sort_keys=True, indent=2)
        if "sid" in response.json() and "already exists" in response.json()["sid"][0]:
            success = True

    except json.decoder.JSONDecodeError:
        success = False

    return success
