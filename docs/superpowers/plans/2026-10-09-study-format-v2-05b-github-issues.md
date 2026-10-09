---
search:
  exclude: true
---

# Study format 2 migration, part B: GitHub issues Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `pkdb issues sync [--adopt] [--dry-run]` keeps exactly one GitHub issue per format 2 study in matthiaskoenig/pkdb_data, with the canonical title, the substance and workflow labels, the curators and reviewers as assignees and the right open or closed state, using a new `GET /api/v2/curators` roster for GitHub logins.

**Architecture:** A small GitHub REST client (`python/src/pkdb/issues/github.py`, httpx2) does paging, writes, rate-limit waits and error messages, and the curation app's read-only issue lookup moves onto it. A pure planner (`issues/state.py`) reads every format 2 study of the checkout, computes the desired state of its issue and the changes against GitHub; `issues/adopt.py` matches studies without an issue to existing issues; `issues/sync.py` applies adoptions and the plan in order, writing files only in adopt mode through the revision-checked writers. The server lists curators with their GitHub logins at `GET /api/v2/curators`, and the Python client reads it with `Client.curators()`.

**Tech Stack:** Python 3.14, httpx2 (`httpx2.MockTransport` in tests), Pydantic 2, FastAPI and SQLAlchemy (backend), argparse, pytest, ruff, ty.

**Spec:** `docs/superpowers/specs/2026-10-08-study-format-v2-05-migration-design.md` (section 5, section 8 "GitHub" and "Backend") and `docs/superpowers/specs/2026-10-05-study-format-v2-design.md` (section 12).

## Global Constraints

- **Python:** 3.14. Run from `python/`: `uv run --locked pytest -q -x`, `uv run --locked ruff check .`, `uv run --locked ruff format --check .`, `uv run --locked ty check`. Every commit keeps them green.
- **Backend:** tests need the disposable test database: from the repository root `docker compose -f compose.test.yaml up -d --wait`, `export PKDB_TEST_DATABASE_URL=postgresql+psycopg://pkdb_test:local-test-only@127.0.0.1:15439/pkdb_test`, `uv run --project backend pytest backend/tests -q -x`; ruff and ty from `backend/` as for `python/`. Never touch deployment data volumes.
- **Lock files:** a change of `python/pyproject.toml` also needs `uv lock` in `python/` and in `backend/` (the backend installs `pkdb` from `../python`); keep `revision = 3` in both lock files.
- **Docs:** when a Markdown file changes, run `uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean` from the repository root; it must print no warning.
- **Writing:** never use the em dash character; Markdown paragraphs on one source line; no attribution lines in commits, docs or code; user-facing text in plain, short English sentences.
- **Generated files:** never hand-edit `docs/study-format.md`, any `CHANGELOG.md`, or the curation contract fixtures.
- **No real GitHub in tests:** every test talks to GitHub through `httpx2.MockTransport`; tests never write into pkdb_data.
- **Secrets:** the GitHub token and the PK-DB API key never appear in output, error messages or reports.
- **Values from the spec:** title `<substance>/<name>`; workflow labels `curate` (draft), `check` (in_review), `approved` (approved); token from `GH_TOKEN` or `GITHUB_TOKEN`; repository from `PKDB_ISSUES_REPO`, default `matthiaskoenig/pkdb_data`; adoption prefixes `Curate `, `Check `, `Check and curate `; duplicate comment `Duplicate of #N`; closed as completed exactly when the study has a `release` block and review status `approved`.
- **Plan decisions where the spec is silent:**
  - The roster lists users with role `admin`, `curator` or `reviewer`, active or not (imported roster users stay inactive until invited); `name` is `display_name`, else first and last name, else the username.
  - The command uses the repository's `--format human|json` convention instead of the spec's `--json`.
  - Only a `draft` study becomes `in_review` on adoption; an approved study is never downgraded.
  - Assignees are limited to users GitHub lists as assignable in the repository and to at most 10 per issue (GitHub's limit); the others are warnings.
  - Label colors: `curate` `fbca04`, `check` `1d76db`, `approved` `0e8a16`, substance labels `c5def5`.
  - A GitHub answer 401 or 403 that is not a rate limit stops the run; other failures of one issue are errors of that study and the run goes on.
  - Writes are at least one second apart, as GitHub asks for mutating requests.

## Review Focus

1. **Two studies name one issue number** (a copy-paste of `study.json`): both are errors, neither issue is changed, the run goes on for the others and exits 1. Test in Task 6 (`test_two_studies_with_one_issue_are_errors_and_untouched`) and Task 8 (`test_sync_exits_with_errors_and_changes_the_rest`).
2. **GitHub limits the requests mid-run** (secondary limit with `Retry-After`, or an exhausted hourly limit): the client waits and goes on; a 403 that is not a rate limit (no permission) stops at once with GitHub's message and never shows the token. Tests in Task 4 (`test_waits_for_retry_after`, `test_waits_for_the_reset_of_an_exhausted_limit`, `test_a_forbidden_request_is_an_error_without_the_token`).
3. **An adoption run stops after GitHub changed but before `study.json` got the number** (Ctrl-C, a crash): the rerun finds the renamed or created issue by its exact title and adopts it instead of creating a second issue. Test in Task 8 (`test_an_interrupted_adoption_is_finished_by_the_rerun`).
4. **Users the sync cannot assign** (no GitHub login, not in the roster, not assignable in the repository, more than 10): the issue gets the others, each case is one warning, and the issue update never fails because of them. Test in Task 6 (`test_unassignable_users_are_warnings`).
5. **`study.json` changes on disk during an adoption** (a curator saves in the curation app): the revision check refuses the write, the study is an error, no file is written over, and the other studies go on. Test in Task 8 (`test_a_changed_study_json_is_not_written_over`).

---

## File Structure

| File | Responsibility |
|---|---|
| `python/src/pkdb/schemas/curators.py` | Shared response model of `GET /api/v2/curators`: `Curator`, `CuratorList`. |
| `backend/src/pkdb_server/api/curators.py` | The route `GET /api/v2/curators`. |
| `backend/src/pkdb_server/app.py` | Register the router. |
| `backend/src/pkdb_server/api/reference.py` | Tag the route as Curation. |
| `python/src/pkdb/client.py` | `Client.curators()`. |
| `python/src/pkdb/repository.py` | The pkdb_data checkout: root, study folders, locations, substances (moved out of `migration/run.py`). |
| `python/src/pkdb/issues/__init__.py` | Package docstring. |
| `python/src/pkdb/issues/github.py` | GitHub REST client: paging, issues, labels, writes, rate-limit waits, errors, token and repository from the environment. |
| `python/src/pkdb/curation/github.py` | Curation app lookup on the new client. |
| `python/src/pkdb/issues/state.py` | Read the studies; desired state; the sync plan (pure). |
| `python/src/pkdb/issues/adopt.py` | Match studies without issue to issues (pure). |
| `python/src/pkdb/issues/sync.py` | Apply adoptions and the plan; `SyncResult`. |
| `python/src/pkdb/issues_cli.py` | `pkdb issues sync`. |
| `python/src/pkdb/cli.py` | Register and dispatch `issues`. |
| `docs/api.md`, `docs/python-client.md`, `docs/local-curation.md` | Route, command, environment. |

---

### Task 1: The curator roster route

**Files:**
- Create: `python/src/pkdb/schemas/curators.py`, `backend/src/pkdb_server/api/curators.py`, `backend/tests/api/test_curators.py`
- Modify: `backend/src/pkdb_server/app.py` (import block near line 30, `include_router` near line 581), `backend/src/pkdb_server/api/reference.py` (`category`, line 38), `docs/api.md` (endpoint table near line 26)

**Interfaces:**
- Consumes: `request.app.state.principal(request, required=True)`, `pkdb_server.services.authorization.require_scope`, `pkdb_server.db.models.users.User` (`username`, `role`, `display_name`, `first_name`, `last_name`, `github`, `github_visible`).
- Produces:
  - `pkdb.schemas.curators.Curator(username: str, name: str, github: str | None = None)` and `CuratorList(curators: list[Curator])`, both `ConfigDict(extra="ignore")`.
  - `GET /api/v2/curators` -> `{"curators": [{"username", "name", "github"}, ...]}` sorted by username; 401 without credentials.

- [ ] **Step 1: Write the failing tests**

`backend/tests/api/test_curators.py`:

```python
"""The curator roster lists GitHub logins for the issue sync, also hidden ones."""

from datetime import UTC, datetime, timedelta

from pkdb_server.db.models.credentials import ApiKey
from pkdb_server.db.models.users import User
from pkdb_server.services.credentials import digest


def key_for(session, user):
    secret = f"pkdb_live_curators_{user.id}"
    session.add(
        ApiKey(
            user_id=user.id,
            name="roster test",
            prefix=secret[:17],
            digest=digest(secret),
            scopes=["read"],
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    return {"Authorization": f"Bearer {secret}"}


def test_the_roster_needs_credentials(client):
    assert client.get("/api/v2/curators").status_code == 401


def test_the_roster_lists_curators_with_hidden_github_logins(client, session_factory):
    with session_factory.begin() as session:
        session.add_all(
            [
                User(
                    username="hidden",
                    role="curator",
                    display_name="Hidden Person",
                    github="hidden-gh",
                    github_visible=False,
                ),
                User(username="rev", role="reviewer", first_name="Re", last_name="Viewer"),
                User(username="boss", role="admin", github="boss-gh"),
                User(username="plain", role="user", github="plain-gh"),
            ]
        )
        reader = User(username="reader", role="user", active=True)
        session.add(reader)
        session.flush()
        headers = key_for(session, reader)
    response = client.get("/api/v2/curators", headers=headers)
    assert response.status_code == 200
    rows = {row["username"]: row for row in response.json()["curators"]}
    assert rows["hidden"] == {"username": "hidden", "name": "Hidden Person", "github": "hidden-gh"}
    assert rows["rev"] == {"username": "rev", "name": "Re Viewer", "github": None}
    assert rows["boss"]["name"] == "boss"
    assert "plain" not in rows and "reader" not in rows
    names = [row["username"] for row in response.json()["curators"]]
    assert names == sorted(names)
```

If `User` needs more fields to be inserted (check `db/models/users.py` and the `ingestion_context` fixture in `backend/tests/db_fixtures.py`), add the minimum and keep the assertions.

- [ ] **Step 2: Run the tests to verify they fail**

Run (repository root, test database up): `uv run --project backend pytest backend/tests/api/test_curators.py -q`
Expected: FAIL, 404 for `/api/v2/curators`.

- [ ] **Step 3: Implement**

`python/src/pkdb/schemas/curators.py`:

```python
"""The curator roster of a PK-DB server, read by the GitHub issue sync."""

from pydantic import BaseModel, ConfigDict


class Curator(BaseModel):
    model_config = ConfigDict(extra="ignore")
    username: str
    name: str
    github: str | None = None


class CuratorList(BaseModel):
    model_config = ConfigDict(extra="ignore")
    curators: list[Curator]
```

`backend/src/pkdb_server/api/curators.py`:

```python
"""The curator roster with GitHub logins, for the GitHub issue sync of study folders."""

from fastapi import APIRouter, Request
from sqlalchemy import select

from pkdb.schemas.curators import Curator, CuratorList
from pkdb_server.db.models.users import User
from pkdb_server.services.authorization import require_scope

router = APIRouter(prefix="/api/v2")
ROLES = ("admin", "curator", "reviewer")


def _name(user: User) -> str:
    full = " ".join(part for part in (user.first_name, user.last_name) if part)
    return user.display_name or full or user.username


@router.get("/curators", response_model=CuratorList)
def curators(request: Request) -> CuratorList:
    """Every administrator, curator and reviewer with name and GitHub login.

    Logins are listed also when a user hides them on the profile, because assigning
    the user to a GitHub issue shows the login there anyway.
    """
    actor = request.app.state.principal(request, required=True)
    require_scope(actor, "read")
    with request.app.state.session_factory() as session:
        users = session.scalars(
            select(User).where(User.role.in_(ROLES)).order_by(User.username)
        ).all()
        return CuratorList(
            curators=[
                Curator(username=user.username, name=_name(user), github=user.github or None)
                for user in users
            ]
        )
```

Register it in `app.py`: add `curators` to the `from pkdb_server.api import (...)` block and `app.include_router(curators.router)` next to `app.include_router(curation.router)`. In `api/reference.py` `category`, return `"Curation"` for `path == "/api/v2/curators"` before the generic `/api/v2/` rule. If `tests/api/test_reference.py` lists the paths of a tag, extend it.

`docs/api.md`: add the table row `| GET /api/v2/curators | Administrators, curators and reviewers with name and GitHub login, for the GitHub issue sync; needs an API key |` after the capabilities row, and below the table one paragraph: `GET /api/v2/curators` lists GitHub logins also of users who hide them on their profile, because assigning a user to a GitHub issue shows the login there anyway. Build the docs.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --project backend pytest backend/tests/api/test_curators.py backend/tests/api/test_reference.py backend/tests/api/test_profile_visibility.py -q`, then the whole backend suite once, ruff and ty in `backend/` and `python/`.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/schemas/curators.py backend/src/pkdb_server/api/curators.py backend/src/pkdb_server/app.py backend/src/pkdb_server/api/reference.py backend/tests/api/test_curators.py docs/api.md
git commit -m "List curators with their GitHub logins at GET /api/v2/curators"
```

---

### Task 2: `Client.curators()`

**Files:**
- Modify: `python/src/pkdb/client.py` (next to `identity`, line 376), `python/tests/test_client.py`, `docs/python-client.md` (section "Prepare and upload from Python", line 148)

**Interfaces:**
- Consumes: Task 1 `CuratorList`, `Curator`; `Client._request`, `Client._headers(required=True)`, `Client._model`.
- Produces: `Client.curators() -> list[Curator]`; raises `ClientError` like `identity()`.

- [ ] **Step 1: Write the failing test** in `python/tests/test_client.py`, following the file's MockTransport pattern:

```python
def test_curators_are_read_with_the_api_key():
    seen = []

    def handler(request):
        seen.append(request)
        assert request.url.path == "/api/v2/curators"
        return httpx2.Response(
            200,
            json={
                "curators": [
                    {"username": "ana", "name": "Ana", "github": "ana-gh", "extra": 1},
                    {"username": "bo", "name": "Bo", "github": None},
                ]
            },
        )

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        with Client(endpoint="https://example.test", api_key="pkdb_live_x", transport=transport) as client:
            curators = client.curators()
    assert [(c.username, c.github) for c in curators] == [("ana", "ana-gh"), ("bo", None)]
    assert seen[0].headers["authorization"] == "Bearer pkdb_live_x"


def test_curators_need_an_api_key():
    with Client(endpoint="https://example.test", api_key=None) as client:
        with pytest.raises(ClientError, match="PKDB_API_KEY"):
            client.curators()
```

Clear `PKDB_API_KEY` in the second test with `monkeypatch.delenv("PKDB_API_KEY", raising=False)` if the file has no autouse fixture for it.

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --locked pytest -q tests/test_client.py -k curators`
Expected: FAIL, `AttributeError: 'Client' object has no attribute 'curators'`.

- [ ] **Step 3: Implement** in `client.py` (import `Curator, CuratorList` from `pkdb.schemas.curators`):

```python
    def curators(self) -> list[Curator]:
        """Administrators, curators and reviewers of the server with their GitHub logins."""
        value = self._model(
            CuratorList,
            self._request("GET", "/api/v2/curators", headers=self._headers(required=True)),
        )
        return value.curators
```

`docs/python-client.md`: one sentence in "Prepare and upload from Python": `client.curators()` lists the administrators, curators and reviewers of the server with their GitHub logins; it needs an API key.

- [ ] **Step 4: Run to verify it passes**, then the full suite, ruff, ty, docs build.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/client.py python/tests/test_client.py docs/python-client.md
git commit -m "Read the curator roster with Client.curators()"
```

---

### Task 3: Repository helpers shared by migrate and the issue sync

**Files:**
- Create: `python/src/pkdb/repository.py`, `python/tests/test_repository.py`
- Modify: `python/src/pkdb/migration/run.py` (`STUDIES` line 53, `repository_root` line 81, `_location` line 90, `_subfolders` line 114), `python/src/pkdb/migration_cli.py` (its import of `repository_root`)

**Interfaces:**
- Produces:
  - `repository.STUDIES = "studies"`.
  - `repository.repository_root(path: Path) -> Path`: unchanged behavior (walk up to the folder that contains `studies/`; `ValueError` otherwise).
  - `repository.subfolders(folder: Path) -> list[Path]`: non-hidden folders that are not symbolic links.
  - `repository.location(folder: Path) -> str`: `<substance>/<name>`.
  - `repository.study_folders(root: Path) -> list[Path]`: every `root/studies/<substance>/<name>` folder, in natural order of the location.
  - `repository.substances(root: Path) -> list[str]`: names of the substance folders, natural order.
- `migration.run` imports these instead of defining its own; `run.repository_root` stays importable.

- [ ] **Step 1: Write the failing tests** `python/tests/test_repository.py`:

```python
import pytest

from pkdb.repository import location, repository_root, study_folders, substances


def make(root, *locations):
    for value in locations:
        (root / "studies" / value).mkdir(parents=True)


def test_the_root_is_found_from_a_study_folder(tmp_path):
    make(tmp_path, "caffeine/Harder1988")
    assert repository_root(tmp_path / "studies" / "caffeine" / "Harder1988") == tmp_path
    with pytest.raises(ValueError, match="studies"):
        repository_root(tmp_path.parent)


def test_study_folders_in_natural_order_without_hidden_and_links(tmp_path):
    make(tmp_path, "caffeine/Study10", "caffeine/Study2", "acetaminophen/A1", "caffeine/.hidden")
    (tmp_path / "studies" / "caffeine" / "link").symlink_to(tmp_path / "studies" / "caffeine" / "Study2")
    assert [location(p) for p in study_folders(tmp_path)] == [
        "acetaminophen/A1",
        "caffeine/Study2",
        "caffeine/Study10",
    ]
    assert substances(tmp_path) == ["acetaminophen", "caffeine"]
```

- [ ] **Step 2: Run to verify it fails**: `uv run --locked pytest -q tests/test_repository.py` -> FAIL, module not found.

- [ ] **Step 3: Implement** `python/src/pkdb/repository.py`:

```python
"""A pkdb_data checkout: its root folder and its study folders."""

from pathlib import Path

from pkdb.studyformat.text import natural_key

STUDIES = "studies"


def repository_root(path: Path) -> Path:
    """The folder that contains `studies/`, found by walking up from `path`."""
    path = Path(path).resolve()
    for folder in (path, *path.parents):
        if (folder / STUDIES).is_dir():
            return folder
    raise ValueError(f"No folder above {path} contains a studies folder")


def subfolders(folder: Path) -> list[Path]:
    """Folders below `folder`, without hidden folders and symbolic links."""
    return [
        path
        for path in folder.iterdir()
        if not path.name.startswith(".") and path.is_dir(follow_symlinks=False)
    ]


def location(folder: Path) -> str:
    """The `<substance>/<name>` of a study folder."""
    return f"{folder.parent.name}/{folder.name}"


def study_folders(root: Path) -> list[Path]:
    """Every `studies/<substance>/<name>` folder of the checkout, in natural order."""
    folders = [
        study
        for substance in subfolders(root / STUDIES)
        for study in subfolders(substance)
    ]
    return sorted(folders, key=lambda folder: natural_key(location(folder)))


def substances(root: Path) -> list[str]:
    """The substance folder names of the checkout, in natural order."""
    return sorted((folder.name for folder in subfolders(root / STUDIES)), key=natural_key)
```

In `migration/run.py`, delete its `STUDIES`, `repository_root`, `_location` and `_subfolders` definitions and import `STUDIES, location, repository_root, subfolders` from `pkdb.repository`; replace the calls of `_location` and `_subfolders` by `location` and `subfolders`. Update `migration_cli.py` to import `repository_root` from `pkdb.repository` (keep the old import working through `run`). Behavior of migrate must not change.

- [ ] **Step 4: Run** `uv run --locked pytest -q tests/test_repository.py tests/migration` -> PASS; full suite, ruff, ty.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/repository.py python/tests/test_repository.py python/src/pkdb/migration/run.py python/src/pkdb/migration_cli.py
git commit -m "Share the repository root and study folder discovery of pkdb_data checkouts"
```

---

### Task 4: GitHub REST client

**Files:**
- Create: `python/src/pkdb/issues/__init__.py`, `python/src/pkdb/issues/github.py`, `python/tests/issues/__init__.py` (empty), `python/tests/issues/test_github.py`

**Interfaces:**
- Produces (all in `pkdb.issues.github`):
  - Constants `API = "https://api.github.com"`, `DEFAULT_REPOSITORY = "matthiaskoenig/pkdb_data"`, `PER_PAGE = 100`, `MAX_PAGES = 1000`, `MAX_WAITS = 5`, `WRITE_INTERVAL = 1.0`.
  - `GitHubError(RuntimeError)` with `status_code: int | None`.
  - `Issue` (frozen dataclass): `number: int`, `title: str`, `state: str` (`open`/`closed`), `state_reason: str | None`, `labels: tuple[str, ...]`, `assignees: tuple[str, ...]`; `Issue.from_api(data: dict) -> Issue`.
  - `repository_from(value: str | None = None, environ: Mapping[str, str] = os.environ) -> str`: `value`, else `PKDB_ISSUES_REPO`, else the default; `ValueError("GitHub repository must be owner/name")` when it is not `owner/name`.
  - `token_from(environ: Mapping[str, str] = os.environ) -> str | None`: `GH_TOKEN`, else `GITHUB_TOKEN`, else None.
  - `GitHub(repository: str, token: str | None = None, *, transport=None, sleep=time.sleep, clock=time.time, write_interval: float = WRITE_INTERVAL, max_wait: float | None = None)`: context manager. `max_wait`: a rate-limit wait longer than this raises `GitHubError` instead of sleeping (the curation app passes 0).
    - `pages(resource: str, params: Mapping[str, str | int] | None = None) -> list[dict]`: raw items of a list resource below the repository (`issues` with `state=all`, `assignees`, `labels`), page by page with `per_page=100` and `page=N` until a short page; `GitHubError` when a page is not a list or beyond `MAX_PAGES`.
    - `issues() -> list[Issue]`: every issue in all states, without pull requests.
    - `assignable() -> set[str]`: logins of `assignees`, without bots.
    - `labels() -> list[str]`.
    - `create_label(name: str, color: str) -> None`.
    - `create_issue(title: str, *, labels: list[str], assignees: list[str]) -> Issue`.
    - `update_issue(number: int, *, title: str | None = None, labels: list[str] | None = None, assignees: list[str] | None = None, state: str | None = None, state_reason: str | None = None) -> Issue` (sends only the given fields).
    - `comment(number: int, body: str) -> None`.

Requests: headers `Accept: application/vnd.github+json`, `X-GitHub-Api-Version: 2022-11-28`, `User-Agent: pkdb/<version>`, and `Authorization: Bearer <token>` when a token is set; timeout 30 s. A response 403 or 429 is a rate limit when it has `Retry-After` (wait that many seconds, at least 1) or `x-ratelimit-remaining: 0` (wait until `x-ratelimit-reset` plus 1 second, from `clock`); after `MAX_WAITS` waits, or a wait above `max_wait`, it raises `GitHubError`. Any other error status raises `GitHubError(f"GitHub answered {status} for {method} {path}: {message}", status_code=status)` with GitHub's `message`; a transport error raises `GitHubError("GitHub cannot be reached: ...")`. Writes (`POST`, `PATCH`) wait until `write_interval` seconds passed since the previous write.

- [ ] **Step 1: Write the failing tests** `python/tests/issues/test_github.py`:

```python
import json

import httpx2
import pytest

from pkdb.issues.github import (
    DEFAULT_REPOSITORY,
    GitHub,
    GitHubError,
    repository_from,
    token_from,
)


class Clock:
    def __init__(self, now=1000.0):
        self.now = now
        self.slept = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


def github(handler, clock=None, **options):
    clock = clock or Clock()
    return GitHub(
        "owner/data",
        "secret-token",
        transport=httpx2.MockTransport(handler),
        sleep=clock.sleep,
        clock=clock.time,
        **options,
    )


def issue(number, **fields):
    return {"number": number, "title": f"drug/S{number}", "state": "open", "labels": [], "assignees": [], **fields}


def test_issues_of_all_pages_without_pull_requests():
    pages = []

    def handler(request):
        page = int(request.url.params["page"])
        pages.append((request.url.path, request.url.params["state"], page))
        assert request.headers["authorization"] == "Bearer secret-token"
        if page == 1:
            return httpx2.Response(200, json=[issue(n) for n in range(1, 100)] + [{**issue(100), "pull_request": {}}])
        return httpx2.Response(200, json=[issue(101, labels=[{"name": "curate"}], assignees=[{"login": "ana"}])])

    with github(handler) as client:
        issues = client.issues()
    assert [i.number for i in issues] == [*range(1, 100), 101]
    assert issues[-1].labels == ("curate",) and issues[-1].assignees == ("ana",)
    assert pages == [("/repos/owner/data/issues", "all", 1), ("/repos/owner/data/issues", "all", 2)]


def test_waits_for_retry_after():
    answers = [httpx2.Response(403, headers={"retry-after": "7"}, json={"message": "secondary"}), httpx2.Response(200, json=[])]
    clock = Clock()
    with github(lambda request: answers.pop(0), clock) as client:
        assert client.issues() == []
    assert clock.slept == [7.0]


def test_waits_for_the_reset_of_an_exhausted_limit():
    clock = Clock(now=1000.0)
    answers = [
        httpx2.Response(403, headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1060"}, json={"message": "limit"}),
        httpx2.Response(200, json=[]),
    ]
    with github(lambda request: answers.pop(0), clock) as client:
        client.labels()
    assert clock.slept == [61.0]


def test_a_wait_above_max_wait_is_an_error():
    response = httpx2.Response(429, headers={"retry-after": "30"}, json={"message": "slow down"})
    with github(lambda request: response, max_wait=0) as client:
        with pytest.raises(GitHubError, match="limit"):
            client.issues()


def test_a_forbidden_request_is_an_error_without_the_token():
    response = httpx2.Response(403, json={"message": "Resource not accessible by integration"})
    clock = Clock()
    with github(lambda request: response, clock) as client:
        with pytest.raises(GitHubError) as error:
            client.update_issue(5, title="drug/S5")
    assert error.value.status_code == 403
    assert "Resource not accessible by integration" in str(error.value)
    assert "secret-token" not in str(error.value)
    assert clock.slept == []


def test_writes_send_only_the_given_fields_one_second_apart():
    bodies = []

    def handler(request):
        bodies.append((request.method, request.url.path, json.loads(request.content)))
        return httpx2.Response(200, json=issue(5, title="drug/S5", state="closed", state_reason="completed"))

    clock = Clock()
    with github(handler, clock) as client:
        updated = client.update_issue(5, state="closed", state_reason="completed")
        client.comment(6, "Duplicate of #5")
    assert bodies[0] == ("PATCH", "/repos/owner/data/issues/5", {"state": "closed", "state_reason": "completed"})
    assert bodies[1] == ("POST", "/repos/owner/data/issues/6/comments", {"body": "Duplicate of #5"})
    assert updated.state_reason == "completed"
    assert clock.slept == [1.0]


def test_repository_and_token_from_the_environment():
    assert repository_from(environ={}) == DEFAULT_REPOSITORY
    assert repository_from(environ={"PKDB_ISSUES_REPO": "me/data"}) == "me/data"
    assert repository_from("you/data", environ={"PKDB_ISSUES_REPO": "me/data"}) == "you/data"
    with pytest.raises(ValueError, match="owner/name"):
        repository_from("not a repository", environ={})
    assert token_from({"GITHUB_TOKEN": "b"}) == "b"
    assert token_from({"GH_TOKEN": "a", "GITHUB_TOKEN": "b"}) == "a"
    assert token_from({}) is None
```

- [ ] **Step 2: Run to verify it fails**: `uv run --locked pytest -q tests/issues/test_github.py` -> FAIL, module not found.

- [ ] **Step 3: Implement** `python/src/pkdb/issues/__init__.py` (docstring `"""GitHub issues of the studies of a pkdb_data checkout."""`) and `python/src/pkdb/issues/github.py`:

```python
"""A small GitHub REST client for the issues of the pkdb_data repository."""

import os
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import httpx2

from pkdb import __version__

API = "https://api.github.com"
DEFAULT_REPOSITORY = "matthiaskoenig/pkdb_data"
REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
PER_PAGE = 100
MAX_PAGES = 1000
MAX_WAITS = 5
# GitHub asks for at least one second between mutating requests.
WRITE_INTERVAL = 1.0


class GitHubError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    state: str
    state_reason: str | None
    labels: tuple[str, ...]
    assignees: tuple[str, ...]

    @classmethod
    def from_api(cls, data: dict) -> "Issue":
        return cls(
            number=data["number"],
            title=data["title"],
            state=data["state"],
            state_reason=data.get("state_reason"),
            labels=tuple(label["name"] for label in data.get("labels", [])),
            assignees=tuple(user["login"] for user in data.get("assignees", [])),
        )


def repository_from(value: str | None = None, environ: Mapping[str, str] = os.environ) -> str:
    repository = value or environ.get("PKDB_ISSUES_REPO") or DEFAULT_REPOSITORY
    if not REPOSITORY.fullmatch(repository):
        raise ValueError("GitHub repository must be owner/name")
    return repository


def token_from(environ: Mapping[str, str] = os.environ) -> str | None:
    return environ.get("GH_TOKEN") or environ.get("GITHUB_TOKEN") or None


class GitHub:
    def __init__(
        self,
        repository: str,
        token: str | None = None,
        *,
        transport=None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
        write_interval: float = WRITE_INTERVAL,
        max_wait: float | None = None,
    ):
        self.repository = repository_from(repository, environ={})
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": f"pkdb/{__version__}",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx2.Client(headers=headers, timeout=30, transport=transport)
        self._sleep = sleep
        self._clock = clock
        self._write_interval = write_interval
        self._max_wait = max_wait
        self._last_write: float | None = None

    def __enter__(self) -> "GitHub":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def pages(self, resource: str, params: Mapping[str, str | int] | None = None) -> list[dict]:
        items: list[dict] = []
        for page in range(1, MAX_PAGES + 1):
            response = self._send(
                "GET",
                f"/repos/{self.repository}/{resource}",
                params={**(params or {}), "per_page": PER_PAGE, "page": page},
            )
            values = response.json()
            if not isinstance(values, list):
                raise GitHubError(f"GitHub answered {resource} with no list")
            items.extend(values)
            if len(values) < PER_PAGE:
                return items
        raise GitHubError(f"GitHub lists more than {MAX_PAGES} pages of {resource}")

    def issues(self) -> list[Issue]:
        return [
            Issue.from_api(item)
            for item in self.pages("issues", {"state": "all"})
            if "pull_request" not in item
        ]

    def assignable(self) -> set[str]:
        return {user["login"] for user in self.pages("assignees") if user.get("type") != "Bot"}

    def labels(self) -> list[str]:
        return [label["name"] for label in self.pages("labels")]

    def create_label(self, name: str, color: str) -> None:
        self._write("POST", f"/repos/{self.repository}/labels", {"name": name, "color": color})

    def create_issue(self, title: str, *, labels: list[str], assignees: list[str]) -> Issue:
        body = {"title": title, "labels": labels, "assignees": assignees}
        return Issue.from_api(self._write("POST", f"/repos/{self.repository}/issues", body).json())

    def update_issue(self, number: int, *, title=None, labels=None, assignees=None, state=None, state_reason=None) -> Issue:
        fields = {"title": title, "labels": labels, "assignees": assignees, "state": state, "state_reason": state_reason}
        body = {key: value for key, value in fields.items() if value is not None}
        return Issue.from_api(self._write("PATCH", f"/repos/{self.repository}/issues/{number}", body).json())

    def comment(self, number: int, body: str) -> None:
        self._write("POST", f"/repos/{self.repository}/issues/{number}/comments", {"body": body})

    def _write(self, method: str, path: str, body: dict) -> httpx2.Response:
        if self._last_write is not None:
            delay = self._last_write + self._write_interval - self._clock()
            if delay > 0:
                self._sleep(delay)
        try:
            return self._send(method, path, json=body)
        finally:
            self._last_write = self._clock()

    def _send(self, method: str, path: str, **kwargs) -> httpx2.Response:
        waits = 0
        while True:
            try:
                response = self._client.request(method, API + path, **kwargs)
            except httpx2.RequestError as error:
                raise GitHubError(f"GitHub cannot be reached: {type(error).__name__}") from None
            wait = self._wait(response)
            if wait is None:
                break
            if waits == MAX_WAITS or (self._max_wait is not None and wait > self._max_wait):
                raise GitHubError(
                    f"GitHub limits the requests; try again in {round(wait)} seconds",
                    status_code=response.status_code,
                )
            waits += 1
            self._sleep(wait)
        if response.is_error:
            raise GitHubError(
                f"GitHub answered {response.status_code} for {method} {path}: {_message(response)}",
                status_code=response.status_code,
            )
        return response

    def _wait(self, response: httpx2.Response) -> float | None:
        if response.status_code not in (403, 429):
            return None
        if (after := response.headers.get("retry-after")) is not None:
            return max(float(after), 1.0)
        if response.headers.get("x-ratelimit-remaining") == "0":
            reset = float(response.headers.get("x-ratelimit-reset", "0"))
            return max(reset - self._clock(), 0.0) + 1.0
        return None


def _message(response: httpx2.Response) -> str:
    try:
        message = response.json().get("message")
    except ValueError, AttributeError:
        message = None
    return message if isinstance(message, str) and message else response.reason_phrase
```

Wrap the long lines with `ruff format`. If `ty` rejects the untyped keyword parameters of `update_issue`, annotate them as in the Interfaces block.

- [ ] **Step 4: Run** `uv run --locked pytest -q tests/issues/test_github.py` -> PASS; full suite, ruff, ty.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/issues python/tests/issues
git commit -m "Add a GitHub client for issues with paging, writes and rate-limit waits"
```

---

### Task 5: The curation app reads GitHub through the new client

**Files:**
- Modify: `python/src/pkdb/curation/github.py` (`GitHubAssignments.refresh`), `python/src/pkdb/curation/engine.py:89`, `python/src/pkdb/curation/connection.py:142`, `python/src/pkdb/curation/jobs.py:767`, `python/tests/test_curation_github.py`, `docs/local-curation.md` (where `GH_TOKEN` is mentioned; search for it)

**Interfaces:**
- Consumes: Task 4 `GitHub`, `GitHubError`, `token_from`.
- Produces: unchanged `GitHubAssignments` behavior and data shape (`users`, `issues`, `limited`, `status`, `refreshed_at`, `error`); the token now also comes from `GITHUB_TOKEN`.

- [ ] **Step 1: Write the failing test** in `python/tests/test_curation_github.py`:

```python
def test_a_rate_limit_is_unavailable_at_once_without_waiting():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx2.Response(403, headers={"retry-after": "60"}, json={"message": "limit"})

    provider = GitHubAssignments("owner/data", transport=httpx2.MockTransport(handler))
    assert provider.refresh()["status"] == "unavailable"
    assert len(calls) == 1
```

- [ ] **Step 2: Run** `uv run --locked pytest -q tests/test_curation_github.py` -> the new test FAILS (today a 403 on `assignees` is `limited`, then `issues` is read; with the shared client a rate limit must stop the refresh).

- [ ] **Step 3: Implement**: `refresh` opens `GitHub(self.repository, self.token, transport=self.transport, write_interval=0, max_wait=0)` and replaces its own `pages` with `github.pages("assignees")` and `github.pages("issues", {"state": "all"})`. A `GitHubError` with `status_code` 403 or 404 on `assignees` that is not a rate limit keeps setting `limited`; tell a rate limit apart by the error raised from the wait path (give `GitHubError` an attribute `rate_limited: bool = False`, set it there, and extend Task 4's tests with one assertion). Catch `GitHubError, ValueError, KeyError, TypeError` where `httpx2.HTTPError` was caught. Keep the data shape byte for byte; the three existing tests must pass unchanged. Replace `os.environ.get("GH_TOKEN")` by `token_from()` in `engine.py`, `connection.py` and the redaction in `jobs.py` (redact both variables). `docs/local-curation.md`: name `GH_TOKEN` or `GITHUB_TOKEN` where `GH_TOKEN` is named.

- [ ] **Step 4: Run** `uv run --locked pytest -q tests/test_curation_github.py tests/test_curation_engine.py tests/issues` -> PASS; full suite, ruff, ty, docs build.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/curation python/src/pkdb/issues/github.py python/tests/test_curation_github.py python/tests/issues/test_github.py docs/local-curation.md
git commit -m "Read GitHub issues of the curation app through the shared GitHub client"
```

---

### Task 6: Desired issue state and the sync plan

**Files:**
- Create: `python/src/pkdb/issues/state.py`, `python/tests/issues/test_state.py`, `python/tests/issues/fixtures.py`

**Interfaces:**
- Consumes: Task 3 `study_folders`, `location`, `substances`; Task 4 `Issue`; Task 1 `Curator`; `pkdb.studyformat.validation.is_v2_folder`; `pkdb.studyformat.metadata.read_metadata` (-> `.metadata`, `.revision`; raises `MetadataError`); `pkdb.studyformat.review_edit.read_review` (-> `.review`, `.revision`; raises `ReviewError`).
- Produces (all in `pkdb.issues.state`):
  - `WORKFLOW = {"draft": "curate", "in_review": "check", "approved": "approved"}`, `LABEL_COLORS = {"curate": "fbca04", "check": "1d76db", "approved": "0e8a16"}`, `SUBSTANCE_COLOR = "c5def5"`, `MAX_ASSIGNEES = 10`.
  - `StudyState` (frozen dataclass): `location: str`, `folder: Path`, `issue: int | None`, `status: str`, `released: bool`, `users: tuple[str, ...]` (curators, then reviewers, without repeats), `metadata_revision: str`, `review_revision: str`.
  - `Studies` (frozen dataclass): `states: list[StudyState]`, `errors: list[str]`, `format_1: int`.
  - `read_studies(root: Path) -> Studies`: every format 2 study; a study whose `study.json` or `review.json` cannot be read is an error `"<location>: <message>"`; format 1 folders are counted.
  - `Roster` (frozen dataclass): `logins: dict[str, str | None]` (username to login), `assignable: frozenset[str]`; `Roster.of(curators: list[Curator], assignable: set[str]) -> Roster`.
  - `IssueChange` (Pydantic, `extra="forbid"`): `study: str`, `number: int`, `title: str | None = None`, `labels: list[str] | None = None` (the complete new list), `add_labels: list[str] = []`, `remove_labels: list[str] = []`, `assignees: list[str] | None = None`, `state: Literal["open", "closed"] | None = None`, `state_reason: str | None = None`.
  - `SyncPlan` (Pydantic, `extra="forbid"`): `changes: list[IssueChange] = []`, `labels: list[str] = []` (labels to create), `warnings: list[str] = []`, `errors: list[str] = []`.
  - `desired_assignees(state: StudyState, roster: Roster, problems: Problems) -> list[str]`.
  - `plan(states: list[StudyState], issues: list[Issue], roster: Roster, *, substance_names: list[str], label_names: list[str], repository: str) -> SyncPlan`.

Rules of `plan`:
- Studies are grouped by `issue`. A number named by two or more studies is one error `"Issue #N is named by several studies: a, b"`, and those studies get no change. A study without `issue` is a warning `"<location> has no issue; pkdb issues sync --adopt gives it one"`. A number that is not an issue of the repository (missing, or a pull request) is an error `"<location> names issue #N, which is not an issue of <repository>"`.
- Desired state: title `<location>`; labels: every current label that is neither a workflow label nor named like a substance folder (case-insensitive), plus the substance of the study and `WORKFLOW[status]`; assignees from `desired_assignees`; closed with reason `completed` when `released and status == "approved"`, else open.
- A change lists only what differs: `title` when it differs; `labels` (complete list: the kept labels in their current order and spelling, then the substance label, then the workflow label) with `add_labels` (in that order) and `remove_labels` (in the issue's current order) when the label set differs case-insensitively; `assignees` (sorted, case-insensitive) when the set differs; `state="closed", state_reason="completed"` when the issue is open or closed with another reason and must be closed; `state="open", state_reason="reopened"` when it is closed and must be open. A study whose issue is already right gets no change.
- `desired_assignees`: for each user of the study: not in the roster -> problem `"User <u> is not in the PK-DB roster"`; no login -> `"User <u> has no GitHub login in the PK-DB roster"`; login not assignable -> `"GitHub user <login> cannot be assigned in <repository>"`; the first `MAX_ASSIGNEES` assignable logins in study order are kept, more -> `"<location> has <n> assignees; GitHub assigns at most 10"`. `Problems` collects each user message once with the number of studies, rendered as `"<message> (<n> studies)"`, and appends them to `warnings` sorted.
- Labels to create: the workflow and substance labels the plan uses that are not in `label_names` (case-insensitive), sorted.

- [ ] **Step 1: Write the fixtures and failing tests**

`python/tests/issues/fixtures.py`:

```python
"""Format 2 study folders and GitHub issues for the issue sync tests."""

from pathlib import Path

from pkdb.issues.github import Issue
from pkdb.studyformat.jsonio import dump_json


def study(root: Path, location: str, *, issue=None, status="draft", curators=("ana",), reviewers=(), release=None) -> Path:
    folder = root / "studies" / location
    folder.mkdir(parents=True)
    metadata = {
        "format": 2,
        "reference": {"pmid": "123"},
        "creator": curators[0] if curators else "ana",
        "curators": [{"user": user, "rating": 3} for user in curators],
        "licence": "open",
        "access": "private",
    }
    if issue is not None:
        metadata["issue"] = issue
    if release is not None:
        metadata["release"] = release
    (folder / "study.json").write_text(dump_json(metadata), encoding="utf-8")
    review = {"status": status, "reviewers": list(reviewers)}
    if status == "approved":
        review |= {"approved_by": reviewers[0], "approved": "2026-10-01T00:00:00Z"}
    (folder / "review.json").write_text(dump_json(review), encoding="utf-8")
    return folder


def issue(number, title, *, state="open", reason=None, labels=(), assignees=()) -> Issue:
    return Issue(number, title, state, reason, tuple(labels), tuple(assignees))
```

If `read_metadata` or `read_review` refuse these minimal files (check `StudyMetadata` and `Review` required fields), add the fields they require and keep the parameters.

`python/tests/issues/test_state.py`:

```python
from fixtures import issue, study

from pkdb.issues.state import Roster, plan, read_studies
from pkdb.schemas.curators import Curator

REPOSITORY = "owner/data"
ROSTER = Roster.of(
    [Curator(username="ana", name="Ana", github="ana-gh"), Curator(username="bo", name="Bo", github="bo-gh")],
    {"ana-gh", "bo-gh"},
)


def run(root, issues, roster=ROSTER, labels=("curate", "check", "approved", "caffeine")):
    studies = read_studies(root)
    return plan(
        studies.states,
        issues,
        roster,
        substance_names=["caffeine", "codeine"],
        label_names=list(labels),
        repository=REPOSITORY,
    )


def test_a_matching_issue_needs_no_change(tmp_path):
    study(tmp_path, "caffeine/A", issue=1)
    result = run(tmp_path, [issue(1, "caffeine/A", labels=["caffeine", "curate"], assignees=["ana-gh"])])
    assert result.changes == [] and result.errors == [] and result.warnings == []


def test_title_labels_assignees_and_state_are_aligned(tmp_path):
    study(tmp_path, "caffeine/A", issue=1, status="approved", reviewers=["bo"], release={"pkdb_id": "PKDB00001", "date": "2026-10-01"})
    current = issue(1, "Curate caffeine/A", labels=["curate", "Codeine", "help wanted"], assignees=["zed"])
    [change] = run(tmp_path, [current]).changes
    assert change.title == "caffeine/A"
    assert change.labels == ["help wanted", "caffeine", "approved"]
    assert change.add_labels == ["caffeine", "approved"] and change.remove_labels == ["curate", "Codeine"]
    assert change.assignees == ["ana-gh", "bo-gh"]
    assert (change.state, change.state_reason) == ("closed", "completed")


def test_a_closed_issue_of_an_unreleased_study_is_reopened(tmp_path):
    study(tmp_path, "caffeine/A", issue=1, status="in_review")
    [change] = run(tmp_path, [issue(1, "caffeine/A", state="closed", reason="completed", labels=["caffeine", "check"], assignees=["ana-gh"])]).changes
    assert (change.state, change.state_reason) == ("open", "reopened")


def test_two_studies_with_one_issue_are_errors_and_untouched(tmp_path):
    study(tmp_path, "caffeine/A", issue=1)
    study(tmp_path, "caffeine/B", issue=1)
    study(tmp_path, "caffeine/C", issue=2)
    result = run(tmp_path, [issue(1, "x"), issue(2, "x")])
    assert result.errors == ["Issue #1 is named by several studies: caffeine/A, caffeine/B"]
    assert [change.study for change in result.changes] == ["caffeine/C"]


def test_missing_issues_and_studies_without_issue(tmp_path):
    study(tmp_path, "caffeine/A", issue=9)
    study(tmp_path, "caffeine/B")
    result = run(tmp_path, [])
    assert result.errors == ["caffeine/A names issue #9, which is not an issue of owner/data"]
    assert result.warnings == ["caffeine/B has no issue; pkdb issues sync --adopt gives it one"]


def test_unassignable_users_are_warnings(tmp_path):
    users = ("ana", "bo", "cy", "dee", *(f"u{i}" for i in range(10)))
    study(tmp_path, "caffeine/A", issue=1, curators=users)
    curators = [Curator(username="ana", name="Ana", github="ana-gh"), Curator(username="bo", name="Bo", github="bo-gh"), Curator(username="cy", name="Cy")]
    curators += [Curator(username=f"u{i}", name=f"U{i}", github=f"u{i}-gh") for i in range(10)]
    roster = Roster.of(curators, {"ana-gh", *(f"u{i}-gh" for i in range(10))})
    [change] = run(tmp_path, [issue(1, "caffeine/A", labels=["caffeine", "curate"])], roster).changes
    assert len(change.assignees) == 10 and "ana-gh" in change.assignees
    assert sorted(run(tmp_path, [issue(1, "caffeine/A")], roster).warnings) == [
        "GitHub user bo-gh cannot be assigned in owner/data (1 studies)",
        "User cy has no GitHub login in the PK-DB roster (1 studies)",
        "User dee is not in the PK-DB roster (1 studies)",
        "caffeine/A has 11 assignees; GitHub assigns at most 10",
    ]


def test_missing_labels_are_created(tmp_path):
    study(tmp_path, "codeine/A", issue=1, status="in_review")
    result = run(tmp_path, [issue(1, "codeine/A")], labels=["CHECK"])
    assert result.labels == ["codeine"]


def test_unreadable_studies_are_errors_and_format_1_is_counted(tmp_path):
    folder = study(tmp_path, "caffeine/A", issue=1)
    (folder / "review.json").write_text("{", encoding="utf-8")
    v1 = tmp_path / "studies" / "caffeine" / "Old"
    v1.mkdir()
    (v1 / "study.json").write_text('{"sid": "1", "name": "Old"}', encoding="utf-8")
    studies = read_studies(tmp_path)
    assert studies.states == [] and studies.format_1 == 1
    assert studies.errors[0].startswith("caffeine/A: ")
```

The message "(1 studies)" is deliberate plain text of the counter; if the implementer prefers "1 study", change the rendering and the test together.

- [ ] **Step 2: Run to verify they fail**: `uv run --locked pytest -q tests/issues/test_state.py` -> FAIL, module not found.

- [ ] **Step 3: Implement** `python/src/pkdb/issues/state.py` with the rules above: `read_studies` loops over `study_folders(root)`, skips folders without `study.json`, counts `not is_v2_folder(folder)` as format 1, reads both documents, and builds `StudyState` (users: `[c.user for c in metadata.curators] + review.reviewers`, first occurrence wins). `plan` follows the rule list; keep it as a few small functions (`_duplicates`, `_labels`, `_assignees`, `_state`), each with a docstring.

- [ ] **Step 4: Run** `uv run --locked pytest -q tests/issues` -> PASS; full suite, ruff, ty.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/issues/state.py python/tests/issues/test_state.py python/tests/issues/fixtures.py
git commit -m "Plan the title, labels, assignees and state of the GitHub issue of each study"
```

---

### Task 7: Adoption matching

**Files:**
- Create: `python/src/pkdb/issues/adopt.py`, `python/tests/issues/test_adopt.py`

**Interfaces:**
- Consumes: Task 4 `Issue`; Task 6 `StudyState`.
- Produces (all in `pkdb.issues.adopt`):
  - `PREFIXES = ("Curate ", "Check ", "Check and curate ")`, `DUPLICATE = "Duplicate of #{number}"`.
  - `Adoption` (frozen dataclass): `study: StudyState`, `keep: Issue | None` (None: create a new issue), `duplicates: tuple[Issue, ...]`.
  - `match(states: list[StudyState], issues: list[Issue]) -> list[Adoption]`: one adoption per study without `issue`, in the order of `states`.

Rules: an issue is a candidate of a study when its title is the location exactly or a prefix of `PREFIXES` followed by the location, and no study names its number in `issue`. Among the candidates the kept issue is the first by (exact title before prefixed, open before closed, lower number); the others are duplicates. An issue is a candidate of at most one study (its title fixes the location).

- [ ] **Step 1: Write the failing tests** `python/tests/issues/test_adopt.py`:

```python
from pathlib import Path

from fixtures import issue

from pkdb.issues.adopt import match
from pkdb.issues.state import StudyState


def state(location, number=None):
    return StudyState(location, Path(location), number, "draft", False, ("ana",), "r1", "r2")


def test_the_exact_open_lowest_issue_is_kept():
    issues = [
        issue(5, "Curate caffeine/A"),
        issue(7, "caffeine/A", state="closed", reason="completed"),
        issue(9, "caffeine/A"),
        issue(3, "Check and curate caffeine/A"),
        issue(4, "Check caffeine/AB"),
    ]
    [adoption] = match([state("caffeine/A")], issues)
    assert adoption.keep.number == 9
    assert [i.number for i in adoption.duplicates] == [7, 3, 5]


def test_issues_named_by_a_study_are_never_adopted():
    issues = [issue(1, "caffeine/A"), issue(2, "Curate caffeine/A")]
    [adoption] = match([state("caffeine/A"), state("caffeine/B", number=1)], issues)
    assert adoption.keep.number == 2 and adoption.duplicates == ()


def test_a_study_without_candidates_gets_a_new_issue():
    [adoption] = match([state("caffeine/A")], [issue(1, "caffeine/AB"), issue(2, "Curate: caffeine/A")])
    assert adoption.keep is None and adoption.duplicates == ()
```

Order of duplicates: the same sort key as the kept issue (exact, open, number): `7` (exact, closed) before `3` and `5` (prefixed, open, by number).

- [ ] **Step 2: Run to verify they fail**: `uv run --locked pytest -q tests/issues/test_adopt.py` -> FAIL.

- [ ] **Step 3: Implement** `python/src/pkdb/issues/adopt.py`:

```python
"""Match studies without an issue to existing GitHub issues by title."""

from dataclasses import dataclass

from pkdb.issues.github import Issue
from pkdb.issues.state import StudyState

PREFIXES = ("Curate ", "Check ", "Check and curate ")
DUPLICATE = "Duplicate of #{number}"


@dataclass(frozen=True)
class Adoption:
    study: StudyState
    keep: Issue | None
    duplicates: tuple[Issue, ...]


def _exact(title: str, location: str) -> bool | None:
    """True for the canonical title, False for a known prefix, None otherwise."""
    if title == location:
        return True
    if any(title == prefix + location for prefix in PREFIXES):
        return False
    return None


def match(states: list[StudyState], issues: list[Issue]) -> list[Adoption]:
    claimed = {state.issue for state in states if state.issue is not None}
    adoptions = []
    for state in states:
        if state.issue is not None:
            continue
        candidates = []
        for issue in issues:
            exact = _exact(issue.title, state.location)
            if exact is not None and issue.number not in claimed:
                candidates.append((not exact, issue.state != "open", issue.number, issue))
        candidates.sort(key=lambda candidate: candidate[:3])
        found = [candidate[3] for candidate in candidates]
        adoptions.append(Adoption(state, found[0] if found else None, tuple(found[1:])))
    return adoptions
```

- [ ] **Step 4: Run** `uv run --locked pytest -q tests/issues` -> PASS; ruff, ty.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/issues/adopt.py python/tests/issues/test_adopt.py
git commit -m "Match studies without an issue to existing issues by their title"
```

---

### Task 8: Apply adoptions and the plan

**Files:**
- Create: `python/src/pkdb/issues/sync.py`, `python/tests/issues/test_sync.py`, `python/tests/issues/fake_github.py`

**Interfaces:**
- Consumes: Tasks 3, 4, 6, 7; `pkdb.studyformat.metadata.patch_metadata(folder, patch, revision)`; `pkdb.studyformat.review_edit.set_status(folder, author, status, *, vocabulary, revision)`; `pkdb.studyformat.revision.RevisionConflict`; `pkdb.identity.Author`.
- Produces (all in `pkdb.issues.sync`):
  - `AdoptionResult` (Pydantic): `study: str`, `number: int | None`, `created: bool = False`, `renamed: bool = False`, `duplicates: list[int] = []`, `in_review: bool = False`.
  - `SyncResult` (Pydantic): `repository: str`, `dry_run: bool`, `adopted: list[AdoptionResult] = []`, `plan: SyncPlan`, `applied: int = 0`, `warnings: list[str] = []`, `errors: list[str] = []`, `format_1: int = 0`; property `ok` (no errors).
  - `sync(root: Path, github: GitHub, roster: list[Curator], *, adopt: bool = False, author: Author | None = None, dry_run: bool = False) -> SyncResult`.

Behavior of `sync`:
1. `studies = read_studies(root)`; `issues = github.issues()`; `roster = Roster.of(curators, github.assignable())`; errors of `studies` go to the result.
2. When `adopt` (requires `author`, else `ValueError`): `match(...)`. For each adoption, unless `dry_run`:
   - With a kept issue: rename it to the location when the title differs. Without one: create an issue with the location as title, the study's substance and workflow labels and its desired assignees (`desired_assignees`); create missing labels first.
   - For each duplicate that is not closed with reason `not_planned`: comment `Duplicate of #N` (N the kept or created number), then close it with `state_reason="not_planned"`.
   - Write the number: `patch_metadata(study.folder, {"issue": number}, study.metadata_revision)`. A `RevisionConflict` or `MetadataError` is an error `"<location>: study.json changed on disk; run the sync again"` (or the error message), and the study is left out of the plan.
   - When the study is not released, its status is `draft`, and the kept issue has the label `check` (case-insensitive): `set_status(study.folder, author, "in_review", vocabulary=None, revision=study.review_revision)`; a `RevisionConflict` or `ReviewError` is an error of the study.
   - Replace the study's state by its new number and status, and add the adopted or created issue to `issues`, so that step 3 plans the remaining changes (labels, assignees, state) of adopted issues as well.
   With `dry_run`, record what would happen (`number` of the kept issue or None, `created`, `renamed`, `duplicates`, `in_review`) and write nothing.
3. `result.plan = plan(...)` with `substance_names=substances(root)` and `label_names=github.labels()`.
4. Unless `dry_run`: create the plan's labels (`LABEL_COLORS` or `SUBSTANCE_COLOR`), then apply each change with `update_issue(number, title=..., labels=..., assignees=..., state=..., state_reason=...)` and count `applied`. A `GitHubError` with status 401 or 403 is raised (it stops the run: token or permission); any other `GitHubError` is an error `"<location>: <message>"` and the run goes on.
5. `result.warnings` and `result.errors` collect the plan's and the run's messages.

The order in step 2 (GitHub first, then `study.json`) is what makes an interrupted adoption safe: the rerun finds the renamed or created issue by its exact title.

- [ ] **Step 1: Write a fake GitHub API and the failing tests**

`python/tests/issues/fake_github.py`: a small in-memory GitHub served through `httpx2.MockTransport`, so `sync` runs against the real client:

```python
"""An in-memory GitHub repository behind httpx2.MockTransport for the sync tests."""

import json
import re

import httpx2

from pkdb.issues.github import GitHub


class FakeGitHub:
    def __init__(self, issues=(), labels=(), assignable=()):
        self.issues = {i["number"]: {"state_reason": None, "labels": [], "assignees": [], "state": "open", **i} for i in issues}
        self.labels = list(labels)
        self.assignable = list(assignable)
        self.comments = []
        self.writes = []
        self.fail = {}  # (method, number) -> status

    def handler(self, request):
        path = request.url.path.removeprefix("/repos/owner/data")
        body = json.loads(request.content) if request.content else None
        if request.method != "GET":
            self.writes.append((request.method, path, body))
        number = int(match[1]) if (match := re.fullmatch(r"/issues/(\d+)(?:/comments)?", path)) else None
        if (status := self.fail.get((request.method, number))) is not None:
            return httpx2.Response(status, json={"message": "refused"})
        page = int(request.url.params.get("page", "1"))
        if request.method == "GET":
            items = {
                "/issues": [self._api(i) for i in self.issues.values()],
                "/labels": [{"name": name} for name in self.labels],
                "/assignees": [{"login": login, "type": "User"} for login in self.assignable],
            }[path]
            return httpx2.Response(200, json=items[(page - 1) * 100 : page * 100])
        if path == "/labels":
            self.labels.append(body["name"])
            return httpx2.Response(201, json=body)
        if path == "/issues":
            number = max(self.issues, default=0) + 1
            self.issues[number] = {"number": number, "state": "open", "state_reason": None, **body}
            return httpx2.Response(201, json=self._api(self.issues[number]))
        if path.endswith("/comments"):
            self.comments.append((number, body["body"]))
            return httpx2.Response(201, json={})
        self.issues[number].update(body)
        return httpx2.Response(200, json=self._api(self.issues[number]))

    @staticmethod
    def _api(issue):
        return {
            **issue,
            "labels": [{"name": name} for name in issue["labels"]],
            "assignees": [{"login": login} for login in issue["assignees"]],
        }

    def client(self):
        return GitHub("owner/data", "token", transport=httpx2.MockTransport(self.handler), write_interval=0)
```

`python/tests/issues/test_sync.py`:

```python
import json

import pytest
from fake_github import FakeGitHub
from fixtures import study

from pkdb.identity import Author
from pkdb.issues.sync import sync
from pkdb.schemas.curators import Curator
from pkdb.studyformat.metadata import read_metadata
from pkdb.studyformat.review_edit import read_review

ROSTER = [Curator(username="ana", name="Ana", github="ana-gh")]
AUTHOR = Author("mkoenig")


def number_of(folder):
    return read_metadata(folder).metadata.issue


def test_sync_aligns_issues(tmp_path):
    study(tmp_path, "caffeine/A", issue=1, status="in_review")
    github = FakeGitHub(issues=[{"number": 1, "title": "Check caffeine/A", "labels": ["curate"]}], assignable=["ana-gh"])
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER)
    assert result.ok and result.applied == 1
    assert github.issues[1]["title"] == "caffeine/A"
    assert sorted(github.issues[1]["labels"]) == ["caffeine", "check"]
    assert github.issues[1]["assignees"] == ["ana-gh"]
    assert sorted(github.labels) == ["caffeine", "check"]


def test_a_dry_run_changes_nothing(tmp_path):
    study(tmp_path, "caffeine/A", issue=1)
    github = FakeGitHub(issues=[{"number": 1, "title": "x"}])
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER, dry_run=True)
    assert result.plan.changes and github.writes == []


def test_sync_exits_with_errors_and_changes_the_rest(tmp_path):
    study(tmp_path, "caffeine/A", issue=1)
    study(tmp_path, "caffeine/B", issue=1)
    study(tmp_path, "caffeine/C", issue=2)
    github = FakeGitHub(issues=[{"number": 1, "title": "x"}, {"number": 2, "title": "y"}], assignable=["ana-gh"])
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER)
    assert not result.ok and result.applied == 1
    assert github.issues[1]["title"] == "x" and github.issues[2]["title"] == "caffeine/C"


def test_adoption_renames_closes_duplicates_and_records_the_number(tmp_path):
    folder = study(tmp_path, "caffeine/A")
    github = FakeGitHub(
        issues=[
            {"number": 4, "title": "Check caffeine/A", "labels": ["check"]},
            {"number": 6, "title": "Curate caffeine/A"},
        ],
        assignable=["ana-gh"],
    )
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert result.ok
    assert number_of(folder) == 4
    assert read_review(folder).review.status == "in_review"
    assert github.issues[4]["title"] == "caffeine/A" and "check" in github.issues[4]["labels"]
    assert (github.issues[6]["state"], github.issues[6]["state_reason"]) == ("closed", "not_planned")
    assert github.comments == [(6, "Duplicate of #4")]


def test_adoption_creates_an_issue_without_a_match(tmp_path):
    folder = study(tmp_path, "caffeine/A")
    github = FakeGitHub(assignable=["ana-gh"])
    with github.client() as client:
        sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert number_of(folder) == 1
    assert github.issues[1]["title"] == "caffeine/A"
    assert sorted(github.issues[1]["labels"]) == ["caffeine", "curate"]


def test_an_interrupted_adoption_is_finished_by_the_rerun(tmp_path, monkeypatch):
    folder = study(tmp_path, "caffeine/A")
    github = FakeGitHub(issues=[{"number": 4, "title": "Curate caffeine/A"}], assignable=["ana-gh"])
    from pkdb.issues import sync as module

    original = module.patch_metadata

    def stop(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(module, "patch_metadata", stop)
    with github.client() as client, pytest.raises(KeyboardInterrupt):
        sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert github.issues[4]["title"] == "caffeine/A" and number_of(folder) is None
    monkeypatch.setattr(module, "patch_metadata", original)
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert result.ok and number_of(folder) == 4 and len(github.issues) == 1


def test_a_changed_study_json_is_not_written_over(tmp_path, monkeypatch):
    first = study(tmp_path, "caffeine/A")
    second = study(tmp_path, "caffeine/B")
    github = FakeGitHub(issues=[{"number": 4, "title": "caffeine/A"}, {"number": 5, "title": "caffeine/B"}], assignable=["ana-gh"])
    from pkdb.issues import state as state_module

    original = state_module.read_studies

    def read_then_edit(root):
        studies = original(root)
        text = (first / "study.json").read_text(encoding="utf-8")
        (first / "study.json").write_text(text.replace('"licence": "open"', '"licence": "closed"'), encoding="utf-8")
        return studies

    monkeypatch.setattr("pkdb.issues.sync.read_studies", read_then_edit)
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER, adopt=True, author=AUTHOR)
    assert result.errors == ["caffeine/A: study.json changed on disk; run the sync again"]
    assert '"licence": "closed"' in (first / "study.json").read_text(encoding="utf-8")
    assert number_of(first) is None and number_of(second) == 5


def test_a_forbidden_write_stops_the_run(tmp_path):
    study(tmp_path, "caffeine/A", issue=1)
    study(tmp_path, "caffeine/B", issue=2)
    github = FakeGitHub(issues=[{"number": 1, "title": "x"}, {"number": 2, "title": "y"}], assignable=["ana-gh"])
    github.fail[("PATCH", 1)] = 403
    from pkdb.issues.github import GitHubError

    with github.client() as client, pytest.raises(GitHubError):
        sync(tmp_path, client, ROSTER)
    assert github.issues[2]["title"] == "y"


def test_a_failed_issue_is_an_error_and_the_run_goes_on(tmp_path):
    study(tmp_path, "caffeine/A", issue=1)
    study(tmp_path, "caffeine/B", issue=2)
    github = FakeGitHub(issues=[{"number": 1, "title": "x"}, {"number": 2, "title": "y"}], assignable=["ana-gh"])
    github.fail[("PATCH", 1)] = 422
    with github.client() as client:
        result = sync(tmp_path, client, ROSTER)
    assert result.errors and result.errors[0].startswith("caffeine/A: GitHub answered 422")
    assert github.issues[2]["title"] == "caffeine/B"
```

Check the exact key spelling of `study.json` in `dump_json` output (`"licence": "open"`) before relying on the string replacement; adapt the edit, not the assertion's meaning.

- [ ] **Step 2: Run to verify they fail**: `uv run --locked pytest -q tests/issues/test_sync.py` -> FAIL, module not found.

- [ ] **Step 3: Implement** `python/src/pkdb/issues/sync.py` following the behavior list. Import `patch_metadata`, `read_studies` and `set_status` at module level (the tests patch `pkdb.issues.sync.patch_metadata` and `pkdb.issues.sync.read_studies`). Keep `sync` short by splitting `_adopt(...)`, `_apply(...)` and `_labels(...)`.

- [ ] **Step 4: Run** `uv run --locked pytest -q tests/issues` -> PASS; full suite, ruff, ty.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/issues/sync.py python/tests/issues/test_sync.py python/tests/issues/fake_github.py
git commit -m "Apply issue adoptions and the sync plan to GitHub"
```

---

### Task 9: `pkdb issues sync` and its documentation

**Files:**
- Create: `python/src/pkdb/issues_cli.py`, `python/tests/issues/test_cli.py`
- Modify: `python/src/pkdb/cli.py` (import tuple, `register`, dispatch), `python/tests/test_cli.py` (the help test lists commands; add `issues`), `docs/python-client.md` (environment table line 25, command table near line 198, a new section), release note after the pull request exists

**Interfaces:**
- Consumes: Task 3 `repository_root`; Task 4 `GitHub`, `GitHubError`, `repository_from`, `token_from`; Task 2 `Client.curators`; Task 8 `sync`, `SyncResult`; `pkdb.identity.author_from`, `IdentityError`; `pkdb.errors.ClientError`.
- Produces: `issues_cli.register(commands) -> None`, `issues_cli.run(args) -> int`.

Command:

```
pkdb issues sync [--root PATH] [--repository OWNER/NAME] [--adopt] [--user USER] [--agent AGENT]
                 [--endpoint URL] [--dry-run] [--format human|json]
```

- `--root` defaults to `repository_root(Path.cwd())`; `--repository` to `repository_from(None)`; `--endpoint` to `PKDB_ENDPOINT`.
- The roster comes from `Client(endpoint, api_key).curators()`; without endpoint or `PKDB_API_KEY` the command exits 2: `Set PKDB_ENDPOINT and PKDB_API_KEY: the sync reads GitHub logins from the PK-DB roster`. A `ClientError` exits 1 with its message.
- Without `GH_TOKEN` or `GITHUB_TOKEN` the command exits 2 unless `--dry-run`: `Set GH_TOKEN or GITHUB_TOKEN to change GitHub issues`.
- `--adopt` takes the author from `author_from(args.user, args.agent)` (`--user`, else `PKDB_USER`; `--agent`, else `PKDB_AGENT`); an `IdentityError` exits 2 with its message. The user must be in the roster just read (exit 2: `User <u> is not in the PK-DB roster`); this checks the author without a second server call, unlike `resolve_author`, which would contact the server again.
- Human output: one line per adoption (`caffeine/A: adopt #4, close #6 as duplicate` / `caffeine/B: new issue`), one line per change (`#12 caffeine/A: title, labels +check -curate, assignees ana-gh bo-gh, close`), then the warnings and errors, then `Changed <applied> issues.` or `Dry run: <n> changes.`. JSON: `result.model_dump(mode="json")`.
- Exit 0 when `result.ok`, 1 with errors or a `GitHubError`, 2 for usage errors (`ValueError`, missing settings), 130 on Ctrl-C. Lazy imports inside `run` (the help test checks that `--help` loads no heavy module).

- [ ] **Step 1: Write the failing tests** `python/tests/issues/test_cli.py` with the fake GitHub and a fake PK-DB client:

```python
import json

import pytest
from fake_github import FakeGitHub
from fixtures import study

from pkdb.cli import main
from pkdb.schemas.curators import Curator


@pytest.fixture
def setup(tmp_path, monkeypatch):
    study(tmp_path, "caffeine/A", issue=1)
    github = FakeGitHub(issues=[{"number": 1, "title": "x"}], assignable=["ana-gh"])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PKDB_ENDPOINT", "https://example.test")
    monkeypatch.setenv("PKDB_API_KEY", "pkdb_live_x")
    monkeypatch.setenv("GH_TOKEN", "token")
    monkeypatch.setattr("pkdb.issues_cli.github_client", lambda repository, token: github.client())
    monkeypatch.setattr("pkdb.issues_cli.roster", lambda endpoint, api_key: [Curator(username="ana", name="Ana", github="ana-gh")])
    return github


def test_sync_changes_issues_and_reports_json(setup, capsys):
    assert main(["issues", "sync", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["applied"] == 1 and setup.issues[1]["title"] == "caffeine/A"


def test_a_dry_run_without_token_writes_nothing(setup, monkeypatch, capsys):
    monkeypatch.delenv("GH_TOKEN")
    assert main(["issues", "sync", "--dry-run", "--format", "human"]) == 0
    assert setup.writes == [] and "Dry run: 1 changes." in capsys.readouterr().out


def test_changes_need_a_token(setup, monkeypatch, capsys):
    monkeypatch.delenv("GH_TOKEN")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert main(["issues", "sync", "--format", "human"]) == 2
    assert "GH_TOKEN" in capsys.readouterr().err


def test_the_roster_needs_the_server(setup, monkeypatch, capsys):
    monkeypatch.delenv("PKDB_API_KEY")
    assert main(["issues", "sync", "--format", "human"]) == 2
    assert "PKDB_API_KEY" in capsys.readouterr().err


def test_adoption_needs_a_user_of_the_roster(setup, monkeypatch, capsys):
    monkeypatch.delenv("PKDB_USER", raising=False)
    assert main(["issues", "sync", "--adopt", "--format", "human"]) == 2
    assert main(["issues", "sync", "--adopt", "--user", "zed", "--format", "human"]) == 2
    assert "not in the PK-DB roster" in capsys.readouterr().err
    assert setup.writes == []


def test_adoption_writes_the_issue_number(setup, tmp_path):
    folder = study(tmp_path, "caffeine/B")
    setup.issues[2] = {"number": 2, "title": "Curate caffeine/B", "state": "open", "state_reason": None, "labels": [], "assignees": []}
    assert main(["issues", "sync", "--adopt", "--user", "ana", "--format", "json"]) == 0
    assert '"issue": 2' in (folder / "study.json").read_text(encoding="utf-8")
```

`issues_cli` exposes two module-level factories that the tests replace: `github_client(repository: str, token: str | None) -> GitHub` and `roster(endpoint: str, api_key: str) -> list[Curator]`. Check the exact `"issue": 2` spelling of `dump_json` output and adapt the string, not the meaning.

- [ ] **Step 2: Run to verify they fail**: `uv run --locked pytest -q tests/issues/test_cli.py` -> FAIL.

- [ ] **Step 3: Implement** `issues_cli.py` with `register` (subcommand `issues` with action `sync`) and `run`, following `migration_cli.py` for exit codes and lazy imports; register it in `cli.py` (`issues_cli.register(commands)`; `if args.command == "issues": return issues_cli.run(args)`); add `issues` to the command list of the help test in `tests/test_cli.py`.

Docs in `docs/python-client.md`:
- Environment table rows: `GH_TOKEN`, `GITHUB_TOKEN` (`GitHub token for pkdb issues sync and the curation app; GH_TOKEN wins`) and `PKDB_ISSUES_REPO` (`GitHub repository of the study issues, default matthiaskoenig/pkdb_data`).
- Command table row: `| pkdb issues sync [--adopt] [--dry-run] | Align the GitHub issue of every study: title, labels, assignees, open or closed |`.
- A new section `## GitHub issues of studies` (after the study format 2 commands): what the sync aligns (title, the substance label and one workflow label `curate`, `check` or `approved`, the curators and reviewers as assignees through the PK-DB roster, closed as completed once released and approved); that other labels stay and issues without a study are left alone; that it needs `GH_TOKEN` or `GITHUB_TOKEN`, `PKDB_ENDPOINT` and `PKDB_API_KEY`; that `--dry-run` only shows the plan; that `--adopt --user <user>` gives studies without `issue` an issue (matching titles with `Curate `, `Check ` or `Check and curate `, closing duplicates as not planned with "Duplicate of #N", moving a draft study whose issue has the `check` label to `in_review`, or creating a new issue) and is the only mode that writes `study.json` and `review.json`; that users without a GitHub login, users GitHub cannot assign and assignees beyond 10 are warnings; exit codes 0, 1 and 2. Build the docs.

- [ ] **Step 4: Run** `uv run --locked pytest -q tests/issues tests/test_cli.py` -> PASS; full suite, ruff, ty, docs build.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/issues_cli.py python/src/pkdb/cli.py python/tests/issues/test_cli.py python/tests/test_cli.py docs/python-client.md
git commit -m "Add pkdb issues sync with adoption of existing issues"
```

- [ ] **Step 6: Release note after the pull request exists**

Add to the top of `release-notes/unreleased.md` (with the pull request number):

```markdown
- Keep one GitHub issue per study format 2 study with `pkdb issues sync` (#N): it aligns the title `<substance>/<name>`, the substance label and one workflow label (`curate`, `check`, `approved`), the curators and reviewers as assignees and the open or closed state, and `--adopt --user <user>` gives studies without an issue their existing issue by title, closes duplicates, or creates one. The server lists administrators, curators and reviewers with their GitHub logins at `GET /api/v2/curators`, read by `Client.curators()`, and the curation app reads GitHub through the same client, now also with `GITHUB_TOKEN`.
```

Commit it as "Add the release note of pkdb issues sync" and push.

---

## Self-Review

- **Spec coverage (section 5):** client with paging, create, update, comment, labels, token and repository from the environment, rate-limit waits, writes one after another (Task 4); curation lookup moved (Task 5); roster route with hidden logins and docs, `Client.curators()` (Tasks 1, 2); desired state, labels kept, matching by number, missing issue warning, duplicate number error, issues without study left alone (Task 6); `--dry-run`, `--json` as `--format json`, never writes files without `--adopt` (Tasks 8, 9); adoption by exact title and prefixes, keep order, rename, close duplicates with comment, number in `study.json`, `check` to `in_review`, new issue without match (Tasks 7, 8). The pkdb_data workflow belongs to sub-project 6. Section 8 "GitHub" and "Backend (curators route)" are covered by Tasks 1, 4 and 8.
- **Placeholders:** none; the two places that may need adapting (minimal `User` fields, minimal `study.json` fields) name what to check and keep the assertions.
- **Types:** `Issue`, `StudyState`, `Roster`, `IssueChange`, `SyncPlan`, `Adoption`, `SyncResult` and the function signatures are the same in every task that uses them.
