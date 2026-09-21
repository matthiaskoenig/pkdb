# Branching model and tooling for pkdb

Date: 2026-09-21

## Goal

Bring `pkdb` to the branching model, tooling, workflows, repository policies and
documentation setup of `pkdb_data` and `pkdb_models`, adapted to a Django backend which
lives in `backend/` and is deployed with docker compose instead of being released on PyPI.

The scope is the backend and the python code of the repository. The frontend is not
changed.

## Decisions

| topic | decision |
| ----- | -------- |
| stack | tooling only: Django 3.1.14, the pinned dependencies and python 3.9 stay. The upgrade of python and Django is a separate project with its own spec, after the tests of this spec exist |
| tests | smoke tests and unit tests with pytest-django against postgres and elasticsearch, as service containers in CI |
| ruff | the rule set of `pkdb_data`, all findings are fixed including real docstrings. Ignored are only the rules which fight Django idioms (`RUF012`, `D106`), migrations are excluded |
| ty | strict (`error-on-warning = true`) with `django-stubs` and `djangorestframework-stubs`, all diagnostics are fixed |
| migration | `develop` stays the default branch, `master` is deleted, the first release creates `main` |
| release | bump on a branch, pull request, tag on `develop`; the tag creates a GitHub release from `release-notes/<version>.md` and fast-forwards `main`. No PyPI job |
| documentation | zensical: home, installation, deployment and operations, development, contributing, `llms.txt` |

Decided without a question, each can be revisited:

- The python project stays in `backend/`, which is the docker build context.
  `pyproject.toml`, `.ruff.toml`, `tox.ini` and `uv.lock` live there. The files of the
  repository level live in the root: `.github/`, `.pre-commit-config.yaml`,
  `.bumpversion.toml`, `zensical.toml`, `docs/`, `scripts/`, `CLAUDE.md`.
- No move to a `src/` layout.
- The first release is `0.10.0`. The tag format stays `v<version>` as for the existing tags
  `v0.9.3` to `v0.9.8`.
- No `CITATION.cff` and no `.zenodo.json` in this update.
- The open pull request #756 (`np.NaN` with NumPy 2) touches backend code and is handled
  before the formatting commit: the bug is reproduced, and the pull request is merged or
  the fix is applied on `tooling`. The dependabot pull request #752 (Django 4.2.26) is
  closed, it belongs to the stack upgrade.
- `.env.local` is tracked. It stays if it holds development values only; it is checked for
  real secrets during the implementation.

## 1. Branch model and migration

- `develop` is the default branch and the integration branch. Documentation is published
  from it.
- `main` tracks the latest release. It is created and fast-forwarded only by the
  `sync-main` job of the release workflow; the first release creates it.
- Work happens on short lived branches off `develop`, deleted after the merge.
- `master` holds only seven merge commits of pull requests from `develop` and no own
  content, so `develop` cannot fast-forward it. It is deleted after the check that
  `git diff develop origin/master` contains nothing which is missing in `develop`.

Rollout order, the rulesets come last because the required checks have to exist first:

1. branch `tooling` with all changes of this spec
2. pull request `tooling` into `develop`, merge, all four checks green on `develop`
3. `.github/rulesets/apply.sh` activates the rulesets and the merge settings
4. `master`, the three stale dependabot branches and `update-django-dependency` are
   deleted on GitHub
5. first release `v0.10.0` creates `main`; `apply.sh` is run again so `main.json` applies

Steps 3, 4 and the tag of step 5 change the shared public repository and are confirmed
with the maintainer one by one.

## 2. Tooling

`backend/pyproject.toml`

- `dev` extra with the complete tooling: ruff, ty, tox, tox-uv, pytest, pytest-django,
  pytest-cov, pre-commit, bump-my-version, zensical, django-stubs,
  djangorestframework-stubs, ipython, ipdb.
- removed: `flake8`, `mock`, `factory-boy`, `django-nose`, `nose-progressive`, `coverage`
  and the `test` extra, which is merged into `dev`.
- fixes: `[project_urls]` becomes `[project.urls]`, the documentation url points at the
  published site, the hatch wheel target `backend/pkdb_app` becomes `pkdb_app` (the path
  is relative to `backend/`), the classifier lists python 3.9 instead of 3.13.
- `[tool.pytest.ini_options]`: `testpaths`, `DJANGO_SETTINGS_MODULE`.
- `[tool.ty]`: `error-on-warning = true`, same scope as ruff.

Other files

- `backend/.ruff.toml`: the rule set of `pkdb_data` with `target-version = "py39"`.
  Ignored: `RUF012` (mutable class attributes of Django models, serializers and views) and
  `D106` (nested `Meta` classes). Excluded: `**/migrations/**`. Checked: `pkdb_app/`,
  `tests/`, `manage.py`, and `scripts/` of the root.
- The fixes come in separate commits so the history stays readable: first formatting and
  safe automatic fixes without a manual change, then the manual fixes per rule group, then
  the docstrings, then the ty fixes. Docstrings describe what the class, method or
  function does; no placeholder docstrings.
- ty: reverse relations and managers get annotations, narrowing replaces unchecked
  attribute access. `# ty: ignore[<rule>]` is allowed only where Django cannot be typed,
  always with the rule and the reason.
- `backend/tox.ini`: environments `py3.9` and `ty`.
- `.pre-commit-config.yaml`: current hook versions, ruff and ty for `backend/` and
  `scripts/`. The whitespace and end-of-file fixers skip `frontend/`, `nginx/` and
  `docs/presentation/`; the large file, merge conflict and private key hooks cover
  everything.
- `.bumpversion.toml`: `tag = false`, updates `backend/pkdb_app/__init__.py`.
- `.gitignore`: `site/`, `.tox/`, `.ruff_cache/`, `.venv/` added.
- `backend/.python-version` with `3.9` is committed.

## 3. Tests

The repository has no tests today: `studies/tests.py` is empty and `subjects/tests.py`
holds only the Django template comment. Both are deleted. The new tests live in `backend/tests/`.

Smoke tests, they need postgres and elasticsearch:

- `manage.py check` passes.
- All migrations apply on an empty database (done by the pytest-django database setup).
- `makemigrations --check --dry-run` reports no missing migration.
- The API root `api/v1/`, `api/v1/swagger.json`, `api/v1/statistics/` and the list
  endpoints `studies`, `info_nodes`, `_studies` answer with 200 for an empty database.
- The elasticsearch indices are created and rebuilt on the empty database
  (`search_index --rebuild -f`).
- The endpoints which need authentication reject an anonymous write with 401 or 403.

Unit tests, no services: `error_measures.py`, `utils.py`, the normalization in
`behaviours.py`, the unit handling in `info_nodes/units.py` and the pharmacokinetic
calculation in `outputs/pk_calculation.py`, each with the edge cases (missing values,
zero counts, unit conversion).

Environment

- `settings.py` reads `PKDB_*` variables. `backend/.env.test` is committed with the test
  values (no secrets) and is documented in `docs/development.md`.
- CI: service containers `postgres:18.0` and `elasticsearch:7.9.2`, the images of
  `docker-compose-develop.yml`, with health checks.
- Local: the same two services from `docker-compose-develop.yml`, then `tox -e py3.9`.

## 4. Workflows and policies

- `ci-cd.yml`: job `test` (ubuntu, python 3.9, the service containers, `tox -e py3.9` in
  `backend/`), job `docker` (build of `backend/Dockerfile`), aggregate job `tests` as the
  required check, and on a tag the jobs `release` (GitHub release with the notes of
  `release-notes/<version>.md`) and `sync-main` (fast-forward of `main`, created by the
  first release).
- `ruff.yml`, `ty.yml`, `docs.yml` as in `pkdb_data`: least privilege,
  `persist-credentials: false`, pinned action versions, `working-directory: backend` for
  the python steps.
- `.github/rulesets/develop.json`, `main.json`, `tags.json` and `apply.sh`, `CODEOWNERS`,
  `pull_request_template.md` as in `pkdb_data`. `develop`: pull request required, checks
  `tests`, `ruff`, `ty`, `docs`, resolved conversations, linear history, no force push, no
  deletion, no bypass.
- `dependabot.yml`: `pip` in `/backend` and `github-actions`, both grouped. The pinned
  Django stack (Django, djangorestframework, the elasticsearch packages and the django
  extensions) is ignored for version updates until the stack upgrade; security updates
  stay active. No `npm` entry, the frontend is out of scope.

## 5. Documentation

- `zensical.toml` and `docs/`:
  - `index.md`: what PK-DB is, links to the website, the API and the publication.
  - `installation.md`: the content of `INSTALLATION.md`, which becomes a pointer to the
    page.
  - `deployment.md`: docker compose for develop and production, the `PKDB_*` environment
    variables, `backup.sh`, `deploy.sh`, `docker-purge.sh`, `docker-update.sh`,
    `elastic-rebuild-index.sh` and the nginx configuration. Today this is documented only
    in script comments.
  - `development.md`: setup with uv, the checks, the tests with the services, branch
    model, pull requests, repository policies, release.
  - `contributing.md`: branch, commit, push, pull request, fix red checks, update a branch.
- `scripts/llms_txt.py` from `pkdb_models` creates `llms.txt`, `llms-full.txt` and the
  markdown of every page.
- `docs/images/`, `docs/presentation/` and `docs/pkdb_api.ipynb` stay and are not part of
  the navigation.
- Published from `develop` to GitHub Pages; the repository is public, so the private
  repository configuration of `pkdb_data` is not needed.
- `README.md` is updated (badges, links to the site, setup in short), `CLAUDE.md` is
  added, `release-notes/0.10.0.md` describes the release.
- The specs and plans in `superpowers/` are not part of the published site.

## 6. Transition of the contributors

`develop` keeps its name, so no clone needs a rename. A clone which tracks `master` runs
once:

```bash
git switch develop
git branch -D master
git fetch --prune origin
```

The formatting commit changes 50 files. A contributor branch is rebased on `develop`
after the merge; `docs/contributing.md` describes the steps. `.git-blame-ignore-revs` in
the root lists the formatting commit so `git blame` skips it.

## Verification

- In `backend/`: `uv sync --extra dev`, `ruff check`, `ruff format --check`, `tox -e ty`
  and `tox -e py3.9` against the compose services pass locally.
- In the root: `zensical build --clean`, `scripts/llms_txt.py` and
  `pre-commit run --all-files` pass.
- The docker image builds, `docker-compose-develop.yml` starts the complete stack, and the
  API, swagger and the frontend are checked in the browser. This is the regression check
  for the formatting, lint and type fixes beyond the automated tests.
- The four workflows are green on the pull request and on `develop`.
- A direct push to `develop` is rejected after `apply.sh`.
- The tag `v0.10.0` creates the GitHub release and `main` points at the tagged commit.
