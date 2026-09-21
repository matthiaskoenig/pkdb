"""Exercise route enumeration against the real legacy Django URL resolver."""

from tools.backend_migration.contracts import collect_contracts


def test_real_routes_include_reads_writes_and_auth():
    """Test real routes include reads writes and auth."""
    rows = collect_contracts()
    assert any(
        "/api/v1/" in row["path"]
        and "studies" in row["path"]
        and row["method"] == "GET"
        for row in rows
    )
    assert any("_studies" in row["path"] and row["method"] == "POST" for row in rows)
    assert any(
        "api-token-auth" in row["path"] and row["method"] == "POST" for row in rows
    )
    assert len({(row["path"], row["method"]) for row in rows}) == len(rows)
