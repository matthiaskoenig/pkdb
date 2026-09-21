# CLAUDE.md

This file provides guidance when working with code in this repository.

## Project

PK-DB is a database and web interface for pharmacokinetics data, deployed at
[https://pk-db.com](https://pk-db.com). The backend is a Django 3.1.14 REST API
in `backend/` (python 3.9, postgres, elasticsearch); the frontend is a Vue
application in `frontend/`. The stack is deployed with `docker compose`, not
published on PyPI.

## Layout

- `backend/` - the Django project, its own uv project (`pyproject.toml`,
  `tox.ini`, `uv.lock` live here). This is what the python tooling below
  covers.
- `frontend/` - the Vue application. Out of scope of the python tooling; it is
  not linted, formatted or type checked by the commands below and is not
  changed unless a task explicitly asks for it.
- `docs/` - the documentation site (Zensical), `zensical.toml` in the root.
- `scripts/` - repository level python scripts (currently `llms_txt.py`),
  checked against python 3.14, not the backend's python 3.9.
- `.github/` - workflows, rulesets, `CODEOWNERS`, `dependabot.yml`.
- root level compose files and shell scripts (`docker-compose-develop.yml`,
  `docker-compose-production.yml`, `docker-purge.sh`, `deploy.sh`, ...)
  operate the development and production stacks, see `docs/deployment.md`.

## Commands

Every line below is written to be run from the repository root, one after
another, in any order; lines that need `backend/` use a subshell (`(cd
backend && ...)`) so they do not change the shell's working directory for the
next line.

```bash
# environment (uv based, backend is its own uv project)
(cd backend && uv sync --extra dev)
uv run --project backend pre-commit install   # once per checkout

# tests: need the services of docker-compose-test.yml (ports 5434 / 9124)
docker compose -f docker-compose-test.yml up -d --wait
(cd backend && uv run pytest -q)
(cd backend && uv run tox -e py3.9)      # the tests, matching CI
(cd backend && uv run tox -e ty)         # ty type check

# lint / format (backend/ and scripts/ are covered by the hierarchical
# .ruff.toml configuration)
uv run --project backend ruff check .
uv run --project backend ruff format .

# documentation (zensical needs python 3.14, the backend is on 3.9)
uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean
uvx --python 3.14 --with-requirements docs/requirements.txt zensical serve
```

## Test services, never the development stack

The tests run only against `docker-compose-test.yml` (postgres `localhost:5434`,
elasticsearch `localhost:9124`, no named volumes). Never run `search_index
--rebuild`, `flush`, `migrate` or any other destructive command against the
development stack (postgres `localhost:5433`, elasticsearch `localhost:9123`,
containers `pkdb-*-1`) or the production stack. Never run a root level script
(`docker-purge.sh`, `docker-update.sh`, `deploy.sh`, `backup.sh`,
`elastic-rebuild-index.sh`, `docker-down-up.sh`, `docker-interactive.sh`) or a
`docker compose` command against `docker-compose-develop.yml` or
`docker-compose-production.yml` unless explicitly asked; several of them
delete volumes, rebuild the search index or pull and deploy, see
`docs/deployment.md`.

## Migrations

Migrations (`backend/*/migrations/*.py`) are gitignored and generated per
deployment; CI runs `manage.py makemigrations` before the tests, and
`docker-purge.sh` runs it as part of resetting the development stack.
`backend/` is bind mounted into the running development container
(`pkdb-backend-1`): never run `manage.py makemigrations` in a checkout whose
`backend/` is bind mounted into a running development container unless you
mean to change that stack. For the tests, use the migration files already
present in the checkout; generate them locally with `uv run python
manage.py makemigrations` from `backend/` if none exist yet.

## Branch model and release

`develop` is the default branch, protected by the rulesets in
`.github/rulesets/`; every change goes through a pull request with the
`tests`, `ruff`, `ty` and `docs` checks green. `main` tracks the latest
release and is only fast-forwarded by the `sync-main` job of the `CI-CD`
workflow. A release is a tag `v<version>` on `develop`, with release notes in
`release-notes/<version>.md` (without the leading `v`); there is no PyPI
release. Details are in `docs/development.md`.

## Conventions

- Never use the em dash character, use the plain dash `-`.
- Commit messages carry no agent co-author line and no "Generated with" line.
- The behavior of the backend does not change unless a task explicitly asks
  for it.
