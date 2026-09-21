"""Tests that the public API documentation survives in the swagger schema.

`drf_yasg` builds the `summary` and `description` of an operation from the
view docstrings: it prefers the docstring of the view METHOD over the
docstring of the view CLASS. The docstring work of task 5 added method
docstrings where there were none, and for `PKDataView.get` (`/api/v1/filter/`)
and `StatisticsViewSet.list` (`/api/v1/statistics/`) this silently replaced
the public documentation that users of the API see in swagger. These tests
guard the restored documentation.
"""

import pytest
from rest_framework.test import APIClient

# HTTP methods which can carry an operation in the swagger schema.
_OPERATION_METHODS = {"get", "post", "put", "patch", "delete"}

# operations which already had no `summary` before the docstring work of
# task 5 (commit f5f1d471), excluded from the completeness guard below.
OPERATIONS_WITHOUT_SUMMARY = {
    ("/info_nodes/", "get"),
    ("/info_nodes/{sid}/", "get"),
    ("/statistics/substances/", "get"),
}

# the six filter prefixes documented for `PKDataView.get`.
FILTER_PREFIXES = (
    "studies__",
    "groups__",
    "individuals__",
    "interventions__",
    "outputs__",
    "subsets__",
)


def _fetch_swagger_schema() -> dict:
    """Fetch `/api/v1/swagger.json` and return the decoded schema."""
    response = APIClient().get("/api/v1/swagger.json")
    assert response.status_code == 200, response.content[:500]
    return response.json()


@pytest.fixture
def swagger_schema(db: None) -> dict:
    """Fetch the swagger schema once for a test."""
    return _fetch_swagger_schema()


@pytest.mark.django_db
def test_filter_operation_keeps_its_public_documentation(
    swagger_schema: dict,
) -> None:
    """`/filter/` keeps its old summary and its old, detailed description."""
    operation = swagger_schema["paths"]["/filter/"]["get"]
    assert operation["summary"] == "Endpoint to filter and query data."

    description = operation["description"]
    for term in ("uuid", "download", "concise", *FILTER_PREFIXES):
        assert term in description, f"{term!r} missing from the description"


@pytest.mark.django_db
def test_statistics_operation_keeps_its_public_documentation(
    swagger_schema: dict,
) -> None:
    """`/statistics/` keeps its old summary and gets back a real description."""
    operation = swagger_schema["paths"]["/statistics/"]["get"]
    assert operation["summary"].startswith("Endpoint to query PK-DB statistics")

    description = operation["description"]
    assert (
        description
        == "Get database statistics consisting of count and version information."
    )


@pytest.mark.django_db
def test_every_operation_has_a_summary(swagger_schema: dict) -> None:
    """Every operation of the schema has a summary, except a named exception list.

    Guards against silently losing an operation's summary, the way
    `PKDataView.get` and `StatisticsViewSet.list` lost theirs; see the two
    tests above. The set of operations without a summary must equal
    `OPERATIONS_WITHOUT_SUMMARY` exactly: once an exempt operation gets a
    summary, it has to be removed from that constant too.
    """
    without_summary = {
        (path, method)
        for path, methods in swagger_schema["paths"].items()
        for method, operation in methods.items()
        if method in _OPERATION_METHODS and not operation.get("summary")
    }
    assert without_summary == OPERATIONS_WITHOUT_SUMMARY
