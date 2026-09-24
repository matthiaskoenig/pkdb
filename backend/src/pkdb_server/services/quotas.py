"""Shared fixed-window request budgets, independent of workers and transports."""

import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import insert

from pkdb_server.db.models.users import AccountThrottle


class QuotaExceeded(Exception):
    def __init__(self, retry_after):
        self.retry_after = retry_after


class QuotaService:
    def __init__(self, session_factory, settings=None):
        self.session_factory = session_factory
        self.settings = settings

    def limit(self, name, default):
        return getattr(self.settings, name, default)

    def charge(self, principal, ip, operation="read"):
        if principal.user_id is not None:
            return
        now = datetime.now(UTC)
        buckets = [
            (
                f"ip:{ip}",
                self.limit("quota_ip_per_minute", 600),
                60,
            )
        ]
        if not principal.user_id:
            buckets.append(
                (
                    f"anonymous-ip:{ip}",
                    self.limit("quota_anonymous_per_minute", 120),
                    60,
                )
            )
        if operation == "export":
            buckets.append((f"anonymous-export:{ip}", 0, 60))
        for_login = operation == "login"
        if for_login:
            buckets.append((f"login-ip:{ip}", 30, 600))
        if operation == "register":
            buckets.append((f"register-ip:{ip}", 20, 3600))
        # One transaction for all budgets; sorted keys avoid lock inversion.
        with self.session_factory.begin() as session:
            for label, limit, seconds in sorted(buckets):
                key = hashlib.sha256(("quota:" + label).encode()).hexdigest()
                statement = insert(AccountThrottle).values(
                    key=key, attempts=1, expires_at=now + timedelta(seconds=seconds)
                )
                row = session.execute(
                    statement.on_conflict_do_update(
                        index_elements=[AccountThrottle.key],
                        set_={
                            "attempts": case(
                                (AccountThrottle.expires_at <= now, 1),
                                else_=AccountThrottle.attempts + 1,
                            ),
                            "expires_at": case(
                                (
                                    AccountThrottle.expires_at <= now,
                                    now + timedelta(seconds=seconds),
                                ),
                                else_=AccountThrottle.expires_at,
                            ),
                        },
                    ).returning(AccountThrottle.attempts, AccountThrottle.expires_at)
                ).one()
                if row.attempts > limit:
                    raise QuotaExceeded(
                        max(1, int((row.expires_at - now).total_seconds()))
                    )

    def acquire(self, principal, ip, operation="read"):
        if principal.user_id is not None:
            return None
        from uuid import uuid4

        from sqlalchemy import delete, func, text

        from pkdb_server.db.models.limits import WorkLease

        identifier = uuid4().hex
        now = datetime.now(UTC)
        buckets = [
            (
                f"ip:{hashlib.sha256(ip.encode()).hexdigest()}",
                self.limit("quota_anonymous_concurrency", 2),
            )
        ]
        if operation in {"upload", "export"}:
            buckets += [
                (f"{operation}:{principal.user_id}", 1),
                (
                    f"{operation}:global",
                    self.limit(
                        "upload_concurrency"
                        if operation == "upload"
                        else "export_concurrency",
                        2,
                    ),
                ),
            ]
        with self.session_factory.begin() as session:
            for bucket, limit in sorted(buckets):
                lock = int.from_bytes(
                    hashlib.sha256(("lease:" + bucket).encode()).digest()[:8],
                    "big",
                    signed=True,
                )
                session.execute(
                    text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock}
                )
                session.execute(
                    delete(WorkLease).where(
                        WorkLease.bucket == bucket, WorkLease.expires_at <= now
                    )
                )
                count = session.scalar(
                    select(func.count())
                    .select_from(WorkLease)
                    .where(WorkLease.bucket == bucket)
                )
                if count >= limit:
                    raise QuotaExceeded(5)
                session.add(
                    WorkLease(
                        request_id=identifier,
                        bucket=bucket,
                        expires_at=now + timedelta(seconds=120),
                    )
                )
                session.flush()
        return identifier

    def renew(self, identifier):
        from sqlalchemy import update

        from pkdb_server.db.models.limits import WorkLease

        with self.session_factory.begin() as session:
            session.execute(
                update(WorkLease)
                .where(WorkLease.request_id == identifier)
                .values(expires_at=datetime.now(UTC) + timedelta(seconds=120))
            )

    def release(self, identifier):
        from sqlalchemy import delete

        from pkdb_server.db.models.limits import WorkLease

        with self.session_factory.begin() as session:
            session.execute(delete(WorkLease).where(WorkLease.request_id == identifier))
