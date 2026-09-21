# Contributing

This page describes step by step how a change gets into the repository. The rules behind it are in [Development](development.md).

The short version: nobody pushes to `develop` directly. Every change is made on a branch, pushed, and merged through a pull request once the four checks `tests`, `ruff`, `ty` and `docs` are green.

## Once: update an existing clone { #update-an-existing-clone }

`develop` was already the default branch; a clone which still tracks `master` is updated once with:

```bash
git switch develop
git branch -D master
git fetch --prune origin
```

Then sync the backend environment and install the git hook:

```bash
cd backend && uv sync --extra dev && cd ..
uv run --project backend pre-commit install
```

A fresh clone needs only the second block, see [Installation](installation.md).

## 1. Create a branch

Start every piece of work from the current `develop`:

```bash
git switch develop
git pull
git switch -c fix-elasticsearch-host
```

Name the branch after the change. Keep a branch small and short lived: one topic per branch, merged within days. Small branches are reviewed faster and rarely conflict.

## 2. Work and commit

Commit as usual. The git hook checks the changed files on every commit:

- files larger than 2 MB, merge conflict markers and private keys are rejected everywhere
- python files under `backend/` are linted and formatted with ruff and type checked with ty

If the hook changed a file, e.g. ruff formatted it, add the file again and repeat the commit.

Run the focused test for what you changed:

```bash
cd backend
uv run pytest -k <keyword> -q
```

## 3. Push and open the pull request

```bash
git push -u origin fix-elasticsearch-host
```

Open the pull request against `develop`, either with the link git prints after the push or on the GitHub page of the repository. Fill in the template. The maintainer is requested as reviewer automatically.

## 4. Get the checks green

| check | what it runs | run it locally |
| --- | --- | --- |
| `tests` | the backend tests against postgres and elasticsearch, and the docker build | `cd backend && uv run tox -e py3.9` |
| `ruff` | lint and format of `backend/` | `uv run --project backend ruff check .`, `uv run --project backend ruff format --check .` |
| `ty` | type check of `backend/` | `cd backend && uv run ty check` |
| `docs` | build of this documentation | `uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean` |

A red check shows the reason in its log on the pull request page ("Details"). Fix it locally, commit and push to the same branch; the pull request updates itself and the checks run again.

The most common cases:

- **`tests` fails.** Start the test services if they are not running (`docker compose -f docker-compose-test.yml up -d --wait`) and run `cd backend && uv run pytest -q` to see the failure directly.
- **`ruff` fails.** Run `uv run --project backend ruff check --fix .`, fix what remains by hand, and `uv run --project backend ruff format .`; commit the result.
- **`ty` fails.** Run `cd backend && uv run ty check` and fix the diagnostic, or suppress an unavoidable one with a rule specific `# ty: ignore[rule-name]`.

## 5. Merge

When the checks are green and all review comments are resolved the pull request is merged with "Squash and merge" or "Rebase and merge". GitHub deletes the branch afterwards. Locally:

```bash
git switch develop
git pull
git branch -D fix-elasticsearch-host
```

`-D` instead of `-d`: after a squash or rebase merge the commits on `develop` are new ones, so git does not recognize the local branch as merged.

## Update a branch

If `develop` moved on while you worked, bring the changes into your branch:

```bash
git fetch origin
git rebase origin/develop
git push --force-with-lease
```

`--force-with-lease` is needed because the rebase rewrites the commits of your branch; it only overwrites your own branch and refuses if somebody else pushed to it in the meantime. On a conflict git stops and names the files: edit them, `git add` them and continue with `git rebase --continue`. `git rebase --abort` returns to the state before the rebase.

If you are not comfortable with a rebase, the button "Update branch" on the pull request page does the same on GitHub; run `git pull` afterwards.

## What does not belong in a commit

- credentials: the deployment env files (`.env`, `.env.develop`, `.env.production`, `.env.alpha`) are gitignored; `.env.local` in the repository holds development values only
- generated migrations: `*/migrations/` under `backend/` is gitignored, see [Migrations](development.md#migrations)
- files above 2 MB are rejected by the git hook
