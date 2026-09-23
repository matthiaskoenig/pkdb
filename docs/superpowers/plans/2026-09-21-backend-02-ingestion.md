# Backend Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a fully validated study atomically into the fresh PostgreSQL schema through an authenticated API.

**Architecture:** Parse and calculate before opening the write transaction, then lock the SID, recheck mutable invariants, and bulk-replace study-owned rows. Durable immutable files are staged before database publication and reclaimed separately.

**Tech Stack:** Both supported Pythons, SQLAlchemy 2, Psycopg 3, Alembic, PostgreSQL 18, FastAPI, Pydantic v2, Uvicorn, pwdlib/Argon2.

**Spec:** [Backend design](../specs/2026-09-21-backend-replacement-design.md). Depends on [foundations](2026-09-21-backend-01-foundations.md); follow the [index](2026-09-21-backend-replacement.md).

## Global Constraints

- Support CPython 3.13 and 3.14 on standard GIL-enabled builds.
- Declare `requires-python = ">=3.13,<3.15"` and Ruff `target-version = "py313"`.
- A study upload completely replaces that study's previous definition.
- Never share a session between requests or threads.
- The server always performs its own validation.
- Existing study SIDs and vocabulary identifiers remain stable.
- Shared users and vocabulary are not deleted.

## Review Focus

1. Two first uploads for the same absent SID race — I4.
2. Authorization or vocabulary changes between preparation and commit — I2/I4.
3. File staging succeeds but SQL commit fails — I3/I4.
4. A reader assembles a mixture of old and new children — I4.
5. An oversized multipart request fills memory before validation — I5 bounds reads, expanded rows and concurrent uploads.

## File and interface map

- `src/pkdb/db/models/`: `base.py`, `studies.py`, `subjects.py`, `interventions.py`, `measurements.py`, `vocabulary.py`, `users.py`, `files.py`.
- `src/pkdb/db/`: `session.py`, `bootstrap.py`, `replace.py`, `read.py`.
- `src/pkdb/services/`: `authorization.py`, `authentication.py`, `ingestion.py`.
- `src/pkdb/files/`: `store.py`, `cleanup.py`.
- `src/pkdb/api/`: `dependencies.py`, `errors.py`, `uploads.py`.
- `src/pkdb/schemas/`: `security.py`, `replacement.py`.
- `src/pkdb/app.py`, `alembic.ini`, `alembic/env.py`, `alembic/versions/`.
- Integration tests use real PostgreSQL through isolated test databases; no SQLite fallback.

Shared interfaces, defined in the owning task:

```python
# I1 db/session.py: configured factory; new Session for each call.
def make_session_factory(database_url: str) -> sessionmaker[Session]: ...
# I2 schemas/security.py
# Principal: user_id: int | None, username: str | None, role: str
# Action: Literal['read', 'write', 'delete', 'read_file', 'administer']
def authorize(principal: Principal, action: Action, study: StudyAccess) -> None: ...
# StudyAccess: sid, access, licence, creator_id, curator_ids, collaborator_ids
# I2: authentication.py
# AuthorizationDenied and AuthenticationFailed are domain exceptions.
def authenticate_token(raw_token: str, session: Session) -> Principal: ...
# I2 bootstrap.py
# BootstrapReport: inserted, unchanged, errors; errors are ValidationIssue records.
def bootstrap(directory: Path, session: Session) -> BootstrapReport: ...
# I3 files/store.py
# StagedFile: id: UUID, owner_id: int, digest: str, storage_key: str,
#             size: int, original_name: str, expires_at: datetime
# FileStore(root: Path, session_factory, max_bytes: int)
# stage(owner: Principal, original_name: str, source: BinaryIO) -> StagedFile
# open_authorized(principal: Principal, attachment_id: UUID) -> BinaryIO
# I4 schemas/replacement.py
# ReplacementResult: sid: str, created: bool, digest: str,
#                    counts: dict[str, int], warnings: list[ValidationIssue]
# I4 ingestion.py
# IngestionService(session_factory, file_store, settings)
# validate(bundle: SourceBundle, principal: Principal) -> PreparedStudy
# replace(bundle: SourceBundle, principal: Principal) -> ReplacementResult
# I5 app.py
# create_app(settings: Settings | None = None) -> FastAPI
```

### I1: Build and migrate the relational schema

**Files:** Create model/session/Alembic files above, `tests/integration/conftest.py`, `tests/integration/test_schema.py`, and `docker-compose-next-test.yml`. Modify replacement pyproject/lock with `sqlalchemy>=2,<3`, `psycopg[binary]`, and Alembic.

**Interfaces:** `Base` exposes metadata; `Study` has stable unique `sid` and integer root ID. Create factories `session_factory` and `db_session` in integration conftest. The `schema_seed` fixture inserts two independent study graphs plus a shared user and vocabulary node, with known SIDs `S1` and `S2`.

- [ ] Write the constraint test before creating models:

```python
import pytest
from sqlalchemy.exc import IntegrityError
from pkdb_server.db.models.studies import Study

def test_duplicate_sid_is_rejected(db_session, schema_seed):
    db_session.add(Study(sid='S1', name='duplicate', access='public', licence='open'))
    with pytest.raises(IntegrityError):
        db_session.flush()
```

- [ ] Run `uv run --project backend-next --locked pytest backend-next/tests/integration/test_schema.py -q`; expect missing-model failure. Implement tables one family at a time, translating all F1 fields. Keep units/statistics typed; ordered authors and timecourse points carry explicit positions. Use foreign keys/unique constraints to enforce stable keys, one reference association per legacy rules, and study-scoped relationships.
- [ ] Generate and review an initial Alembic migration. Commit it; do not generate migrations automatically on application startup. Add indexes for FK ownership, stable identifiers, and characterized exact/range filters. No speculative full-text index until A2 establishes its query contract.
- [ ] Test child deletion never deletes shared users/vocabulary; dangling references, cross-study associations, and duplicate ordered keys are rejected. Test empty database `upgrade head`, `alembic check`, and downgrade/upgrade on disposable DB. Add a PostgreSQL-only test service with a distinct project name and local port to avoid touching current containers. No Elasticsearch service in that file.
- [ ] Run integration tests on both Pythons, then commit as `feat: add fresh PostgreSQL schema and Alembic migrations`.

### I2: Bootstrap identities/vocabulary and enforce domain authorization

**Files:** Create `db/bootstrap.py`, `schemas/security.py`, `services/authorization.py`, `services/authentication.py`, `tests/integration/test_bootstrap.py`, `tests/unit/test_authorization.py`, `tests/integration/test_tokens.py`, `tests/fixtures/bootstrap/`.

**Interfaces:** Implement I2 declarations above. `Principal` is immutable. `admin`, `creator`, `curator`, `collaborator`, `reviewer`, `anonymous` fixtures provide principals; `private_study` provides a `StudyAccess`. Unknown roles deny. `bootstrap` reads versioned JSON vocabulary/user files and requires an explicit transaction owned by its caller; no network discovery or automatic credentials.

- [ ] Write and run the denied-write test first:

```python
import pytest
from pkdb_server.services.authorization import authorize, AuthorizationDenied

def test_public_read_does_not_allow_replacement(anonymous, private_study):
    study = private_study.model_copy(update={'access': 'public'})
    with pytest.raises(AuthorizationDenied):
        authorize(anonymous, 'write', study)
```

- [ ] Run `uv run --project backend-next --locked pytest backend-next/tests/unit/test_authorization.py -q`; expect missing authorization. Implement an explicit role/action table: admin can administer; creator/curator can change their study; collaborators can read it; reviewer reads across studies but cannot write without another authorized role; anonymous sees public studies. Files additionally require allowed licence/role. New-study creation requires an authenticated permitted curator/admin identity. Published-study write checks use existing ownership, never ownership supplied by the replacement payload. Only permitted administrators transfer ownership.
- [ ] Test all matrix cells, including PUT being a write, hidden statistics and file access. Resolve legacy ambiguities in `contracts.json` as intentional corrections rather than reproducing accidental anonymous writes.
- [ ] Bootstrap users disabled for login unless credentials are explicitly set; load vocabulary before studies. Add idempotency, missing user, duplicate node, unknown parent, and changed-version cases. Mutation increments a vocabulary version under a lock; prepared studies with an outdated version are rejected with `vocabulary_changed` and can be prepared again.
- [ ] Add pwdlib/Argon2; generate opaque tokens with `secrets.token_urlsafe(32)`; persist SHA-256 token digests, expiry, purpose, and revocation. Test expiry, revocation, token hashing, no raw token logs, and invalid-token rejection.
- [ ] Run unit/integration tests on both Pythons and commit as `feat: bootstrap reference data and centralize authorization`.

### I3: Stage immutable files and reclaim unreachable bytes

**Files:** Create file store/cleanup files, `tests/integration/test_files.py`. Extend `db/models/files.py` and create an explicit follow-up migration if needed.

**Interfaces:** Implement `FileStore` and `StagedFile`; stage files with random storage paths, not a globally exposed digest URL. `cleanup_expired_files(now: datetime, session_factory, file_store: FileStore) -> int` removes only unreferenced, expired files. A staged-file row is durable and owner-scoped. A live upload lease prevents collection; publication locks the same metadata row and verifies bytes.

- [ ] Write tests using a temporary directory and a real test database:

```python
import io
import pytest
from pkdb_server.services.authorization import AuthorizationDenied

def test_staged_file_is_not_public(file_store, creator, anonymous):
    staged = file_store.stage(creator, 'paper.pdf', io.BytesIO(b'%PDF-test'))
    with pytest.raises(AuthorizationDenied):
        file_store.open_authorized(anonymous, staged.id)
```

  Define `file_store` in integration conftest with the temporary root, `session_factory`, and a 1 MiB test limit; never serve that directory statically.
- [ ] Run `uv run --project backend-next --locked pytest backend-next/tests/integration/test_files.py -q`; expect missing store. Stream chunks with a counted byte limit; hash while writing, flush/fsync, and rename within the same filesystem before marking staged metadata ready. Failed stage removes its partial file. Treat original filenames as metadata.
- [ ] Add tests for traversal names, symlink escape, duplicate original names, oversized streams, corrupt/missing bytes, another user's handle, and owner-only draft access. File reads join to active study associations and authorize them.
- [ ] Add crash/cleanup tests: untracked files use a 24-hour grace period; staged files use expiry plus lease checks; published references are never collected. Cleanup locks/rechecks metadata before unlinking. Test a concurrent finalization/cleanup race and grace-period protection of old readers.
- [ ] Run tests on both Pythons; commit as `feat: stage protected attachments with recoverable cleanup`.

### I4: Atomically replace complete study graphs

**Files:** Create `services/ingestion.py`, `db/replace.py`, `db/read.py`, `schemas/replacement.py`, `tests/integration/test_replace.py`, `tests/integration/test_replace_concurrency.py`.

**Interfaces:** Implement `IngestionService`. `read_study(sid: str, principal: Principal, session_factory) -> CanonicalStudy` returns a graph using a consistent snapshot. The integration `ingestion` fixture supplies a service using real SQL, actual domain functions, test vocabulary/bootstrap, and `file_store`.

- [ ] Write the failed-replacement preservation test:

```python
import pytest
from pkdb.schemas.validation import StudyValidationError
from pkdb_server.db.read import read_study

def test_invalid_replacement_preserves_published_study(
    ingestion, valid_bundle, creator, session_factory
):
    result = ingestion.replace(valid_bundle, creator)
    before = read_study(result.sid, creator, session_factory)
    broken = valid_bundle.model_copy(deep=True)
    broken.study['sid'] = ''
    with pytest.raises(StudyValidationError):
        ingestion.replace(broken, creator)
    assert read_study(result.sid, creator, session_factory) == before
```

- [ ] Run `uv run --project backend-next --locked pytest backend-next/tests/integration/test_replace.py -q`; expect missing ingestion. Call parse/prepare once, stage files, then begin SQL transaction. Acquire `pg_advisory_xact_lock` on a deterministic signed 64-bit SHA-256-derived SID key (not Python's randomized hash). Recheck current owner, user status, vocabulary version, file ownership, and shared-reference constraints.
- [ ] Lock vocabulary version while checking it and committing so concurrent vocabulary updates cannot invalidate validated output. Apply the same locking discipline to ownership/user-state changes. Unique constraints arbitrate competing shared-reference assignments; translate integrity errors to reports.
- [ ] Retain the root ID, delete study-owned children, bulk insert in FK order, map returned keys explicitly, and associate staged files. Store report, source digest and processing versions. Commit once. Reference modification and author association changes occur in that transaction, never before publication.
- [ ] Add fault injection immediately after deletion and immediately before commit; assert the exact old graph survives both failures. Test omitted optional sets remove old data, same input does not duplicate rows, study root persists, another study/shared vocabulary stays intact, and revoked authorization prevents commit.
- [ ] Run two separate sessions with barriers: same missing SID yields one root and one complete final graph; two distinct SIDs proceed independently. Hold an old read snapshot across replacement; it must see entirely old data while a new reader sees entirely new data. Test cleanup and file publication failures.
- [ ] Count SQL statements for 10 versus 1,000 measurements; reference lookup count remains constant and inserts scale by configured chunks, not per-row queries. Re-run F1 matched upload budgets once the HTTP path exists in I5.
- [ ] Run both interpreter integration suites and commit as `feat: replace validated studies atomically with bulk persistence`.

### I5: Expose complete validation/replacement REST endpoints

**Files:** Create `app.py`, API files above, `tests/api/conftest.py`, `tests/api/test_uploads.py`, `tests/api/test_limits.py`; add FastAPI, Uvicorn and python-multipart to pyproject/lock. Update additive CI with PostgreSQL service.

**Interfaces:** `create_app(settings=None)` constructs services/lifecycles; omitted settings are loaded from the environment for Uvicorn factory startup. `client` fixture uses FastAPI TestClient with lifespan enabled and explicit test settings; `creator_headers` issues a real test token. `bundle_multipart` fixture encodes `valid_bundle` as `study`/`reference` JSON form fields and repeated `files` parts whose filenames map to source filenames.

- [ ] Write the dry-run HTTP test:

```python
from sqlalchemy import func, select
from pkdb_server.db.models.studies import Study

def test_validation_does_not_publish(client, creator_headers,
                                     bundle_multipart, db_session):
    response = client.post('/api/v2/studies/validate', headers=creator_headers,
                           **bundle_multipart)
    assert response.status_code == 200
    assert response.json()['valid'] is True
    assert db_session.scalar(select(func.count()).select_from(Study)) == 0
```

- [ ] Run `uv run --project backend-next --locked pytest backend-next/tests/api/test_uploads.py -q`; expect missing app/route. Add sync route handlers delegating to ingestion; dependencies create principals, not shared sessions. Multipart parsing/staging enforces counted stream limits before buffering complete bodies; Content-Length alone is not trusted. Close all files on every exit path.
- [ ] Define response contracts: validation report 200 when valid, 422 on invalid content; replacement 201 for creation, 200 for replacement; 401 invalid/missing credentials, 403 unauthorized action, 409 concurrent mutable-state conflict, 413 size limit, 422 malformed content/SID mismatch, 503 admission limit with Retry-After. Hide internals in 500 responses while logging request IDs.
- [ ] Test both first and replacement PUT, bad JSON, SID mismatch, malformed multipart, unknown file handles, absent credentials, invalid vocabulary, oversize chunked input, row expansion limit, and cancelled clients. Test dry-run cleanup. After reported success public read service sees complete data.
- [ ] Add liveness (process alive) and readiness (database reachable, schema at head, file root usable) endpoints; no credentials or detailed SQL errors in responses. Run startup/API tests and matched ingestion benchmarks on both Pythons, then commit as `feat: expose authenticated complete-study API`.

## Phase acceptance

- [ ] Alembic builds an empty PostgreSQL database without legacy services.
- [ ] Failure/concurrency/file tests prove atomic replacement, not just happy paths.
- [ ] Every REST write uses central authorization and independent server validation.
- [ ] Both interpreter suites pass and concrete F1 upload budgets are met or an investigated regression is reviewed before continuing.
