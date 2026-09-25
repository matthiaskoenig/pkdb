from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from pkdb.schemas.security import Principal
from pkdb_server.services.quotas import QuotaExceeded, QuotaService


@pytest.mark.parametrize("kind", ["session", "api_key", "legacy"])
def test_authenticated_requests_do_not_consume_any_quota(session_factory, kind):
    from types import SimpleNamespace

    from sqlalchemy import func

    from pkdb_server.db.models.limits import WorkLease
    from pkdb_server.db.models.users import AccountThrottle

    quotas = QuotaService(
        session_factory,
        SimpleNamespace(
            quota_ip_per_minute=1,
        ),
    )
    p = Principal(user_id=42, role="user", credential_kind=kind, credential_id=1)
    for operation in ("read", "upload", "export"):
        for _ in range(125):
            quotas.charge(p, "test-ip", operation)
            assert quotas.acquire(p, "test-ip", operation) is None
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(AccountThrottle)) == 0
        assert session.scalar(select(func.count()).select_from(WorkLease)) == 0


def test_anonymous_bulk_export_denied(session_factory):
    with pytest.raises(QuotaExceeded):
        QuotaService(session_factory).charge(Principal(), "test-ip", "export")


def test_shared_work_leases_release_and_expire(session_factory):
    from pkdb_server.db.models.limits import WorkLease

    quotas = QuotaService(session_factory)
    principal = Principal()
    lease = quotas.acquire(principal, "ip", "upload")
    with pytest.raises(QuotaExceeded):
        QuotaService(session_factory).acquire(principal, "ip", "upload")
    quotas.release(lease)
    lease = quotas.acquire(principal, "ip", "upload")
    with session_factory.begin() as session:
        for row in session.scalars(
            select(WorkLease).where(WorkLease.request_id == lease)
        ):
            row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    lease2 = quotas.acquire(principal, "ip", "upload")
    quotas.release(lease2)


def test_signed_in_requests_do_not_consume_anonymous_allowance(session_factory):
    from types import SimpleNamespace

    quotas = QuotaService(
        session_factory, SimpleNamespace(quota_anonymous_per_minute=2)
    )
    for _ in range(3):
        quotas.charge(Principal(user_id=42, role="user"), "shared-ip")
    quotas.charge(Principal(), "shared-ip")
    quotas.charge(Principal(), "shared-ip")
    with pytest.raises(QuotaExceeded):
        quotas.charge(Principal(), "shared-ip")


def test_anonymous_browsing_budget_remains_bounded(session_factory):
    quotas = QuotaService(session_factory)
    for _ in range(120):
        quotas.charge(Principal(), "browser-ip")
    with pytest.raises(QuotaExceeded):
        quotas.charge(Principal(), "browser-ip")


def test_combined_ip_budget_still_applies(session_factory):
    from types import SimpleNamespace

    quotas = QuotaService(session_factory, SimpleNamespace(quota_ip_per_minute=2))
    quotas.charge(Principal(), "shared-ip")
    quotas.charge(Principal(), "shared-ip")
    with pytest.raises(QuotaExceeded):
        quotas.charge(Principal(), "shared-ip")
