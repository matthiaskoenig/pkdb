# Branching Model and Tooling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the backend and the python code of `pkdb` to the branching model, tooling, workflows, repository policies and zensical documentation of `pkdb_data` and `pkdb_models`, without PyPI releases and without a change of the frontend.

**Architecture:** All file changes happen on the branch `tooling` and reach the repository through one pull request. The templates are the files of the sibling checkout `/home/USERNAME/git/pkdb_models` (commit `d720fe2b8`), which already has the variant without PyPI; every task names the template and the exact adaptations. The tests come before the mass fixes, so formatting, lint and type fixes are made with a safety net. The remote operations (rulesets, branch deletion, tag) come last and are confirmed one by one.

**Tech Stack:** uv, hatchling, ruff, ty, tox with tox-uv, pytest with pytest-django and pytest-env, pre-commit, bump-my-version, zensical, GitHub Actions with service containers, GitHub rulesets, Django 3.1.14 on python 3.9, postgres 18.0, elasticsearch 7.9.2.

**Spec:** `superpowers/specs/2026-09-21-branching-tooling-design.md`

## Global Constraints

- Never use the em dash character, use the plain dash `-`.
- Commit messages carry no agent co-author line.
- `gh-axi` is used instead of `gh` in interactive work. `apply.sh` and the workflows keep `gh`, they run for the maintainer and on the runners.
- Django 3.1.14, the pinned dependencies and python 3.9 stay. `requires-python = ">=3.9"`, CI runs python 3.9 on `ubuntu-latest`.
- `frontend/` and `nginx/` are not changed.
- The python project stays in `backend/`. No `src/` layout.
- ruff: rule set of `pkdb_data`, ignored only `RUF012` and `D106`, excluded `**/migrations/**` and `frontend`. All other findings are fixed, no per-file ignores, no placeholder docstrings.
- ty: `error-on-warning = true`. `# ty: ignore[<rule>]` only where Django cannot be typed, always with the rule and the reason.
- Required checks are named exactly `tests`, `ruff`, `ty`, `docs`.
- Tags keep the format `v<version>`, the first release is `v0.10.0`, the release notes file is `release-notes/0.10.0.md`.
- The behavior of the backend does not change, except for the fix of `np.NaN` (task 1) and the elasticsearch host setting (task 2).

## Baseline found during planning

- `backend/.venv` exists with python 3.9 and the locked dependencies. The compose stack of `docker-compose-develop.yml` runs on the development machine: postgres on `localhost:5433`, elasticsearch on `localhost:9123`, backend on `localhost:8000`, frontend on `localhost:8081`.
- ruff with the `pkdb_data` rule set: 1366 findings outside of migrations (363 `D102`, 131 `D101`, 125 `RUF012`, 108 `D106`, 61 `RET503`, ...), 50 files need formatting.
- ty: 327 diagnostics without stubs, about 130 with `django-stubs` and `djangorestframework-stubs`.
- `settings.py` reads all `PKDB_*` variables with `os.environ[...]` on import, and the elasticsearch host is hardcoded as `elasticsearch:9200`, the name of the compose service. Tests outside of compose cannot reach it.
- zensical does not support python 3.9. The documentation tooling cannot be part of the `dev` extra of the backend.
- `backend/pkdb_app/outputs/models.py:128` uses `np.NaN`, which NumPy 2 removed (pull request #756).
- `.env.local` holds development values only (the email values are empty). It stays tracked.
- `utils.clean_import` has an unreachable branch: `"NA"` is never mapped to `None`. The tests pin the current behavior, the branch is reported to the maintainer and not changed here.

## Deviations from the spec, decided during planning

The spec is updated in the commit of this plan.

- One `.ruff.toml` in the root instead of `backend/.ruff.toml`: ruff finds the configuration hierarchically, so one file covers `backend/` and `scripts/`.
- zensical is not in the `dev` extra. `docs/requirements.txt` pins it, the build runs with `uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean`.
- The test environment is set by `pytest-env` in `backend/pyproject.toml` with defaults which CI overrides. There is no `backend/.env.test`.
- The tests run against their own services of `docker-compose-test.yml` (postgres on `localhost:5434`, elasticsearch on `localhost:9124`, no volumes). The index names are fixed strings, so a rebuild against the development stack would empty the development indices.
- New setting `PKDB_ELASTICSEARCH_HOST` with the default `elasticsearch:9200`.
- ty checks `backend/` only. `scripts/llms_txt.py` needs python 3.11 (`tomllib`) and is covered by ruff.
- The unit tests cover `error_measures.py`, `utils.py`, `info_nodes/units.py` and `behaviours.map_field`. The normalization and `pk_calculation.py` need info nodes in the database and are not covered; they are candidates for the tests of the stack upgrade.

## File Structure

| file | responsibility |
| ---- | -------------- |
| `backend/pyproject.toml`, `backend/uv.lock`, `backend/.python-version` | package metadata, `dev` extra, pytest, pytest-env and ty configuration |
| `backend/tox.ini` | environments `py3.9` and `ty` |
| `.ruff.toml`, `.pre-commit-config.yaml`, `.bumpversion.toml`, `.gitignore`, `.git-blame-ignore-revs` | tooling of the repository level |
| `docker-compose-test.yml` | postgres and elasticsearch for the tests, without volumes |
| `backend/tests/test_smoke.py` | checks, migrations, endpoints and the search index against the services |
| `backend/tests/test_error_measures.py`, `test_utils.py`, `test_units.py`, `test_behaviours.py` | unit tests |
| `.github/workflows/{ci-cd,ruff,ty,docs}.yml` | the four required checks, docker build, release and `sync-main` |
| `.github/rulesets/{develop,main,tags}.json`, `apply.sh` | repository policies |
| `.github/{CODEOWNERS,dependabot.yml,pull_request_template.md}` | review and maintenance |
| `zensical.toml`, `docs/*.md`, `docs/requirements.txt`, `docs/robots.txt`, `scripts/llms_txt.py` | documentation |
| `README.md`, `INSTALLATION.md`, `CLAUDE.md`, `release-notes/0.10.0.md` | entry points for people and agents |

---

### Task 1: Fix `np.NaN` (pull request #756)

**Files:**
- Modify: `backend/pkdb_app/outputs/models.py:128`

- [ ] **Step 1: Reproduce.** `cd backend && .venv/bin/python -c "import numpy as np; np.NaN"` fails with `AttributeError: np.NaN was removed in the NumPy 2.0 release`. In the running stack `docker compose -f docker-compose-develop.yml logs backend | grep -c "np.NaN"` or a rebuild of the `outputs` index shows the same error.
- [ ] **Step 2: Fix.** The pull request is from a fork and cannot pass the new checks, so the one line change is applied here with the author credited: `np.NaN` becomes `np.nan`. The commit carries the trailer `Co-authored-by:` of the pull request author (name and email from `gh-axi api repos/matthiaskoenig/pkdb/pulls/756/commits`).
- [ ] **Step 3: Verify.** `rg -n "np\.NaN|np\.NAN|np\.Inf\b|np\.float_\b" backend` prints nothing.
- [ ] **Step 4: Commit.** `git commit -m "Replace np.NaN, which NumPy 2 removed (#756)"`. The pull request is closed with a comment and thanks in the rollout (task 8).

### Task 2: Packaging, tooling configuration and test environment

**Files:**
- Modify: `backend/pyproject.toml`, `backend/pkdb_app/settings.py:235-239`, `.gitignore`, `docker-compose-develop.yml` and `docker-compose-production.yml` only if they list the backend environment explicitly
- Create: `.ruff.toml`, `backend/tox.ini`, `backend/.python-version`, `.pre-commit-config.yaml`, `.bumpversion.toml`

- [ ] **Step 1: `backend/pyproject.toml`.**
  - Replace both extras with one `dev` extra, lower bounds which resolve on python 3.9: `bump-my-version>=1.2.0`, `ruff>=0.16.6`, `pre-commit>=4.3.0`, `ty>=0.0.78`, `tox>=4.30.0`, `tox-uv>=1.28.0`, `pytest>=8.4.0`, `pytest-django>=4.11.0`, `pytest-env>=1.1.5`, `pytest-cov>=6.0.0`, `django-stubs>=5.1.0`, `djangorestframework-stubs>=3.15.0`, `types-Markdown>=3.7.0`, `ipython>=8.18.0`, `ipdb>=0.13.13`. When `uv lock` cannot resolve a bound on python 3.9 the bound is lowered to the newest version with python 3.9 support.
  - `[project_urls]` becomes `[project.urls]` with `Homepage = "https://pk-db.com"`, `Documentation = "https://matthiaskoenig.github.io/pkdb"`, `Repository`, `Issues`, `Changelog = "https://github.com/matthiaskoenig/pkdb/tree/develop/release-notes"`.
  - Classifier `Programming Language :: Python :: 3.9` instead of `3.13`.
  - `[tool.hatch.build.targets.wheel] packages = ["pkdb_app"]`.
  - Add:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
DJANGO_SETTINGS_MODULE = "pkdb_app.settings"
addopts = "--strict-markers"

[tool.pytest_env]
# defaults for the services of docker-compose-test.yml; an environment variable
# which is set (CI) wins
PKDB_DJANGO_CONFIGURATION = {value = "local", skip_if_set = true}
PKDB_API_BASE = {value = "http://localhost:8000", skip_if_set = true}
PKDB_SECRET_KEY = {value = "test-secret-key-not-used-anywhere-else", skip_if_set = true}
PKDB_DB_NAME = {value = "postgres", skip_if_set = true}
PKDB_DB_USER = {value = "postgres", skip_if_set = true}
PKDB_DB_PASSWORD = {value = "postgres", skip_if_set = true}
PKDB_DB_SERVICE = {value = "localhost", skip_if_set = true}
PKDB_DB_PORT = {value = "5434", skip_if_set = true}
PKDB_ELASTICSEARCH_HOST = {value = "localhost:9124", skip_if_set = true}
PKDB_EMAIL_HOST_USER = {value = "", skip_if_set = true}
PKDB_EMAIL_HOST_PASSWORD = {value = "", skip_if_set = true}

[tool.ty.src]
include = ["pkdb_app", "tests", "manage.py"]
exclude = ["**/migrations/**"]

[tool.ty.terminal]
error-on-warning = true
```

- [ ] **Step 2: `settings.py`.**

```python
ELASTICSEARCH_DSL = {
    'default': {
        'hosts': os.environ.get('PKDB_ELASTICSEARCH_HOST', 'elasticsearch:9200')
    },
}
```

  The default keeps compose and production unchanged, no compose file needs the variable.
- [ ] **Step 3: `.ruff.toml`** in the root. Copy of `/home/USERNAME/git/pkdb_models/.ruff.toml` with: `target-version = "py39"`, `extend-exclude = ["**/migrations/**", "frontend", "docs"]`, `RUF012` and `D106` added to `ignore` with the comment "Django idioms: class attributes of models, serializers and views, nested Meta classes", `[lint.per-file-target-version] "scripts/*.py" = "py314"`, first party `known-first-party = ["pkdb_app"]`, and the per-file ignores of the template for `tests/` moved to `backend/tests/**`.
- [ ] **Step 4: `backend/tox.ini`.**

```ini
[tox]
envlist = ty, py3.9

[testenv]
# editable: manage.py and the settings module are used from the checkout
package = editable
extras =
    dev
passenv =
    PKDB_*
commands =
    pytest {posargs}

[testenv:ty]
passenv =
    TY_OUTPUT_FORMAT
extras =
    dev
commands =
    ty check
```

- [ ] **Step 5: `backend/.python-version`** with the line `3.9`.
- [ ] **Step 6: `.pre-commit-config.yaml`.** Copy of the `pkdb_models` file. `trailing-whitespace`, `end-of-file-fixer`, `mixed-line-ending`, `check-json`, `check-yaml`, `check-toml` and `debug-statements` get `exclude: ^(frontend/|nginx/|docs/presentation/|docs/images/)`. The ty hook runs `uv run --project backend --extra dev ty check --project backend` as a local hook with `files: ^backend/.*\.py$` and `pass_filenames: false`. ruff follows `.ruff.toml`.
- [ ] **Step 7: `.bumpversion.toml`.** Copy of the `pkdb_models` file with `current_version = "0.9.8"`, `tag = false` and the single file `./backend/pkdb_app/__init__.py`.
- [ ] **Step 8: `.gitignore`.** Add `site/`, `.cache/`, `.tox/`, `.pytest_cache/`, `.ruff_cache/`, `.venv/`, `dist/`.
- [ ] **Step 9: Environment.** `cd backend && uv sync --extra dev`, then in the root `uv run --project backend pre-commit install`.
- [ ] **Step 10: Verify.** `cd backend && uv run python -c "import pytest_django, pytest_env, django; print(django.VERSION)"` prints `(3, 1, 14, 'final', 0)`. `docker compose -f docker-compose-develop.yml up -d --build backend` and `curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/v1/` prints `200`: the setting default works in compose.
- [ ] **Step 11: Commit.** `git commit -m "Update the tooling to uv, ruff, ty, tox and pre-commit as in pkdb_data"`. ruff and ty do not pass yet; the pre-commit hooks are skipped for this commit and the following ones until task 5 with `--no-verify`.

### Task 3: Tests

**Files:**
- Create: `docker-compose-test.yml`, `backend/tests/__init__.py` (docstring only), `backend/tests/test_smoke.py`, `backend/tests/test_error_measures.py`, `backend/tests/test_utils.py`, `backend/tests/test_units.py`, `backend/tests/test_behaviours.py`
- Delete: `backend/pkdb_app/studies/tests.py`, `backend/pkdb_app/subjects/tests.py`

**Interfaces:**
- Consumes: the `[tool.pytest_env]` table and `PKDB_ELASTICSEARCH_HOST` of task 2.

The tests are written against the current code and have to pass before task 4 changes it. A test which fails shows a bug of the backend: it is reproduced in the running stack, fixed in its own commit, and reported.

- [ ] **Step 0: `docker-compose-test.yml`** in the root, services for the tests only, without volumes, so every start is empty and the development data is never touched:

```yaml
# Services for the backend tests, see docs/development.md
#   docker compose -f docker-compose-test.yml up -d --wait
#   docker compose -f docker-compose-test.yml down
name: pkdb-test
services:
  postgres:
    image: postgres:18.0
    environment:
      POSTGRES_PASSWORD: postgres
    ports:
      - "127.0.0.1:5434:5432"
    tmpfs:
      - /var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 20
  elasticsearch:
    image: elasticsearch:7.9.2
    environment:
      discovery.type: single-node
      ES_JAVA_OPTS: -Xms512m -Xmx512m
    ports:
      - "127.0.0.1:9124:9200"
    healthcheck:
      test: ["CMD-SHELL", "curl -fs http://localhost:9200/_cluster/health"]
      interval: 5s
      timeout: 5s
      retries: 40
```

- [ ] **Step 1: `test_smoke.py`.**

```python
"""Smoke tests of the backend against postgres and elasticsearch.

The services are the ones of `docker-compose-test.yml`, see `docs/development.md`.
"""

from io import StringIO

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

PUBLIC_ENDPOINTS = [
    "/api/v1/",
    "/api/v1/swagger.json",
    "/api/v1/statistics/",
    "/api/v1/studies/",
    "/api/v1/info_nodes/",
    "/api/v1/_studies/",
]


@pytest.fixture
def search_index(db: None) -> None:
    """Create the elasticsearch indices for the empty test database."""
    call_command("search_index", "--rebuild", "-f", stdout=StringIO())


def test_check() -> None:
    """The Django system check reports no issue."""
    call_command("check", "--fail-level", "WARNING", stdout=StringIO())


@pytest.mark.django_db
def test_no_missing_migrations() -> None:
    """The migrations are complete for the models."""
    call_command("makemigrations", "--check", "--dry-run", stdout=StringIO())


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", PUBLIC_ENDPOINTS)
def test_public_endpoint(endpoint: str, search_index: None) -> None:
    """The public endpoints answer for an empty database."""
    response = APIClient().get(endpoint)
    assert response.status_code == 200, response.content[:500]


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", ["/api/v1/_studies/", "/api/v1/_info_nodes/"])
def test_anonymous_write_rejected(endpoint: str) -> None:
    """An anonymous client cannot write."""
    response = APIClient().post(endpoint, data={}, format="json")
    assert response.status_code in {401, 403}
```

  The index names are fixed strings (`studies`, `outputs`, ...), so a rebuild against the elasticsearch of the development stack would empty the development indices. The tests therefore use their own services, see step 0.
- [ ] **Step 2: `test_error_measures.py`.**

```python
"""Test the calculation of error measures."""

import numpy as np
import pytest

from pkdb_app.error_measures import calculate_cv, calculate_sd, calculate_se


def test_sd_from_se_and_count() -> None:
    """The standard deviation is se * sqrt(n)."""
    sd = calculate_sd(se=np.array([1.0]), count=np.array([4]), cv=None, mean=None)
    assert sd == pytest.approx([2.0])


def test_sd_from_cv_and_mean() -> None:
    """The standard deviation is cv * mean."""
    sd = calculate_sd(se=None, count=None, cv=np.array([0.5]), mean=np.array([10.0]))
    assert sd == pytest.approx([5.0])


def test_sd_missing_information() -> None:
    """Without se and count or cv and mean there is no standard deviation."""
    assert calculate_sd(se=np.array([1.0]), count=None, cv=None, mean=None) is None


def test_se_from_sd_and_count() -> None:
    """The standard error is sd / sqrt(n)."""
    se = calculate_se(sd=np.array([2.0]), count=np.array([4]), cv=None, mean=None)
    assert se == pytest.approx([1.0])


def test_se_from_cv_mean_and_count() -> None:
    """The standard error is cv * mean / sqrt(n)."""
    se = calculate_se(
        sd=None, count=np.array([4]), cv=np.array([0.5]), mean=np.array([10.0])
    )
    assert se == pytest.approx([2.5])


def test_cv_from_sd_and_mean() -> None:
    """The coefficient of variation is sd / mean."""
    cv = calculate_cv(sd=np.array([5.0]), count=None, se=None, mean=np.array([10.0]))
    assert cv == pytest.approx([0.5])


def test_cv_mean_zero_is_nan() -> None:
    """A mean of zero gives nan and not inf."""
    cv = calculate_cv(
        sd=np.array([5.0, 5.0]), count=None, se=None, mean=np.array([0.0, 10.0])
    )
    assert np.isnan(cv[0])
    assert cv[1] == pytest.approx(0.5)


def test_cv_does_not_change_mean() -> None:
    """The cleaning of the mean works on a copy."""
    mean = np.array([0.0, 10.0])
    calculate_cv(sd=np.array([5.0, 5.0]), count=None, se=None, mean=mean)
    assert mean[0] == 0.0
```

- [ ] **Step 3: `test_utils.py`.**

```python
"""Test the helper functions."""

import pytest
from rest_framework import serializers

from pkdb_app.utils import (
    _validate_not_allowed_key,
    _validate_required_key,
    _validate_required_key_and_value,
    _validate_required_key_and_value_or_nr,
    clean_import,
    create_choices,
    create_if_exists,
    list_duplicates,
    recursive_iter,
    set_keys,
)


def test_list_duplicates() -> None:
    """Only the items which occur more than once are returned, once each."""
    assert sorted(list_duplicates(["a", "b", "a", "c", "a", "c"])) == ["a", "c"]
    assert list_duplicates(["a", "b"]) == []


def test_create_choices() -> None:
    """Strings are their own key, other items provide `key`."""

    class Item:
        key = "item"

    assert create_choices(["a", Item()]) == [("a", "a"), ("item", "item")]


def test_create_if_exists() -> None:
    """The value is copied only when the source has the key."""
    assert create_if_exists({"a": 1}, "a", {}, "b") == {"b": 1}
    assert create_if_exists({"a": 1}, "x", {}, "b") == {}


def test_clean_import() -> None:
    """Empty values and nan are dropped, everything else is kept."""
    data = {"a": 1, "b": "", "c": " ", "d": float("nan"), "e": "NA", "f": "text"}
    assert clean_import(data) == {"a": 1, "e": "NA", "f": "text"}


def test_recursive_iter() -> None:
    """The nested structure is flattened to key tuples."""
    data = {"a": {"b": 1}, "c": [2, {"d": 3}], "e": []}
    assert dict(recursive_iter(data)) == {
        ("a", "b"): 1,
        ("c", 0): 2,
        ("c", 1, "d"): 3,
        ("e",): None,
    }


def test_set_keys() -> None:
    """The value is set at the nested key."""
    data = {"a": {"b": 1}}
    set_keys(data, 2, "a", "b")
    assert data == {"a": {"b": 2}}


def test_validate_required_key_and_value() -> None:
    """A missing key and a null value are errors."""
    _validate_required_key_and_value({"a": 1}, "a")
    with pytest.raises(serializers.ValidationError):
        _validate_required_key_and_value({}, "a")
    with pytest.raises(serializers.ValidationError):
        _validate_required_key_and_value({"a": None}, "a", details="details")


def test_validate_required_key_and_value_or_nr() -> None:
    """The value `NR` (not reported) is accepted and becomes None."""
    attrs = {"a": "NR"}
    _validate_required_key_and_value_or_nr(attrs, "a")
    assert attrs == {"a": None}
    with pytest.raises(serializers.ValidationError):
        _validate_required_key_and_value_or_nr({}, "a")


def test_validate_required_key() -> None:
    """Only the key is required, the value can be None."""
    _validate_required_key({"a": None}, "a")
    with pytest.raises(serializers.ValidationError):
        _validate_required_key({}, "a")


def test_validate_not_allowed_key() -> None:
    """The key must not exist."""
    _validate_not_allowed_key({}, "a")
    with pytest.raises(serializers.ValidationError):
        _validate_not_allowed_key({"a": 1}, "a")
```

- [ ] **Step 4: `test_units.py`.**

```python
"""Test the unit registry."""

import pytest

from pkdb_app.info_nodes.units import ureg


@pytest.mark.parametrize("unit", ["cups", "beverages", "none"])
def test_count_units(unit: str) -> None:
    """The custom count units convert to count."""
    assert ureg.Quantity(2, unit).to("count").magnitude == pytest.approx(2)


def test_percent() -> None:
    """Percent is a hundredth of a count."""
    assert ureg.Quantity(50, "percent").to("count").magnitude == pytest.approx(0.5)


@pytest.mark.parametrize("unit", ["IU", "NO_UNIT", "arbitrary_unit"])
def test_own_dimension(unit: str) -> None:
    """The units with an own dimension do not convert to count or mass."""
    quantity = ureg.Quantity(1, unit)
    assert not quantity.check("[mass]")
    assert not quantity.dimensionless


def test_pharmacokinetic_conversion() -> None:
    """A typical conversion of a concentration."""
    assert ureg.Quantity(1, "mg/l").to("µg/ml").magnitude == pytest.approx(1)
```

- [ ] **Step 5: `test_behaviours.py`.** `map_field` is read first (`sed -n 54,66p backend/pkdb_app/behaviours.py`); the test asserts its result for `["value", "mean"]`, the expected value is what the function returns for the current code, e.g.:

```python
"""Test the model behaviours."""

from pkdb_app.behaviours import map_field


def test_map_field() -> None:
    """Every field gets its map field."""
    assert map_field(["value", "mean"]) == ["value_map", "mean_map"]
```

- [ ] **Step 6: Run.** `docker compose -f docker-compose-test.yml up -d --wait`, then `cd backend && uv run pytest -q` and `uv run tox -e py3.9` pass. `curl -s http://localhost:8000/api/v1/statistics/` still reports the study count of before the run: the tests did not touch the development data.
- [ ] **Step 7: Delete** `studies/tests.py` and `subjects/tests.py`.
- [ ] **Step 8: Commit.** `git commit -m "Smoke tests against postgres and elasticsearch, unit tests of the helpers"`

### Task 4: Formatting and automatic fixes

**Files:**
- Modify: the python files of `backend/` reported by ruff
- Create: `.git-blame-ignore-revs`

- [ ] **Step 1:** `uv run --project backend ruff format` and `uv run --project backend ruff check --fix` (safe fixes only, no `--unsafe-fixes`). No manual edit in this commit.
- [ ] **Step 2: Verify.** `cd backend && uv run pytest -q` passes; `git diff --stat | tail -1`; `git diff -- '*/migrations/*' | wc -l` prints `0`.
- [ ] **Step 3: Commit.** `git commit -m "Format the backend with ruff and apply the safe automatic fixes"`
- [ ] **Step 4: `.git-blame-ignore-revs`** with a comment line and the full hash of the commit of step 3. Commit: `git commit -m "Skip the formatting commit in git blame"`.

### Task 5: Manual ruff fixes and docstrings

**Files:**
- Modify: the python files of `backend/pkdb_app/`, `backend/manage.py`

The work is split by Django app so that the parts are independent and can run in parallel: (a) `comments`, `users`, `info_nodes`; (b) `subjects`, `interventions`; (c) `outputs`, `data`; (d) `studies`; (e) the modules of `pkdb_app/` itself. Each part follows the same steps.

- [ ] **Step 1: List.** `uv run --project backend ruff check backend/pkdb_app/<app> --output-format concise`.
- [ ] **Step 2: Fix the findings which are not docstrings.** Rules of the hand: `RET503` gets an explicit `return None`; `B905` is not reported for `target-version = "py39"` (`zip(strict=)` needs python 3.10), a report means the target version is wrong; `B028` gets `stacklevel=2`; `B019`, `B018`, `SIM*`, `C4*`, `RUF015`, `RUF059` are rewritten as ruff proposes after reading the code; unused variables are removed only if the right hand side has no side effect. No behavior change: a fix which would change a query, a serializer field or a response is stopped and reported.
- [ ] **Step 3: Docstrings.** Every public module, class, method and function gets a docstring in the imperative mood which says what it does, read from the code, not from the name. Serializer and view methods of the framework (`create`, `update`, `validate`, `to_representation`, `to_internal_value`, `get_queryset`, ...) say what this implementation adds to the framework behavior. One line is enough when one line says it. No `"""Docstring."""`, no repetition of the name.
- [ ] **Step 4: Verify the part.** `uv run --project backend ruff check backend/pkdb_app/<app>` and `ruff format --check` pass, `cd backend && uv run pytest -q` passes.
- [ ] **Step 5: Commit the part.** `git commit -m "ruff fixes and docstrings: <apps>"`
- [ ] **Step 6: After all parts.** `uv run --project backend ruff check && uv run --project backend ruff format --check` pass for the repository.

### Task 6: ty fixes

**Files:**
- Modify: the python files of `backend/pkdb_app/`, `backend/tests/`

- [ ] **Step 1: List.** `cd backend && uv run ty check --output-format concise | sed -E 's/.*\[([a-z-]+)\].*/\1/' | sort | uniq -c | sort -rn`.
- [ ] **Step 2: Fix by kind.**
  - Reverse relations and managers: annotation on the model under `TYPE_CHECKING`, e.g. `outputs: "RelatedManager[Output]"` with `from django.db.models.manager import RelatedManager` in the `TYPE_CHECKING` block. No runtime import is added which could create an import cycle.
  - Attributes on a union or an optional: narrowing with `isinstance` or an `is None` branch which keeps the current behavior (the branch raises what the attribute access raised before, or returns what was returned before).
  - `invalid-parameter-default` (`x: str = None`): the annotation becomes `Optional[str]`.
  - `unresolved-import`: the import is fixed if the module moved; a missing stub package is added to the `dev` extra.
  - What Django creates at runtime and the stubs cannot know (e.g. `apps.get_model` results, `serializer.Meta.model` access): `# ty: ignore[<rule>]  # <reason>` on the line.
- [ ] **Step 3: Verify.** `cd backend && uv run tox -e ty` passes, `uv run pytest -q` passes, `uv run --project backend ruff check` still passes, `rg -c "ty: ignore" backend/pkdb_app | awk -F: '{s+=$2} END {print s}'` is reported in the commit message body.
- [ ] **Step 4: Regression check in the stack.** `docker compose -f docker-compose-develop.yml up -d --build backend`; with `chrome-devtools-axi`: `http://localhost:8000/api/v1/` (API root), `/api/v1/swagger/`, `/api/v1/studies/`, `/api/v1/outputs/`, `/api/v1/statistics/` answer with data, `http://localhost:8081` shows the studies table, a study detail page and the data download; the backend log has no traceback: `docker compose -f docker-compose-develop.yml logs --since 10m backend | grep -c Traceback` prints `0`.
- [ ] **Step 5: Commit.** `git commit -m "Type fixes for ty with django-stubs"`. From here on commits run the pre-commit hooks.

### Task 7: Workflows, repository policies and documentation

**Files:**
- Create: `.github/workflows/{ci-cd,ruff,ty,docs}.yml`, `.github/rulesets/{develop,main,tags}.json`, `.github/rulesets/apply.sh`, `.github/CODEOWNERS`, `.github/dependabot.yml`, `.github/pull_request_template.md`, `zensical.toml`, `docs/{index,installation,deployment,development,contributing}.md`, `docs/requirements.txt`, `docs/robots.txt`, `scripts/llms_txt.py`, `CLAUDE.md`, `release-notes/0.10.0.md`
- Modify: `README.md`, `INSTALLATION.md`

- [ ] **Step 1: Verbatim copies** from `/home/USERNAME/git/pkdb_models/.github/`: `rulesets/develop.json`, `rulesets/main.json`, `CODEOWNERS`. `rulesets/tags.json` with the tag pattern checked against `v*`. `apply.sh` with `pkdb_models` replaced by `pkdb` (mode 755). `pull_request_template.md` with the test item "the tests pass against the services (`tox -e py3.9`)".
- [ ] **Step 2: `dependabot.yml`.** `pip` with `directory: /backend` and `github-actions`, both weekly and grouped as in the template; `pip` in `/docs` for `requirements.txt`. For `/backend` an `ignore` list with `update-types: ["version-update:semver-major", "version-update:semver-minor"]` for `Django`, `djangorestframework`, `django-*`, `drf-yasg`, `elasticsearch-dsl`.
- [ ] **Step 3: `ruff.yml`, `ty.yml`.** Copies without the sparse checkout block (the repository is small). `ty.yml` runs in `working-directory: backend` with python 3.9 and `uv sync --extra dev`. Project names replaced in comments and urls.
- [ ] **Step 4: `ci-cd.yml`.** Copy with these changes: job `test` on `ubuntu-latest`, python `3.9`, `working-directory: backend`, and

```yaml
    services:
      postgres:
        image: postgres:18.0
        env:
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 10s --health-timeout 5s --health-retries 10
      elasticsearch:
        image: elasticsearch:7.9.2
        env:
          discovery.type: single-node
          ES_JAVA_OPTS: -Xms512m -Xmx512m
        ports:
          - 9200:9200
        options: >-
          --health-cmd "curl -fs http://localhost:9200/_cluster/health"
          --health-interval 10s --health-timeout 5s --health-retries 20
    env:
      PKDB_DB_SERVICE: localhost
      PKDB_DB_PORT: "5432"
      PKDB_DB_PASSWORD: postgres
      PKDB_ELASTICSEARCH_HOST: localhost:9200
```

  New job `docker`: `docker build backend` with `docker/build-push-action` pinned as the other actions, `push: false`. The aggregate job `tests` needs `test` and `docker`. `release` takes the notes from `release-notes/${GITHUB_REF_NAME#v}.md`: a step strips the `v` and sets `body_path`. `sync-main` as in the template (creates `main` when it does not exist).
- [ ] **Step 5: `docs.yml`.** Copy with the build commands `uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean` and `uv run --no-project --python 3.14 python scripts/llms_txt.py`, without the private repository configuration.
- [ ] **Step 6: `zensical.toml`.** Copy with `pkdb_models` replaced by `pkdb`, site name `PK-DB`, the description "PK-DB - the open pharmacokinetics database", `logo = "pkdb_logo.png"` if the template supports a logo path in `docs/`, no mkdocstrings plugin, nav: Home, Installation, Deployment, Development, Contributing. `docs/images`, `docs/presentation`, `docs/pkdb_api.ipynb`, `docs/requirements_api.txt` are excluded from the build if zensical offers an exclude, otherwise step 9 checks what is published and the size of `site/`.
- [ ] **Step 7: Pages.** `index.md` (what PK-DB is, links to https://pk-db.com, the API, the publication from the README, table of pages, license, funding), `installation.md` (the content of `INSTALLATION.md` checked against the current scripts and compose files, every command is run once; `INSTALLATION.md` becomes a pointer), `deployment.md` (develop and production compose, every `PKDB_*` variable including `PKDB_ELASTICSEARCH_HOST` in a table with meaning and example, `backup.sh`, `deploy.sh`, `docker-purge.sh`, `docker-update.sh`, `docker-down-up.sh`, `docker-interactive.sh`, `elastic-rebuild-index.sh`, nginx; read from the scripts, the FIXME notes of `deploy.sh` are listed as known limitations), `development.md` (copy of the `pkdb_models` page adapted: setup in `backend/` with uv, the checks, the tests with the services of `docker-compose-test.yml` and why they are separate from the development stack, branch model, pull requests, repository policies, release with `v` tags and without PyPI, documentation build with python 3.14), `contributing.md` (branch off `develop`, commit, push, pull request, the four checks and how to fix each locally, update a branch with `git rebase origin/develop`, the one time cleanup of a clone which tracks `master` with the three git commands of the spec).
- [ ] **Step 8: `scripts/llms_txt.py`.** Copy with the project names replaced and the API reference part (`importlib`, `inspect`, the mkdocstrings directive handling) removed; it has to pass ruff.
- [ ] **Step 9: Build and check.** `uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean && uv run --no-project --python 3.14 python scripts/llms_txt.py` pass without warnings. `uvx ... zensical serve`, every page is opened with `chrome-devtools-axi` in light and dark mode and at phone width; nav, tables, code blocks, logo render correctly; `site/superpowers` does not exist; `du -sh site` is reported.
- [ ] **Step 10: `README.md`** (badges of the four workflows, short description, link to the documentation, setup in short, license, funding; the existing scientific content stays), **`CLAUDE.md`** (project, layout, commands, the services for the tests, branch model, release, the rule that `frontend/` is out of scope of the python tooling), **`release-notes/0.10.0.md`** (tooling, tests, documentation, `np.NaN` fix, `PKDB_ELASTICSEARCH_HOST`).
- [ ] **Step 11: Verify.** `uv run --project backend pre-commit run --all-files` passes. `actionlint` (`uvx --from actionlint-py actionlint`) passes for the workflows.
- [ ] **Step 12: Commits.** `git commit -m "GitHub workflows, rulesets and repository policies as in pkdb_data"` and `git commit -m "Documentation with zensical"`.

### Task 8: Rollout

Every step changes the shared public repository and is confirmed by the maintainer before it runs.

- [ ] **Step 1:** `git push -u origin tooling`.
- [ ] **Step 2:** enable GitHub Pages with the source "GitHub Actions"; pull request `tooling` into `develop`; the four checks are green; merge with rebase so the task commits stay separate and the hash in `.git-blame-ignore-revs` stays valid (the hash is checked after the merge and corrected in a follow up pull request if the rebase changed it).
- [ ] **Step 3:** `.github/rulesets/apply.sh`; a direct push to `develop` is rejected.
- [ ] **Step 4:** close #756 with thanks and the hash of the fix, close #752 with the reference to the stack upgrade. Delete `master` after `git diff develop origin/master --stat` shows only what `develop` has in addition; delete `dependabot/pip/backend/django-4.2.26`, `dependabot/pip/backend/djangorestframework-3.15.2`, `dependabot/pip/backend/numpy-1.22.0`, `update-django-dependency`.
- [ ] **Step 5:** release: branch, `uvx bump-my-version bump minor`, pull request, merge, `git tag v0.10.0` on `develop`, `git push origin v0.10.0`; the GitHub release exists and `main` points at the tag; `apply.sh` again for `main.json`.
