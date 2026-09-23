# Development

Installation and development instructions are now combined in [Local setup and development](installation.md), including the two-command backend/frontend startup, user import, tests, migrations, and documentation builds.

## Python package releases

The public `pkdb` package and `pkdb-server` use the same version and release tag. Bump versions with the repository's bump-my-version configuration, commit the generated lock updates, and release through a `vVERSION` tag. The server wheel pins `pkdb==VERSION`; it is distributed as a GitHub release asset alongside the public wheel and source archive.

After all backend, frontend, container, and Python client checks pass, `.github/workflows/ci-cd.yml` publishes only the public `pkdb` wheel and source archive to PyPI. The workflow verifies that both filenames match the release tag. The GitHub release and `main` synchronization wait for successful PyPI publication. Publishing uses short-lived GitHub OIDC credentials, with no stored PyPI API token.

Before the first tagged release, a maintainer must complete this one-time setup:

1. Check ownership and availability of the PyPI project name `pkdb`. Its public metadata API returned HTTP 404 on 2026-09-23; this does not reserve the name or guarantee that PyPI will allow registration. If the project already exists by release time, its owner must grant the appropriate project role and configure its publisher.
2. Create the GitHub repository environment named `pypi` and restrict deployment to release tags according to the repository's release policy.
3. Configure a [PyPI Trusted Publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/) for the project. For a new project, use PyPI's [pending publisher registration](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/). Enter PyPI project name `pkdb`, GitHub owner `matthiaskoenig`, repository `pkdb`, workflow filename `ci-cd.yml`, and environment `pypi`.

The workflow uses the official [PyPA publishing action](https://github.com/pypa/gh-action-pypi-publish) in a dedicated job with `id-token: write`. The setup above is external account configuration; adding the workflow does not create the PyPI project or grant publishing access.
