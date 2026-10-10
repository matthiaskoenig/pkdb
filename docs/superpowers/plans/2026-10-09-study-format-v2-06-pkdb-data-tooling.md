---
search:
  exclude: true
---

# pkdb_data tooling for study format 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `pkdb check` checks the format 2 studies of a pkdb_data checkout (canonical form, offline validation with a pinned vocabulary, tracked workbooks, repository-wide identifiers and issue numbers), and pkdb_data runs it in pre-commit and a required CI check, keeps its GitHub issues in sync, refreshes its vocabulary lock, and documents the format 2 workflow for curators and AI agents.

**Architecture:** In pkdb, a new module `python/src/pkdb/checks.py` selects study folders (paths, staged files, or changes since a base), runs the existing format check, validation and registry checks on them without writing or contacting the network, and `python/src/pkdb/checks_cli.py` exposes it as `pkdb check`. In pkdb_data, plain files carry the rest: `.gitignore`, `.gitattributes`, the pins `requirements/pkdb.txt` and `vocabulary.lock.json`, a pre-commit hook and three GitHub Actions workflows (`studies`, `issues`, `vocabulary`), the format 2 curation guide, `AGENTS.md`, a Claude skill and the maintainer documentation.

**Tech Stack:** Python 3.14, argparse, git (subprocess), pytest, ruff, ty (pkdb); pre-commit, GitHub Actions (`actions/checkout` partial clone and sparse checkout, `astral-sh/setup-uv`), Dependabot, Zensical (pkdb_data).

**Spec:** `docs/superpowers/specs/2026-10-09-study-format-v2-06-pkdb-data-tooling-design.md`, and `docs/superpowers/specs/2026-10-05-study-format-v2-design.md` sections 13 and 14.

## Global Constraints

- **pkdb (Tasks 1-2):** branch `feature/study-format-v2-11` in `/home/mkoenig/git/pkdb` (stacked on part C, PR #880). Python 3.14. From `python/`: `uv run --locked pytest -q -x`, `uv run --locked ruff check .`, `uv run --locked ruff format --check .`, `uv run --locked ty check`. Docs: `uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean` from the repository root, no warning.
- **pkdb_data (Tasks 3-7):** a separate git worktree `/home/mkoenig/git/pkdb_data-tooling` of `/home/mkoenig/git/pkdb_data` on a new branch `feature/study-format-2-tooling` from `origin/develop`. Never change, stash or switch the user's checkout `/home/mkoenig/git/pkdb_data` (it is on `merge-final` with other work). Follow `/home/mkoenig/git/pkdb_data/CLAUDE.md`: never read, search or bulk-process all of `studies/`; no Python package or application dependencies (the pkdb pin is a tool pin); docs build with `uvx --from "$(cat docs/requirements.txt)" zensical build --clean --strict`.
- **Both repositories:** never use the em dash character; Markdown paragraphs on one source line; no attribution lines anywhere (no "Co-Authored-By", no "Generated with ..."); never hand-edit generated files (`docs/study-format.md`, `CHANGELOG.md`); user-facing text in plain, short English sentences.
- **No outward actions without the user:** never push, open pull requests, publish to PyPI, change GitHub settings, rulesets, secrets or variables. Tasks prepare files and dry runs; the controller asks the user for each outward step.
- **Spec values:** `pkdb check [PATH...] [--staged | --changed BASE] [--root PATH] [--vocabulary FILE] [--format human|json]`; vocabulary order `--vocabulary`, then `<root>/vocabulary.lock.json`, then bundled; exit 0 clean, 1 problems, 2 usage; `.gitignore` adds `.*.pkdb-base` now and `studies/**/*.xlsx` only in the cutover PR; `.gitattributes` `*.tsv text eol=lf`, `*.json text eol=lf`, `*.pdf binary`, `*.png binary`, `*.jpg binary`, `*.xlsx binary`; `requirements/pkdb.txt` pins `pkdb==0.12.0` (the first release with `pkdb check`; the user decides the release); `vocabulary.lock.json` at the pkdb_data root; workflows `studies` (required check on `develop`), `issues`, `vocabulary`; agents commit with the responsible curator's identity and the trailer `Agent: <model>`.

## Review Focus

1. **A staged rename or deletion of a whole study** (a curator runs `pkdb move` or removes a study): `pkdb check --staged` checks the study at its new place, skips the deleted one, and never fails on a path that no longer exists. Test in Task 1 (`test_a_moved_and_a_deleted_study_are_handled`).
2. **A path with spaces or non-ASCII characters** (a few pkdb_data folders have spaces, such as `Bayer Study_11651`; reference names have umlauts): selection from `git diff` must use NUL-separated output, never split on whitespace. Test in Task 1 (`test_paths_with_spaces_and_umlauts_are_selected`).
3. **Running outside a git repository or with an unknown base** (`pkdb check --changed origin/develop` in a shallow clone, or `--staged` in a plain folder): a clear usage error (exit 2) instead of a traceback. Test in Task 1 (`test_git_problems_are_usage_errors`).
4. **The CI checkout of a 7.9 GB repository**: the `studies` workflow must never fetch all blobs; it clones without blobs and checks out only `study.json` files and changed study folders. Checked in Task 5 by a dry run of the workflow's shell steps on a local partial clone (`git clone --filter=blob:none`), measuring that no study PDFs or PNGs outside the changed folders are fetched.
5. **The pre-commit hook on a commit without study files or with only format 1 studies** (curators keep working in format 1 until the cutover): the hook does not run or passes quickly, without network access. Test in Task 4 by running `pre-commit run pkdb-check` on staged format 1 and docs-only changes in the worktree.

---

## File Structure

| File | Responsibility |
|---|---|
| `python/src/pkdb/checks.py` (pkdb) | Study selection from paths, staged files or a base; per-study checks; repository checks; `CheckReport`. |
| `python/src/pkdb/checks_cli.py` (pkdb) | `pkdb check` command. |
| `python/src/pkdb/cli.py` (pkdb) | Register and dispatch `check`. |
| `docs/python-client.md`, `docs/study-format-2-cutover.md`, main spec (pkdb) | Command docs, runbook steps, spec record. |
| `.gitignore`, `.gitattributes` (pkdb_data) | Ignore rules and line ends. |
| `requirements/pkdb.txt`, `vocabulary.lock.json` (pkdb_data) | Pins. |
| `.pre-commit-config.yaml` (pkdb_data) | Generic hooks with their own excludes, `pkdb check --staged`, `actionlint`. |
| `.github/workflows/studies.yml`, `issues.yml`, `vocabulary.yml`, `.github/dependabot.yml`, `.github/rulesets/develop.json` (pkdb_data) | CI and automation. |
| `docs/curation-v2.md`, `docs/development.md`, `AGENTS.md`, `.claude/skills/pkdb-curation/SKILL.md`, `CLAUDE.md`, `zensical.toml` (pkdb_data) | Documentation and agent instructions. |

---

### Task 1: The check engine (`pkdb.checks`)

**Files:**
- Create: `python/src/pkdb/checks.py`, `python/tests/test_checks.py`

**Interfaces:**
- Consumes: `pkdb.repository` (`repository_root`, `location`, `STUDIES`); `pkdb.preparation.study_folders(path)` (skips hidden folders); `pkdb.studyformat.validation.is_v2_folder`, `validate_folder(folder, vocabulary)`; `pkdb.studyformat.formatter.format_folder(folder, check=True) -> FormatResult(changes, issues, ok)`; `pkdb.cache.select_vocabulary(path, endpoint, cache)` (with `endpoint=None` it never contacts a server), `VocabularyCache`; `pkdb.lifecycle.registry` (`scan(root)`, `duplicates(scan)`, `registry_problems(scan, root)`); `pkdb.studyformat.workbook.base` (`workbook_path`, `state_path`).
- Produces (all in `pkdb.checks`):
  - `CheckError(ValueError)`: a usage problem (not a git repository, unknown base, a path outside the checkout).
  - `Problem` (Pydantic, `extra="forbid"`): `study: str | None` (location, None for repository problems), `code: str`, `message: str`, `file: str | None = None`, `row: int | None = None`, `severity: Literal["error", "warning"] = "error"`.
  - `CheckReport` (Pydantic): `checked: list[str]` (locations), `format_1: int`, `deleted: list[str]`, `problems: list[Problem]`; property `ok` (no problem with severity error).
  - `select(root: Path, *, paths: list[Path] = [], staged: bool = False, changed: str | None = None) -> tuple[list[Path], list[str]]`: the existing study folders to check and the locations of deleted studies.
  - `vocabulary_for(root: Path, path: Path | None)`: `--vocabulary`, else `root/vocabulary.lock.json` when it exists, else bundled (through `select_vocabulary(path, None, VocabularyCache())`).
  - `check(root: Path, folders: list[Path], vocabulary) -> CheckReport`.

Behavior:
- `select`: with `paths`, every study folder found by `study_folders(path)` for each path (a path outside `root/studies` is a `CheckError`). With `staged`, `git -C root diff --cached --name-only -z --diff-filter=ACMRD` (NUL separated); with `changed`, `git -C root diff --name-only -z --diff-filter=ACMRD <changed>...HEAD`. Each path `studies/<substance>/<name>/...` gives the folder `root/studies/<substance>/<name>`; a folder that no longer exists is a deleted study (its location goes to the second list), others are kept once. Without `paths`, `staged` or `changed`: every study folder of `root/studies` (`study_folders(root / STUDIES)`). A failing git command (not a repository, unknown revision) is a `CheckError` with git's first error line. Hidden folders are never selected.
- `check`: for each folder, skip and count format 1 (`not is_v2_folder`). For format 2: `format_folder(folder, check=True)`: each planned change is a problem `code="not_canonical"`, `file=<change file>`, message "`<file>` is not in canonical form; run pkdb format"; its error issues become problems with their code, message, file and row. `validate_folder(folder, vocabulary)`: errors and warnings become problems with their severity. Tracked or staged workbook: when `git -C root ls-files --cached -z -- <workbook> <state file>` lists either, a problem `code="workbook_tracked"` ("The workbook <name>.xlsx is generated; remove it from git with git rm --cached"). Then the repository checks once: `scan(root)`, `duplicates(scan)`, `scan.errors`, `registry_problems(scan, root)` become problems with `study=None` and codes `duplicate_identifier`, `unreadable_study`, `registry_file`.
- Never writes a file and never contacts the network.

- [ ] **Step 1: Write the failing tests** `python/tests/test_checks.py`. Build throwaway repositories with `git init` in `tmp_path` (set `user.name`/`user.email` with `git -c` in a helper, never globally), studies from the `valid_files` fixture of `python/tests/conftest.py` written to `studies/<substance>/<name>/` and formatted with `format_folder`, and format 1 studies as a `study.json` with `"sid"` (see `python/tests/lifecycle_fixtures.py` and `python/tests/migration_fixtures.py` for builders):

```python
import json
import subprocess

import pytest

from pkdb.checks import CheckError, check, select, vocabulary_for


def git(root, *args):
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.org", *args], check=True, capture_output=True)


def test_staged_files_select_their_studies(checkout):
    root, studies = checkout("caffeine/A", "caffeine/B", "codeine/C")
    (studies["caffeine/A"] / "subjects.tsv").write_text((studies["caffeine/A"] / "subjects.tsv").read_text() + "", encoding="utf-8")
    (studies["codeine/C"] / "notes.txt").write_text("x", encoding="utf-8")
    git(root, "add", "studies/codeine/C/notes.txt")
    folders, deleted = select(root, staged=True)
    assert [f.name for f in folders] == ["C"] and deleted == []


def test_changes_since_a_base_select_their_studies(checkout):
    root, studies = checkout("caffeine/A", "caffeine/B")
    git(root, "tag", "base")
    (studies["caffeine/B"] / "notes.txt").write_text("x", encoding="utf-8")
    git(root, "add", "-A"); git(root, "commit", "-m", "change B")
    folders, _ = select(root, changed="base")
    assert [f.name for f in folders] == ["B"]


def test_a_moved_and_a_deleted_study_are_handled(checkout):
    root, studies = checkout("caffeine/A", "caffeine/B")
    git(root, "mv", "studies/caffeine/A", "studies/caffeine/A2")
    git(root, "rm", "-r", "-q", "studies/caffeine/B")
    folders, deleted = select(root, staged=True)
    assert [f.name for f in folders] == ["A2"]
    assert sorted(deleted) == ["caffeine/A", "caffeine/B"]


def test_paths_with_spaces_and_umlauts_are_selected(checkout):
    root, studies = checkout("caffeine/Bayer Study_1", "caffeine/Jönsson2015")
    for folder in studies.values():
        (folder / "notes.txt").write_text("x", encoding="utf-8")
    git(root, "add", "-A")
    folders, _ = select(root, staged=True)
    assert sorted(f.name for f in folders) == ["Bayer Study_1", "Jönsson2015"]


def test_git_problems_are_usage_errors(tmp_path, checkout):
    with pytest.raises(CheckError, match="git"):
        select(tmp_path, staged=True)
    root, _ = checkout("caffeine/A")
    with pytest.raises(CheckError, match="nosuchbase"):
        select(root, changed="nosuchbase")


def test_a_valid_format_2_study_passes_and_format_1_is_skipped(checkout, sf_vocabulary):
    root, studies = checkout("caffeine/A", format_1=["caffeine/Old"])
    report = check(root, [studies["caffeine/A"], root / "studies" / "caffeine" / "Old"], sf_vocabulary)
    assert report.ok and report.checked == ["caffeine/A"] and report.format_1 == 1


def test_problems_of_form_validation_workbooks_and_the_repository(checkout, sf_vocabulary):
    root, studies = checkout("caffeine/A", "caffeine/B")
    folder = studies["caffeine/A"]
    (folder / "subjects.tsv").write_text((folder / "subjects.tsv").read_text(encoding="utf-8").replace("\t", "\t ", 1), encoding="utf-8")
    (folder / "Example.xlsx").write_bytes(b"x")
    git(root, "add", "-f", "studies/caffeine/A/Example.xlsx")
    metadata = json.loads((studies["caffeine/B"] / "study.json").read_text(encoding="utf-8"))
    report = check(root, [folder, studies["caffeine/B"]], sf_vocabulary)
    codes = {(p.study, p.code) for p in report.problems}
    assert ("caffeine/A", "not_canonical") in codes
    assert not report.ok


def test_vocabulary_lock_is_used_when_present(tmp_path):
    ...  # write vocabulary.lock.json with a recognizable version (snapshot.save of a small Vocabulary) and assert vocabulary_for(root, None).version; without it the bundled vocabulary; an explicit path wins
```

Write the elided test fully, and add: a workbook named after the study and its state file tracked gives `workbook_tracked`; two studies with one `issue` give a repository problem with `study=None`; validation warnings keep `report.ok` true; nothing in the repository changes (compare `git status --porcelain` before and after `check`); no network (monkeypatch `pkdb.client.Client` and `httpx2` transports to raise). Define the `checkout(*locations, format_1=())` fixture in the test file: `git init`, the studies, `git add -A`, a first commit, returns `(root, {location: folder})`. The name of the study files must follow the folder (format the study after writing it under its location, since `format_folder` writes the `study` column from the folder name). Adapt helper lines, not the meaning of the assertions.

- [ ] **Step 2: Run to verify they fail**: `uv run --locked pytest -q tests/test_checks.py` -> FAIL, module not found.

- [ ] **Step 3: Implement** `python/src/pkdb/checks.py` with the behavior above: one `_git(root, *args) -> bytes` helper (`subprocess.run([...], capture_output=True)`; a non-zero exit or a missing `git` raises `CheckError` with the first line of stderr), NUL-split decoding as UTF-8 with `surrogateescape`, small functions `_study_of(path)`, `_form_problems`, `_validation_problems`, `_workbook_problems`, `_repository_problems`, each with a docstring.

- [ ] **Step 4: Run** `uv run --locked pytest -q tests/test_checks.py` -> PASS; full suite, ruff, ty.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/checks.py python/tests/test_checks.py
git commit -m "Check the format 2 studies of a pkdb_data checkout"
```

---

### Task 2: `pkdb check`, its documentation and the spec record

**Files:**
- Create: `python/src/pkdb/checks_cli.py`, `python/tests/test_checks_cli.py`
- Modify: `python/src/pkdb/cli.py` (import tuple, `register`, dispatch), `python/tests/test_cli.py` (help test), `docs/python-client.md` (command table and a section "Check a pkdb_data checkout"), `docs/study-format-2-cutover.md` (two steps), `docs/superpowers/specs/2026-10-05-study-format-v2-design.md` (sections 13 and 14), `release-notes/unreleased.md` only after the PR exists (controller)

**Interfaces:**
- Consumes: Task 1 `select`, `check`, `vocabulary_for`, `CheckError`, `CheckReport`; `pkdb.repository.repository_root`; `study_cli.add_format`, `is_human`, `emit`.
- Produces: `checks_cli.register(commands)`, `checks_cli.run(args) -> int`.

Command: `pkdb check [PATH...] [--staged | --changed BASE] [--root PATH] [--vocabulary FILE] [--format human|json]`. `--root` defaults to `repository_root(first PATH or the current folder)`. `--staged` and `--changed` exclude each other and paths (argparse mutually exclusive group plus a check). Human output: one line per problem `caffeine/A subjects.tsv:3 not_canonical: ...` (repository problems without a study), then `Checked N format 2 studies, skipped M format 1 studies: K errors, W warnings.` JSON: `CheckReport.model_dump(mode="json")`. Exit 0 when `report.ok`, 1 otherwise, 2 for `CheckError`, `ValueError` (no checkout) and argparse errors. Lazy imports inside `run`; `PKDB_NO_UPDATE` is honored by `pkdb` already.

- [ ] **Step 1: Write the failing CLI tests** in `python/tests/test_checks_cli.py` (reuse the `checkout` builder of Task 1 by moving it into a top-level helper `python/tests/check_fixtures.py`, importable as `from check_fixtures import checkout_factory`): a clean checkout exits 0 with the summary line; a not canonical study exits 1 and names the file; `--staged` with nothing staged exits 0 and checks nothing; `--staged --changed x` exits 2; outside a git repository with `--staged` exits 2 with a message naming git; `--format json` output parses and has `checked`, `format_1`, `problems`. Add `check` to the command list of the help test in `python/tests/test_cli.py`.

- [ ] **Step 2: Run to verify they fail**: `uv run --locked pytest -q tests/test_checks_cli.py tests/test_cli.py` -> FAIL.

- [ ] **Step 3: Implement** `checks_cli.py`, register it in `cli.py` (`checks_cli.register(commands)`; `if args.command == "check": return checks_cli.run(args)`).

Docs:
- `docs/python-client.md`: command table row `| pkdb check [PATH...] [--staged \| --changed BASE] | Check the format 2 studies of a pkdb_data checkout: canonical form, offline validation, tracked workbooks, shared identifiers and issue numbers |`, and a section "Check a pkdb_data checkout": what it checks, the vocabulary order (`--vocabulary`, `vocabulary.lock.json` at the checkout root, bundled), that it never writes and never contacts the server, that format 1 studies are skipped, how pre-commit (`--staged`) and CI (`--changed`) use it, exit codes.
- `docs/study-format-2-cutover.md`: in the migration pull request step, add "add `studies/**/*.xlsx` to `.gitignore` (format 2 workbooks are generated)" and "rename `docs/curation-v2.md` to `docs/curation_guide.md`, archive the format 1 guide as `docs/curation-guide-format-1.md`, and update the navigation".
- Main spec section 13: step 5 says agents commit with the responsible curator's git identity and the trailer `Agent: <model>`; section 14: pre-commit runs `pkdb check --staged`, CI runs `pkdb check --changed <base>` with `vocabulary.lock.json`, and `.gitignore` gets `studies/**/*.xlsx` at the cutover, `.*.pkdb-base` before.

Build the docs.

- [ ] **Step 4: Run** `uv run --locked pytest -q tests/test_checks.py tests/test_checks_cli.py tests/test_cli.py` -> PASS; full suite, ruff, ty, docs build.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/checks_cli.py python/src/pkdb/cli.py python/tests/test_checks_cli.py python/tests/check_fixtures.py python/tests/test_checks.py python/tests/test_cli.py docs/python-client.md docs/study-format-2-cutover.md docs/superpowers/specs/2026-10-05-study-format-v2-design.md
git commit -m "Add pkdb check for pre-commit and CI of pkdb_data"
```

---

### Task 3: pkdb_data worktree, ignore rules, line ends and pins

**Files (pkdb_data worktree):**
- Modify: `.gitignore`
- Create: `.gitattributes`, `requirements/pkdb.txt`, `vocabulary.lock.json`

**Interfaces:**
- Consumes: the pkdb CLI of Tasks 1-2 (run from `/home/mkoenig/git/pkdb/python` with `uv run --locked pkdb ...` until the release exists).
- Produces: the worktree `/home/mkoenig/git/pkdb_data-tooling` on branch `feature/study-format-2-tooling`; the two pin files used by Tasks 4-6.

- [ ] **Step 1: Create the worktree** (never touch `/home/mkoenig/git/pkdb_data` itself):

```bash
git -C /home/mkoenig/git/pkdb_data fetch origin develop
git -C /home/mkoenig/git/pkdb_data worktree add -b feature/study-format-2-tooling /home/mkoenig/git/pkdb_data-tooling origin/develop
```

The worktree checks out all files of `develop` (several GB on disk, shared object store); if disk space is short, use `git worktree add --no-checkout` followed by a sparse checkout of everything except `studies/` plus `studies/*/*/study.json` (`git sparse-checkout set --no-cone`), and say so in the report.

- [ ] **Step 2: `.gitignore` and `.gitattributes`.** Append to `.gitignore` a commented block: `# Workbook state of pkdb tables (study format 2)` / `.*.pkdb-base`, and a comment that `studies/**/*.xlsx` follows in the cutover pull request. Create `.gitattributes`:

```
# Study format 2 tables and JSON files are canonical text with LF line ends.
*.tsv text eol=lf
*.json text eol=lf
*.pdf binary
*.png binary
*.jpg binary
*.xlsx binary
```

Then measure line ends of tracked TSV and JSON files without reading `studies/` file contents yourself: `git ls-files --eol -- '*.tsv' '*.json' | awk '$1 ~ /crlf/'` (index line ends). If any are listed, renormalize them in a separate commit (`git add --renormalize .` limited to those paths) and list the count and a few paths in the report; if none, say so.

- [ ] **Step 3: Pins.** `requirements/pkdb.txt` with a comment line `# The pkdb release used by pre-commit and CI; Dependabot proposes updates.` and `pkdb==0.12.0`. `vocabulary.lock.json`: try `uv run --locked pkdb vocabulary sync --endpoint https://beta.pk-db.com --output <worktree>/vocabulary.lock.json` from `/home/mkoenig/git/pkdb/python` (read `pkdb vocabulary sync --help` first; it may need `PKDB_API_KEY`, which is not available to you); if it cannot run, write the vocabulary bundled with the pkdb source through its snapshot writer (find the function `pkdb vocabulary sync` uses to save, call it with `bundled_vocabulary()`) and record in the report that the lock is the bundled vocabulary of pkdb 0.11.1 plus this branch, to be refreshed by the `vocabulary` workflow.

- [ ] **Step 4: Check** `git -C /home/mkoenig/git/pkdb_data-tooling status --short` shows only the intended files; `uv run --locked pkdb check --root /home/mkoenig/git/pkdb_data-tooling --staged` (after `git add`) passes, since no format 2 study exists.

- [ ] **Step 5: Commit** in the worktree (one commit for ignore rules and attributes, one for the pins, plus the optional renormalization commit):

```bash
git -C /home/mkoenig/git/pkdb_data-tooling add .gitignore .gitattributes
git -C /home/mkoenig/git/pkdb_data-tooling commit -m "Ignore workbook state files and keep tables and JSON files with LF line ends"
git -C /home/mkoenig/git/pkdb_data-tooling add requirements/pkdb.txt vocabulary.lock.json
git -C /home/mkoenig/git/pkdb_data-tooling commit -m "Pin the pkdb release and the vocabulary that the checks use"
```

---

### Task 4: Pre-commit and Dependabot

**Files (pkdb_data worktree):** Modify: `.pre-commit-config.yaml`, `.github/dependabot.yml`

**Interfaces:**
- Consumes: Task 3 pins.
- Produces: the hook `pkdb-check` used by curators.

- [ ] **Step 1: Restructure** `.pre-commit-config.yaml`: remove the global `exclude: ^studies/` and add `exclude: ^studies/` to each generic hook (keep the comment about curated files). Add:

```yaml
  - repo: local
    hooks:
      - id: pkdb-check
        name: pkdb check (study format 2)
        entry: env PKDB_NO_UPDATE=1 uvx --python 3.14 --with-requirements requirements/pkdb.txt pkdb check --staged
        language: system
        files: ^studies/
        pass_filenames: false
  - repo: https://github.com/rhysd/actionlint
    rev: v1.7.7
    hooks:
      - id: actionlint
```

Check `uvx --with-requirements` resolves `pkdb` to the pinned version (if `uvx` needs `--from`, use `uvx --python 3.14 --from "$(head ... )"` via a tiny `sh -c`, and keep the single pin file as the source). Verify the `actionlint` hook's current tag and language (it may need Go or Docker; if it cannot run here, use the `actionlint-py` hook repository instead and say so).

- [ ] **Step 2: Dependabot.** Add to `.github/dependabot.yml` a `pip` entry for directory `/requirements`, weekly, grouped, with the same commit message prefix style as the existing entry.

- [ ] **Step 3: Test the hook** in the worktree (use a temporary local `pre-commit` via `uvx pre-commit`, installed into the worktree only, and uninstall it afterwards): stage a docs-only change (the hook is skipped); stage a change inside one format 1 study folder (the hook runs and passes, skipping it); run `uvx pre-commit run --all-files` for the generic hooks and `actionlint` (expect only the workflow files of later tasks to matter). Since the pin `pkdb==0.12.0` is not on PyPI yet, run the hook's command with the local pkdb (`uv run --locked --project /home/mkoenig/git/pkdb/python pkdb check --staged` from the worktree) to verify the behavior, and record that the pinned command runs once the release exists. Unstage and restore every test change.

- [ ] **Step 4: Commit**

```bash
git -C /home/mkoenig/git/pkdb_data-tooling add .pre-commit-config.yaml .github/dependabot.yml
git -C /home/mkoenig/git/pkdb_data-tooling commit -m "Run pkdb check on staged studies and lint the workflows in pre-commit"
```

---

### Task 5: The `studies` CI workflow and the ruleset

**Files (pkdb_data worktree):** Create: `.github/workflows/studies.yml`; Modify: `.github/rulesets/develop.json`

**Interfaces:**
- Consumes: Task 3 pins; `pkdb check` of Tasks 1-2.

Workflow (model the header on `.github/workflows/docs.yml` and pkdb's `ruff.yml`): name `studies`; triggers `pull_request` (branches `develop`, `main`), `push` (branch `develop`), `workflow_dispatch`; `permissions: contents: read`; concurrency group per ref with `cancel-in-progress: true`; job `studies`, `ubuntu-latest`, timeout 30 minutes. Steps:
1. `actions/checkout` (same major version as `docs.yml`) with `filter: blob:none`, `fetch-depth: 0`, `sparse-checkout-cone-mode: false`, `sparse-checkout:` lines `/*` (root files), `/requirements/`, `/.github/`, `/studies/*/*/study.json`, `/studies/study_identifiers.json`, `persist-credentials: false`.
2. Compute the base: for `pull_request` the merge base with `origin/${{ github.base_ref }}`; for `push`, `${{ github.event.before }}` (when it is all zeros, check all studies); for `workflow_dispatch`, all studies.
3. Decide the scope: when the diff touches `requirements/pkdb.txt` or `vocabulary.lock.json`, all studies; otherwise the changed study folders from `git diff --name-only -z <base>...HEAD -- studies/`, added to the sparse checkout with `git sparse-checkout add` (NUL-safe, quoted paths). For "all studies", `git sparse-checkout set --no-cone '/*' '/studies/'` (fetches blobs of study files on demand, which is the full study data; acceptable for these rare runs).
4. `astral-sh/setup-uv` (the version used in pkdb's workflows) with Python 3.14 and cache on `requirements/pkdb.txt`.
5. `env PKDB_NO_UPDATE=1 uvx --python 3.14 --with-requirements requirements/pkdb.txt pkdb check --changed <base> --format human` (or without `--changed` for all studies).

Ruleset: add the required status check `studies` beside `docs` in `.github/rulesets/develop.json` (keep the JSON format of the file); do not run `apply.sh`.

- [ ] **Step 1: Write the workflow and the ruleset change.**
- [ ] **Step 2: Lint** with `actionlint` (pre-commit hook of Task 4).
- [ ] **Step 3: Dry run the shell steps** locally: make a partial clone `git clone --filter=blob:none --no-checkout /home/mkoenig/git/pkdb_data <scratch>/clone` (from the local repository; no network), apply the sparse patterns, simulate a pull request base (`origin/develop`) and a branch that changes one study folder, run the base and scope scripts of steps 2-3 extracted to a temporary script, and check with `git -C <scratch>/clone count-objects -v` and `du -sh` that only the selected folders' blobs were fetched (Review Focus 4); run `pkdb check` from the local pkdb against it. Delete the scratch clone.
- [ ] **Step 4: Commit**

```bash
git -C /home/mkoenig/git/pkdb_data-tooling add .github/workflows/studies.yml .github/rulesets/develop.json
git -C /home/mkoenig/git/pkdb_data-tooling commit -m "Check changed studies in CI and require the check on develop"
```

---

### Task 6: The `issues` and `vocabulary` workflows

**Files (pkdb_data worktree):** Create: `.github/workflows/issues.yml`, `.github/workflows/vocabulary.yml`

- **`issues`:** triggers `push` to `develop` with `paths: [studies/**]`, `schedule` nightly (`cron: "17 3 * * *"`), `workflow_dispatch` with a boolean input `dry_run` (default false); `permissions: contents: read, issues: write`; concurrency group `issues` with `cancel-in-progress: false`; checkout with `filter: blob:none`, sparse patterns `/*`, `/requirements/`, `/studies/*/*/study.json`, `/studies/*/*/review.json`; setup-uv as in Task 5; run `pkdb issues sync --root . --format human` (plus `--dry-run` when the input is true) with env `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}`, `PKDB_ISSUES_REPO: ${{ github.repository }}`, `PKDB_ENDPOINT: ${{ vars.PKDB_ENDPOINT }}`, `PKDB_API_KEY: ${{ secrets.PKDB_API_KEY }}`, `PKDB_NO_UPDATE: 1`. Check `pkdb issues sync --help` for the exact options.
- **`vocabulary`:** triggers `schedule` weekly (`cron: "23 4 * * 1"`) and `workflow_dispatch`; `permissions: contents: write, pull-requests: write`; checkout as in `issues` but with `/studies/*/*/` study files only when the lock changed (start with the `issues` patterns); run `pkdb vocabulary sync --endpoint "$PKDB_ENDPOINT" --output vocabulary.lock.json` (with `PKDB_API_KEY` if the command needs it); if `git diff --quiet vocabulary.lock.json` fails, widen the sparse checkout to all of `studies/`, run `pkdb check --vocabulary vocabulary.lock.json --format human > check.txt || true`, and open a pull request with `peter-evans/create-pull-request` (pin a released major version) on branch `vocabulary/refresh`, title "Refresh the vocabulary lock", body with the new vocabulary version and the check summary (first 200 lines of `check.txt`) and the note that a maintainer closes and reopens the pull request to run the required `studies` check.

- [ ] **Step 1: Write both workflows.**
- [ ] **Step 2: Lint** with `actionlint`.
- [ ] **Step 3: Dry run** the `issues` command locally against a scratch copy of 3 migrated studies (`pkdb migrate` on a copy of three pkdb_data study folders in a scratch checkout, then `pkdb issues sync --root <scratch> --dry-run` with `PKDB_ENDPOINT`/`PKDB_API_KEY` unset: expect exit 2 with the roster message, which proves the wiring; never call GitHub with write methods). Delete the scratch copy.
- [ ] **Step 4: Commit**

```bash
git -C /home/mkoenig/git/pkdb_data-tooling add .github/workflows/issues.yml .github/workflows/vocabulary.yml
git -C /home/mkoenig/git/pkdb_data-tooling commit -m "Sync study issues nightly and refresh the vocabulary lock weekly"
```

---

### Task 7: Curation guide, AGENTS.md, the Claude skill and maintainer docs

**Files (pkdb_data worktree):** Create: `docs/curation-v2.md`, `docs/development.md`, `AGENTS.md`, `.claude/skills/pkdb-curation/SKILL.md`; Modify: `CLAUDE.md`, `zensical.toml` (navigation), `.github/pull_request_template.md` if it names the old flow

Content (plain, short sentences; link the pkdb documentation at its published URL as `docs/index.md` and `docs/installation.md` of pkdb_data already do; read them for the base URL):
- **`docs/curation-v2.md`** "Curation guide (study format 2)": a short note at the top that it applies after the cutover, then: install and update pkdb; start a study with `pkdb new` (licence, access private, `papers/`, the issue); the files of a study and the column reference (link to the generated study format page); tables in the workbook (`pkdb tables open/sync`) or as TSV; raw tables and digitized figures (`pkdb tables add --raw`, `pkdb digitize import`, `pkdb plot`); check with `pkdb check` and fix or acknowledge warnings; review items and approval in the curation app (`pkdb curate`); release (`pkdb release --access`) and upload; rename or move with `pkdb move`; the GitHub issue and the nightly sync; pull requests (one per study, the `studies` check).
- **`AGENTS.md`**: as in spec section 4, with the exact commands of main spec section 13 (updated for `pkdb check` and the commit identity), and the rules: JSON only through `pkdb` commands; `--agent <model>` or `PKDB_AGENT` on every command; `pkdb check` before each commit; one branch and one pull request per study linking its issue; commits with the responsible curator's identity and the trailer `Agent: <model>`; never upload, never approve; never read or search all of `studies/`; the schema from `pkdb schema export` and `pkdb schema docs`.
- **`.claude/skills/pkdb-curation/SKILL.md`**: front matter `name: pkdb-curation`, `description:` one sentence on when to use it (curating or correcting a PK-DB study in pkdb_data); then the numbered workflow with commands, referring to `AGENTS.md` for the rules instead of repeating them.
- **`docs/development.md`** (already referenced by `CLAUDE.md` and the pre-commit config): pre-commit setup (`uvx pre-commit install`) and what the hooks do; the pins and how to update them (`requirements/pkdb.txt` through Dependabot or by hand; `vocabulary.lock.json` through the `vocabulary` workflow or `pkdb vocabulary sync`); the three workflows; the secret `PKDB_API_KEY` and the variable `PKDB_ENDPOINT`; applying the ruleset with `.github/rulesets/apply.sh`; closing and reopening a vocabulary pull request to run the checks.
- **`CLAUDE.md`**: add a short section pointing to `AGENTS.md` for curation work and to `docs/development.md` for tooling; update the layout list (pins, workflows, `.claude/skills`).
- **`zensical.toml`**: add `curation-v2.md` (as "Curation guide (study format 2, after the cutover)") and `development.md` to the navigation.

- [ ] **Step 1: Write the pages.**
- [ ] **Step 2: Build** with `uvx --from "$(cat docs/requirements.txt)" zensical build --clean --strict` and `python3 scripts/llms_txt.py` in the worktree; no warning. Remove the generated `site/` afterwards if it is not ignored.
- [ ] **Step 3: Check** every command named in the pages against `pkdb <command> --help` of the local pkdb (wrong options are the most likely error); no em dash; paragraphs on one line.
- [ ] **Step 4: Commit**

```bash
git -C /home/mkoenig/git/pkdb_data-tooling add docs/curation-v2.md docs/development.md AGENTS.md .claude/skills/pkdb-curation/SKILL.md CLAUDE.md zensical.toml
git -C /home/mkoenig/git/pkdb_data-tooling commit -m "Document the study format 2 curation workflow for curators and AI agents"
```

---

## Rollout (controller, with the user)

1. pkdb: push `feature/study-format-v2-11` and open a pull request (after #880 is merged, rebase onto `develop`); add the release note with the PR number.
2. pkdb release `0.12.0` with `pkdb check` to PyPI: the user decides and runs it.
3. pkdb_data: push `feature/study-format-2-tooling` and open a pull request against `develop` (draft until step 2 is done, since the pin needs the release).
4. After the merge, the user applies the ruleset (`.github/rulesets/apply.sh`), sets the secret `PKDB_API_KEY` and the variable `PKDB_ENDPOINT`, and starts the `issues` workflow once with `dry_run`.

## Self-Review

- **Spec coverage:** decisions (section 1) in Global Constraints and Tasks 3-7; `pkdb check` (section 2) in Tasks 1-2; files and workflows (section 3) in Tasks 3-6; documentation and AI instructions (section 4) in Task 7; pkdb changes (section 5) in Task 2; rollout (section 6) in the Rollout section; testing (section 7) in the tests and dry runs of each task.
- **Placeholders:** the `...` in Task 1's last test is a described setup the implementer writes fully; tool versions (`actionlint`, `create-pull-request`, checkout and setup-uv majors) are checked by the implementer against the current releases and the versions already used in the repositories.
- **Types:** `select`, `check`, `vocabulary_for`, `CheckError`, `Problem`, `CheckReport` are the same in Tasks 1 and 2.
