"""Functions for manipulating the elastic index."""

import logging
import multiprocessing
import threading
import time
from datetime import timedelta
from typing import Any

import requests

from pkdb_data.management.query import check_json_response, requests_with_client

logger = logging.getLogger(__name__)


class IndexProcess(multiprocessing.Process):
    """Process for indexing elastic.

    Allows to run the indexing in a separate thread.
    """

    def __init__(
        self, sid: str, api_url: str, auth_headers: dict[str, str], client: Any = None
    ):
        """Initialize IndexProcess."""
        multiprocessing.Process.__init__(
            self,
            target=_update_study_index_log,
            args=(sid, api_url, auth_headers, client),
        )


class IndexThread(threading.Thread):
    """Thread for indexing elastic."""

    def __init__(
        self, sid: str, api_url: str, auth_headers: dict[str, str], client: Any = None
    ):
        """Initialize IndexThread."""
        threading.Thread.__init__(self)
        self.sid = sid
        self.api_url = api_url
        self.auth_headers = auth_headers
        self.client = client

    def run(self) -> None:
        """Run indexing thread."""
        _update_study_index_log(self.sid, self.api_url, self.auth_headers, self.client)


def _update_study_index_log(
    sid: str, api_url: str, auth_headers: dict[str, str], client: Any = None
) -> None:
    """Update the study index log."""
    logger.info("Start indexing %s", sid)
    start_time = time.time()
    update_study_index(
        sid=sid, api_url=api_url, auth_headers=auth_headers, client=client
    )
    index_time = timedelta(seconds=time.time() - start_time).total_seconds()
    logger.info("[white on black]Finished indexing %s in %.2f [s]", sid, index_time)


def update_study_index(
    sid: str, api_url: str, auth_headers: dict[str, str], client: Any = None
) -> None:
    """Update the elasticsearch index for given study_sid."""
    response = requests_with_client(
        client,
        requests,
        f"{api_url}/update_index/",
        method="post",
        data={"sid": sid},
        headers=auth_headers,
    )
    check_json_response(response)
