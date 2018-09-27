"""
Initial setup of database.
"""
import os
import requests
import logging
from pkdb_app.categoricals import SUBSTANCES_DATA, KEYWORDS_DATA

# ---------------------------------------------------------
import environ
env = environ.Env(
    DEBUG=(bool, False)
)
# reading .env file
environ.Env.read_env()

if "PKDB_API_BASE" in env:
    os.environ["PKDB_API_BASE"] = env("PKDB_API_BASE")
if "PKDB_DEFAULT_PASSWORD" in env:
    os.environ["PKDB_DEFAULT_PASSWORD"] = env("PKDB_DEFAULT_PASSWORD")

API_BASE = os.getenv("PKDB_API_BASE")
if not API_BASE:
    raise ValueError("API_BASE could not be read, export the 'PKDB_API_BASE' environment variable.")
API_URL = API_BASE + "/api/v1"

DEFAULT_PASSWORD = os.getenv("PKDB_DEFAULT_PASSWORD")
if not DEFAULT_PASSWORD:
    raise ValueError("Default password could not be read, export the 'PKDB_DEFAULT_PASSWORD' environment variable.")
# ---------------------------------------------------------

USERS = [
    {
        "username": "janekg",
        "first_name": "Jan",
        "last_name": "Grzegorzewski",
        "email": "Janekg89@hotmail.de",
        "password": DEFAULT_PASSWORD,
    },
    {
        "username": "mkoenig",
        "first_name": "Matthias",
        "last_name": "König",
        "email": "konigmatt@googlemail.com",
        "password": DEFAULT_PASSWORD,
    },
]


def get_authentication_header(api_base, username, password):
    """ Get authentication token for given user. """
    response = requests.post(f"{api_base}/api-token-auth/", json={"username": username, "password": password})
    response.raise_for_status()
    token = response.json().get("token")
    return {'Authorization': f'token {token}'}


def requests_with_client(client, requests, *args, **kwargs):
    method = kwargs.pop("method", None)

    if client:
        if kwargs.get("files"):
            kwargs["data"] = kwargs.pop("files",None)
            response = getattr(client, method)(*args, **kwargs)

        else:
            response = getattr(client, method)(*args, **kwargs, format='json')
    else:
        kwargs["json"] = kwargs.pop("data", None)
        response = getattr(requests, method)(*args, **kwargs)

    return response


def setup_database(api_url, authentication_header, client=None):
    """ Creates core information in database.

    This information is independent of study information. E.g., users, substances,
    categorials.

    :return:
    """
    for user in USERS:
        response = requests_with_client(client, requests, f"{api_url}/users/", method="post",
                                        data=user, headers=authentication_header)

        if not response.status_code == 201:
            logging.warning(f"user upload failed: {user} ")
            logging.warning(response.content)

    for substance in SUBSTANCES_DATA:
        response = requests_with_client(client, requests, f"{api_url}/substances/", method="post",
                                        data={"name": substance}, headers=authentication_header)
        if not response.status_code == 201:
            logging.warning(f"substance upload failed: {substance}")
            logging.warning(response.content)

    for keyword in KEYWORDS_DATA:
        response = requests_with_client(client, requests, f"{api_url}/keywords/", method="post",
                                        data={"name": keyword}, headers=authentication_header)
        if not response.status_code == 201:
            logging.warning(f"keyword upload failed: {keyword} ")
            logging.warning(response.content)


if __name__ == "__main__":
    authentication_header = get_authentication_header(api_base=API_BASE, username="admin", password=DEFAULT_PASSWORD)
    setup_database(api_url=API_URL, authentication_header=authentication_header)
