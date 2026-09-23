# Development

!!! important "For developers and operators only"

    This section is for working on PK-DB itself or running a separate server. General users do not need a source checkout, Docker, a database, or administrator access. To use PK-DB, start with [Browse and access data](web-interface.md) or the [Python client and API](python-client.md).

## Choose a development workflow

- [Local setup and development server](installation.md): run the frontend, backend, and PostgreSQL, load studies, and run checks.
- [Local upload testing](local-upload-testing.md): exercise ingestion against your own server.
- [Account administration](administration.md): provision test accounts and manage curator imports.
- [Vocabulary definitions](vocabulary.md): edit and regenerate the server vocabulary.
- [Deployment](deployment.md): configure an externally accessible server and backups.

## Install the Python package from source

For normal use, install [pkdb from PyPI](https://pypi.org/project/pkdb/). Use a source checkout when changing the library or testing unreleased behavior:

```bash
git clone --branch develop https://github.com/matthiaskoenig/pkdb.git
cd pkdb
uv sync --project python --locked --python 3.14
uv run --project python pkdb --help
uv run --project python pytest python/tests -q
```

`uv sync` installs the local package in editable mode and includes its development dependencies. For an existing virtual environment, use `python -m pip install -e /absolute/path/to/pkdb/python`. To use this checkout as a standalone CLI, run `uv tool install --editable ./python`; to add it to another uv project, run `uv add --editable /absolute/path/to/pkdb/python` from that project.

The backend is a separate source package. From the repository root:

```bash
uv sync --project backend --locked --python 3.14
uv run --project backend pre-commit install
```

The backend environment uses the sibling `python/` package in editable mode. Python 3.15 is also supported; pass `--python 3.15` consistently when syncing and running that environment. See [runtime compatibility](installation.md#backend-tests-and-checks) for its current prerelease dependencies.

## Work with the development server

Follow [Local setup](installation.md#quick-start) to start the stack. Its accounts, studies, and API keys are separate from those on the public website. Point scripts at your local endpoint:

```bash
export PKDB_ENDPOINT=http://localhost:18083
uv run --project python pkdb vocabulary sync --endpoint "$PKDB_ENDPOINT" --output /tmp/pkdb-vocabulary.json
```

For authenticated operations, use a key from your **local** account in `PKDB_API_KEY`. Frontend edits reload automatically in the Docker development profile; rebuild the backend image after server changes. Native backend reload instructions are in [Local setup](installation.md#native-backend-server).

## Branches, checks, and review

Start a topic branch from an up-to-date `develop`, make the change, and run the relevant tests. Pre-commit runs formatting, lint, and type checks on applicable files. Push the topic branch and open a pull request against `develop`; merge after `tests`, `ruff`, `ty`, and `docs` pass. Source code, migrations, and documentation belong in the repository; credentials, local databases, attachments, and generated caches do not.

Keep Markdown prose paragraphs on one source line, using editor soft wrapping. See [Local setup](installation.md) for frontend/backend checks, migrations, and documentation builds.

## Continuous integration

Pull requests, branch pushes, and manual runs test the backend and public Python client on Linux with Python 3.14. Release tag pushes (`v*`) expand backend checks to Python 3.14 and 3.15 and test the client on Linux, macOS, and Windows with both versions. Frontend, container, documentation, lint, and type checks still run for ordinary changes.

## Python package releases

The public `pkdb` package and `pkdb-server` use the same version and release tag. Bump versions with the repository's bump-my-version configuration, commit the generated lock updates, and release through a `vVERSION` tag. The server wheel pins `pkdb==VERSION`; it is distributed as a GitHub release asset alongside the public wheel and source archive.

After all backend, frontend, container, and Python client checks pass, `.github/workflows/ci-cd.yml` publishes only the public `pkdb` wheel and source archive to PyPI. The workflow verifies that both filenames match the release tag. The GitHub release and `main` synchronization wait for successful PyPI publication. Publishing uses short-lived GitHub OIDC credentials, with no stored PyPI API token.

Maintainers manage the following publishing configuration:

1. Ensure the maintainer has the appropriate role on the [pkdb PyPI project](https://pypi.org/project/pkdb/) and can configure its trusted publisher.
2. Create the GitHub repository environment named `pypi` and restrict deployment to release tags according to the repository's release policy.
3. Configure a [PyPI Trusted Publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/) for the project. For a new project, use PyPI's [pending publisher registration](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/). Enter PyPI project name `pkdb`, GitHub owner `matthiaskoenig`, repository `pkdb`, workflow filename `ci-cd.yml`, and environment `pypi`.

The workflow uses the official [PyPA publishing action](https://github.com/pypa/gh-action-pypi-publish) in a dedicated job with `id-token: write`. The setup above is external account configuration; adding the workflow does not create the PyPI project or grant publishing access.
