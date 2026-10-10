---
search:
  exclude: true
---

# pkdb_data tooling for study format 2

Date: 2026-10-09. Status: Draft for review. Sub-project 6 of [Study format v2](2026-10-05-study-format-v2-design.md) (section 17), which lists pre-commit, CI, `.gitignore` and `.gitattributes`, the curation guide, the AI skill with `AGENTS.md` and the issue sync workflow for the pkdb_data repository (sections 13 and 14). This document records the decisions taken while planning it on 2026-10-09. Where it is silent, the main spec and [the sub-project 5 spec](2026-10-08-study-format-v2-05-migration-design.md) apply.

## 1. Decisions

- **Timing.** The tooling lands on pkdb_data `develop` before the cutover. Every check works on study format 2 folders and skips format 1 folders, so it runs on today's repository and is ready to check every migrated study in the cutover pull request.
- **One check command.** A new `pkdb check` in pkdb serves both pre-commit and CI, so the logic is tested and versioned with pkdb. The spec's `pkdb check --staged` becomes one of its modes.
- **Pins.** pkdb_data pins the pkdb version and the vocabulary. Pre-commit and CI read the same pins, so a check changes its answer only when the data or a reviewed pin changes.
- **Curation guide.** The format 2 guide is a new page now. The cutover pull request makes it the main guide and archives the format 1 guide.
- **AI commits.** Agents commit with the git identity of the responsible curator and add the commit message trailer `Agent: <model>`. This replaces the `pkdb-ai` identity of the main spec, section 13.
- **Workbook ignore rule.** `studies/**/*.xlsx` is added to `.gitignore` only in the cutover pull request. Before the cutover, curators still create format 1 workbooks, and a new ignore rule would leave them out of commits without a warning. Until then `pkdb check` refuses a tracked format 2 workbook.

## 2. `pkdb check` (pkdb)

`pkdb check [PATH...] [--staged | --changed BASE] [--root PATH] [--vocabulary FILE] [--format human|json]`

- **Selection.** Paths are study folders or folders that contain studies. `--staged` selects the studies touched by staged files (`git diff --cached`), `--changed BASE` the studies touched since `BASE` (`git diff BASE...HEAD`). Without paths and without either option, it checks every study of the checkout. Deleted studies are skipped. Format 1 studies are skipped and counted.
- **Per format 2 study.** The canonical-form check of `pkdb format --check`, without writing; offline validation with the vocabulary from `--vocabulary`, else `vocabulary.lock.json` at the repository root, else the vocabulary bundled with pkdb. Errors fail the check; warnings are listed and do not fail it (acknowledged warnings are already filtered). A workbook `<name>.xlsx` or its `.<name>.xlsx.pkdb-base` file that is tracked or staged in git is an error.
- **Repository.** Always, inside a checkout: the checks of `pkdb registry --check` (a shared PKDB identifier or issue number, an unreadable `study.json`, a disagreement with `studies/study_identifiers.json`).
- **Behavior.** It never writes and never contacts the network. Exit code 0 when clean, 1 for problems, 2 for usage errors. Human output lists each problem with study, file, row and message; JSON output carries the same data.

## 3. pkdb_data files and workflows

- **`.gitignore`.** Add `.*.pkdb-base` now. Spreadsheet lock files (`~$*`, `.~lock.*#`) are already ignored. `studies/**/*.xlsx` follows in the cutover pull request (section 1).
- **`.gitattributes`.** `*.tsv` and `*.json` with `text eol=lf`; `*.pdf`, `*.png`, `*.jpg` and `*.xlsx` as `binary`. When `git ls-files --eol` shows tracked TSV or JSON files with CRLF line ends, they are renormalized in a separate commit of the same pull request.
- **Pins.** `requirements/pkdb.txt` holds `pkdb==X.Y.Z`, the first release with `pkdb check`; Dependabot proposes updates (pip ecosystem, beside the existing GitHub Actions entry). `vocabulary.lock.json` at the root is written by `pkdb vocabulary sync --output vocabulary.lock.json`.
- **Pre-commit.** The global `exclude: ^studies/` moves onto each generic hook, because a global exclude would hide study files from the new hook. A local hook runs `pkdb check --staged` with the pinned pkdb through `uvx`, with `PKDB_NO_UPDATE=1`, when files below `studies/` are staged and without passing file names. An `actionlint` hook checks the workflow files.
- **CI workflow `studies`.** A required check on `develop`. Triggers: pull requests to `develop` and `main`, pushes to `develop`, manual dispatch. Permissions: `contents: read`. The repository (7.9 GB) is cloned without blobs, with a sparse checkout of every `study.json`, `studies/study_identifiers.json`, the root files and the changed study folders; it then runs `pkdb check --changed <base>` (on a push, `<base>` is the previous head). When a pull request changes `requirements/pkdb.txt` or `vocabulary.lock.json`, it checks every format 2 study. `.github/rulesets/develop.json` adds the check; a maintainer applies it with `.github/rulesets/apply.sh` after the merge.
- **Issue sync workflow `issues`.** Triggers: pushes to `develop` that touch `studies/`, nightly, manual dispatch with a `dry_run` input. Permissions: `contents: read`, `issues: write`; the token is the workflow's `GITHUB_TOKEN`; the roster comes from the secret `PKDB_API_KEY` and the variable `PKDB_ENDPOINT`. It runs `pkdb issues sync` on a sparse checkout of every `study.json` and `review.json`, one run at a time (a concurrency group without cancellation). Before the cutover it finds no format 2 study and changes nothing. `pkdb issues sync --adopt` stays a manual step of the cutover runbook.
- **Vocabulary refresh workflow `vocabulary`.** Weekly and by dispatch: `pkdb vocabulary sync`; when the lock changed, `pkdb check` on every format 2 study with the new lock, then a pull request with the new lock and the check summary. A pull request opened with the workflow token does not start other workflows, so a maintainer closes and reopens it to run the required `studies` check; `docs/development.md` says so.

## 4. Documentation and AI instructions (pkdb_data)

- **Format 2 curation guide** `docs/curation-v2.md`. The workflow: `pkdb new` and the `papers/` folder, tables in the workbook or as TSV, raw tables and digitized figures, `pkdb check`, review items, approval in the curation app, `pkdb release`, `pkdb move` and the GitHub issue of each study. It links the generated column reference and the workbook, curation app and command pages of the pkdb documentation instead of repeating them. Until the cutover the navigation lists it as the guide after the cutover; the cutover pull request renames it to `curation_guide.md` and archives the format 1 guide as `curation-guide-format-1.md`.
- **`AGENTS.md`** at the repository root, for every agent. What the repository is; never read or search all of `studies/`; the workflow of the main spec, section 13, with the exact commands; the rules: JSON files only through `pkdb` commands, `--agent <model>` (or `PKDB_AGENT`) on every command, `pkdb check` before each commit, one branch and one pull request per study that links its issue, commits with the responsible curator's identity and the trailer `Agent: <model>`, never upload, never approve. It points to `pkdb schema export` and `pkdb schema docs` for the schema instead of repeating it.
- **Claude skill** `.claude/skills/pkdb-curation/SKILL.md`: the same workflow as step-by-step instructions with the commands to run, referring to `AGENTS.md` for the shared rules.
- **Maintainer documentation.** `CLAUDE.md` points to `AGENTS.md`. `docs/development.md`, which `CLAUDE.md` and the pre-commit configuration already reference, is written: the pins and how to update them, pre-commit, the three workflows, the secret and the variable, applying the ruleset, and reopening a vocabulary pull request.

## 5. Changes in pkdb beyond `pkdb check`

- The main spec, sections 13 and 14, records the agent identity and the `pkdb check` command.
- The cutover runbook `docs/study-format-2-cutover.md` gets two steps in the migration pull request: add `studies/**/*.xlsx` to `.gitignore`, and make the format 2 guide the main guide.
- `docs/python-client.md` lists `pkdb check` and has a short section on the checks of a pkdb_data checkout.

## 6. Rollout

1. A pkdb pull request with `pkdb check`, its tests, the documentation and a release note.
2. A pkdb release with `pkdb check` on PyPI. Publishing is a maintainer decision.
3. A pkdb_data pull request with sections 3 and 4, pinned to that release, made in a separate git worktree from `origin/develop` so that local checkouts with other work stay untouched. Its own `studies` check runs on it and passes, since no format 2 study exists yet.
4. After the merge, a maintainer applies the ruleset, sets the secret `PKDB_API_KEY` and the variable `PKDB_ENDPOINT`, and starts the issue sync once by hand with `dry_run`.

## 7. Testing

- **`pkdb check`** on throwaway git repositories in `tmp_path`: staged files, `--changed BASE`, a deleted study, skipped format 1 studies, canonical-form failures, validation errors against warnings, a tracked or staged workbook and state file, a shared PKDB identifier or issue number, the vocabulary lock and the bundled fallback, no network access, exit codes and JSON output.
- **pkdb_data:** `pre-commit run --all-files` with the new hooks, `zensical build --strict`, and a dry run of each workflow command against a scratch copy of a few migrated studies, never against the real data.
