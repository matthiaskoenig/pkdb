# Development

This page describes the branch model, the repository policies, the tooling and the release. The step by step guide for a first contribution is [Contributing](contributing.md). The repository is [matthiaskoenig/pkdb](https://github.com/matthiaskoenig/pkdb); development happens against the `develop` branch via pull requests. `backend/` is a self-contained python project (Django 3.1, python 3.9); `frontend/` is a separate Vue project and out of scope of the python tooling described here.

## Branch model

Two branches are permanent:

- **`develop`** is the default branch and the branch everything is integrated into.
- **`main`** tracks the latest published release. It is fast-forwarded to the released commit by the `sync-main` job of the `CI-CD` workflow after the GitHub release was created, so `main` and the newest release always agree. Nothing is developed on `main` and nothing is merged into it by hand. The first release creates `main`; there is no PyPI package, PK-DB is deployed as a docker image, see [Deployment](deployment.md).

Work happens on short lived branches off `develop`, which GitHub deletes after the merge. Releases are tagged on `develop`, see [Release](#release).

## Pull requests

Neither branch accepts a direct push, every change goes through a pull request against `develop`. This includes the maintainer, there is no bypass.

A pull request can only be merged once the four required checks are green:

| check | workflow | content |
| --- | --- | --- |
| `tests` | `ci-cd.yml` | aggregates `test` (`tox -e py3.9` against services, see below) and `docker` (builds the backend image) |
| `ruff` | `ruff.yml` | `ruff check` and `ruff format --check` |
| `ty` | `ty.yml` | `ty check` of the backend |
| `docs` | `docs.yml` | the zensical build and the agent facing files |

`tests` aggregates the test matrix into a single job, so the name of the required check stays the same when the matrix changes.

Further rules of a pull request:

- conversations have to be resolved before the merge
- an approval is dismissed when new commits are pushed
- the history stays linear, i.e. a pull request is merged with squash or rebase; merge commits are disabled
- the maintainer is the code owner of the repository (`.github/CODEOWNERS`) and is requested for review on every pull request

### Repository policies { #repository-policies }

The protection is implemented with [repository rulesets](https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets). They are part of the repository in `.github/rulesets/` instead of only living in the web interface, so a change to a policy is reviewed like any other change:

| ruleset | applies to | rules |
| --- | --- | --- |
| `develop.json` | `develop` | pull request required, the four checks above, resolved conversations, linear history, no force push, no deletion. No bypass. |
| `main.json` | `main` | no force push, no deletion, no bypass |
| `tags.json` | tags matching `v*` | a release tag cannot be deleted or moved |

Changing a policy means changing the json and applying it:

```bash
.github/rulesets/apply.sh
```

The script is idempotent: it updates the rulesets which exist and creates the missing ones. It also sets the merge settings of the repository (auto-merge, delete branch on merge, squash and rebase as the only merge methods). It needs the [GitHub CLI](https://cli.github.com) authenticated as a user with admin permission on the repository.

## Setup development environment

Development needs [uv](https://docs.astral.sh/uv/) and a checkout of the repository. The backend is its own uv project in `backend/`:

```bash
git clone https://github.com/matthiaskoenig/pkdb.git
cd pkdb/backend
uv sync --extra dev
```

The `dev` extra adds pytest, ruff, ty, tox and pre-commit. The tools are then run either with `uv run <command>` from `backend/`, or from the activated environment:

```bash
source .venv/bin/activate        # Linux and macOS
.venv\Scripts\activate           # Windows
```

Install the git hook from the repository root:

```bash
uv run --project backend pre-commit install          # once per checkout
uv run --project backend pre-commit run --all-files  # check the current state of the repository
```

From now on every commit is checked with the pre-commit hooks (whitespace and file checks, ruff lint and format, and `ty` on `backend/`). A commit only checks the changed files; `--all-files` checks the whole repository.

## Testing

The tests need a running postgres and elasticsearch, provided by `docker-compose-test.yml` in the repository root - fixed ports `5434` (postgres) and `9124` (elasticsearch), no named volumes, so a `search_index --rebuild` against them never touches the data of the develop stack (`docker-compose-develop.yml`, ports `5433`/`9123`). Start and stop them with:

```bash
docker compose -f docker-compose-test.yml up -d --wait
docker compose -f docker-compose-test.yml down
```

`[tool.pytest_env]` in `backend/pyproject.toml` fills in the `PKDB_*` variables the settings module needs with defaults matching these services (`skip_if_set = true`, so a variable already exported, e.g. in CI, wins). Run the tests from `backend/`:

```bash
cd backend
uv run pytest -q
```

or through tox, which additionally checks types:

```bash
uv run tox -e py3.9    # the tests
uv run tox -e ty       # the type check
```

Continuous integration creates the migrations first (`python manage.py makemigrations`, since migrations are gitignored, see [Migrations](#migrations) below) and then runs `uv run tox -e py3.9`.

Write requests of the REST API need an authenticated user; read the docstrings in `backend/pkdb_app/users/permissions.py` for how access is granted per study role if a test needs to authenticate.

## Migrations { #migrations }

Migrations (`*/migrations/*.py`) are gitignored and generated per deployment; `docker-purge.sh` runs `makemigrations` and `migrate` as part of resetting a stack, and CI runs `makemigrations` before the tests. `backend/` is bind mounted into the running development container `pkdb-backend-1` (see [Installation](installation.md)): never run `manage.py makemigrations` in a checkout whose `backend/` is bind mounted into a running development container unless you mean to change that stack. The tests use the migration files already present in your checkout, generated locally with `uv run python manage.py makemigrations` from `backend/` if none exist yet.

## Linting and formatting

Linting and formatting use [ruff](https://docs.astral.sh/ruff/), configured in `.ruff.toml` in the repository root, run from there so its excludes apply (`frontend/`, `docs/`, `**/migrations/**`, `superpowers/`):

```bash
uv run --project backend ruff check .
uv run --project backend ruff format .
```

`scripts/*.py` is checked against python 3.14 (`[per-file-target-version]`), since it runs with `uv run --no-project --python 3.14`, not with the backend's python 3.9.

## Type checking

Type checking is performed with [ty](https://docs.astral.sh/ty/), from `backend/`:

```bash
uv run ty check
```

The configuration is `[tool.ty]` in `backend/pyproject.toml`; `[tool.ty.src] include` lists `pkdb_app`, `tests` and `manage.py`, migrations are excluded. Warnings are treated as errors (`error-on-warning = true`).

## Documentation

The documentation is built with [Zensical](https://zensical.org/). The sources are markdown files in `docs/`, configured in `zensical.toml` in the repository root. The backend is on python 3.9, which zensical does not support, so the documentation is built standalone with `uvx` and python 3.14, against `docs/requirements.txt` rather than the backend's own environment:

```bash
uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean
```

For writing, the preview rebuilds on save:

```bash
uvx --python 3.14 --with-requirements docs/requirements.txt zensical serve
```

Nothing rendered is committed: the site is built into the gitignored `site/` by the `documentation` workflow on every push and pull request, and published to [matthiaskoenig.github.io/pkdb](https://matthiaskoenig.github.io/pkdb) from `develop`.

### Files for agents { #files-for-agents }

Agents and language models read markdown, not rendered html. `scripts/llms_txt.py` writes the files of the [llms.txt convention](https://llmstxt.org/) into the built site, i.e. [llms.txt](https://matthiaskoenig.github.io/pkdb/llms.txt) as an annotated index of all pages, [llms-full.txt](https://matthiaskoenig.github.io/pkdb/llms-full.txt) with the complete documentation in a single file, and the markdown of every page next to its html (`/installation.md` for `/installation/`):

```bash
uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean
uv run --no-project --python 3.14 python scripts/llms_txt.py
```

The `documentation` workflow runs both steps. `docs/robots.txt` points crawlers at the sitemap and at these files.

## Continuous integration

Four workflows run on every pull request against `develop` and on every push to `develop` and `main`, see `.github/workflows/`. Their required jobs `tests`, `ruff`, `ty` and `docs` are the [checks](#pull-requests) of a pull request:

| workflow | what it does |
| --- | --- |
| `ci-cd` (`ci-cd.yml`) | `test` runs `tox -e py3.9` against postgres and elasticsearch services, `docker` builds the backend image; on a tag it also creates the GitHub release and fast-forwards `main` |
| `ruff` (`ruff.yml`) | lint and format check |
| `ty` (`ty.yml`) | the type check |
| `documentation` (`docs.yml`) | builds the site and the agent facing files, publishes from `develop` |

## Release

There is no PyPI package; a release is a docker image built from the tagged commit. A release is a tag `v<version>` (e.g. `v0.10.0`) on `develop` with its GitHub release, created from `release-notes/<version>.md` (without the leading `v`):

1. write the release notes for the version in `release-notes/<version>.md`
2. make sure everything passes: `uv run --project backend pre-commit run --all-files`, `uv run tox -e py3.9`, `uv run tox -e ty`
3. bump the version in `backend/pkdb_app/__init__.py` and `.bumpversion.toml`, on a branch, merged through a pull request like any other change
4. tag the merged commit on `develop` and push the tag:

    ```bash
    git switch develop
    git pull
    git tag v<version>
    git push origin v<version>
    ```

    This starts the `CI-CD` workflow, which runs the tests, creates the GitHub release from `release-notes/<version>.md` and fast-forwards `main` to the tagged commit (the first release creates `main`). Check the version before pushing, a tag cannot be moved or deleted afterwards.
