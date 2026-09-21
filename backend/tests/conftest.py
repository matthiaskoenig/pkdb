"""Fixtures shared by the test modules.

The services are the ones of `docker-compose-test.yml`, see `docs/development.md`.
"""

from io import StringIO

import pytest
from django.core.management import call_command


@pytest.fixture
def search_index(db: None) -> None:
    """Create the elasticsearch indices for the empty test database."""
    call_command("search_index", "--rebuild", "-f", stdout=StringIO())
