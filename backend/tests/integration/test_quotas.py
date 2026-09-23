from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from pkdb.schemas.security import Principal
from pkdb_server.services.quotas import QuotaExceeded, QuotaService


def test_account_quota_shared_across_keys_and_service_instances(session_factory):
    quotas = QuotaService(session_factory)
    other = QuotaService(session_factory)
    for index in range(120):
        p = Principal(
            user_id=42,
            role="user",
            credential_kind="api_key",
            credential_id=index // 40,
            scopes=frozenset({"read"}),
        )
        quotas.charge(p, "test-ip")
    with pytest.raises(QuotaExceeded) as error:
        other.charge(p.model_copy(update={"credential_id": 99}), "other-ip")
    assert 0 < error.value.retry_after <= 60
    assert quotas.usage(42)["account"]["requests"] == 120


def test_anonymous_bulk_export_denied(session_factory):
    with pytest.raises(QuotaExceeded):
        QuotaService(session_factory).charge(Principal(), "test-ip", "export")


def test_shared_work_leases_release_and_expire(session_factory):
    from pkdb_server.db.models.limits import WorkLease

    quotas = QuotaService(session_factory)
    principal = Principal(user_id=42, role="curator")
    lease = quotas.acquire(principal, "ip", "upload")
    with pytest.raises(QuotaExceeded):
        QuotaService(session_factory).acquire(principal, "different-ip", "upload")
    quotas.release(lease)
    lease = quotas.acquire(principal, "ip", "upload")
    with session_factory.begin() as session:
        for row in session.scalars(
            select(WorkLease).where(WorkLease.request_id == lease)
        ):
            row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    lease2 = quotas.acquire(principal, "ip", "upload")
    quotas.release(lease2)
