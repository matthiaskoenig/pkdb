# Backend replacement handoff — 2026-09-22

Work is paused at the user's explicit request to continue on another machine.
Implementation is incomplete. Do not retire Django, deploy, merge, or represent
corpus/compatibility acceptance as complete.

## Resume here

Branch: `backend/fastapi-replacement`. Original working copy:
`/tmp/pkdb-backend-replacement`; original repository: `/home/mkoenig/git/pkdb`.
The final saved commit includes this document and a read-only administrator role
catalogue. Additional original-workspace source/resources/tests are now included via
checkpoint branch `handoff/local-workspace-20260922`, as explicitly requested by
the user. Develop itself remains unchanged. The legacy uploader is not a
replacement runtime dependency.

Read these committed files first:

1. `docs/superpowers/specs/2026-09-21-backend-replacement-design.md`.
2. `docs/superpowers/plans/2026-09-21-backend-replacement.md` and its three phase plans.
3. `docs/backend-migration/execution-ledger.md` (including all decisions/rulings).
4. `docs/backend-migration/acceptance.md` (chronological evidence; latest checkpoints
   supersede earlier counts), `contracts.json`, and `runbook.md`.

Continue native execution using the executing-plans skill. The user authorized
implementation, not deployment. Do not repeat brainstorming or restart completed
work. No per-task implementation agents; one fresh whole-branch review remains
required at the end. Preserve unrelated/untracked files and source data.

## Transfer and checkout

A portable full-history Git bundle is saved outside this worktree in the original
repository's `backend-migration-handoff-20260922/` folder. Copy that whole folder
to the new machine. It includes this handoff, the bundle, checksums, and selected
local rehearsal evidence/scripts. No credentials, token files, virtualenvs,
Docker volumes, database dumps, or attachment volumes are included.

For a separate checkout on the new machine:

```bash
git clone --branch backend/fastapi-replacement backend-replacement.bundle pkdb-replacement
cd pkdb-replacement
git status --short
```

Alternatively fetch the bundle into an existing clone and create an isolated
worktree for its branch. Do not overwrite an existing branch with local changes.

The corpus is a separate checkout at `../pkdb_data/studies` relative to the original
repository. Transfer or obtain it separately without editing it. The legacy upload client
`backend/pkdb_data` and its resources/tests are now committed at the user's explicit
request and included in this branch and the refreshed bundle. The separate study
corpus remains unchanged. The non-placeholder password in `.env.template` was
replaced with a placeholder; its original is only in a protected local /tmp backup.
Generated transfer artifacts remain outside Git.

Push status: automatic approval review rejected publication of the newly added
legacy resources because they contain personal account data, including user names
and email addresses in `backend/pkdb_data/resources/json/users.json`. The configured
destination is the public repository `matthiaskoenig/pkdb`. No push has succeeded;
explicit approval for that payload/destination is pending.

## Stack and verification

Replacement runtime: `backend-next/`, FastAPI/Pydantic2/SQLAlchemy2/Alembic/
PostgreSQL, authenticated explicit FastMCP, uv/Ruff/ty, standard-GIL Python3.13/3.14.
No Django, Elasticsearch, Redis or queue in the replacement runtime. Existing
legacy code/services remain only because cutover gates have not passed.

- At commit4499eb8a, 337 regular tests passed on **each** Python3.13.1/3.14.6.
- Both images at that checkpoint passed two system tests each: runtime REST/MCP/
  protected files/science/shutdown and PostgreSQL+attachment restore.
- Last added role catalogue: six focused tests pass on3.13; Ruff/format pass.
  **Run complete suites, types and image gates again for this final addition.**
- Migration tooling:16 tests passed on each interpreter, using `python -m pytest`
  from repository root so `tools` is importable.
- Legacy suite previously108 passed on Python3.9; characterization tooling17 passed.
- The broad explicit corpus suite is NOT green: previously24 passed/5 failed on
  both Pythons due to known source/vocabulary blockers.

Follow backend-next/README.md and the CI workflow for clean environment, test DB,
Alembic, wheel and image setup. Original local virtualenv names were .venv-py313
and .venv-py314; these are not portable. Keep separate environments for each Python.
Test suites require `PKDB_TEST_DATABASE_URL`; explicit container tests also require
`PKDB_TEST_IMAGE`, `PKDB_TEST_IMAGE_PYTHON`, and restore tests
`PKDB_TEST_POSTGRES_CONTAINER`. Ordinary tests live in backend-next/tests;
corpus_tests and system_tests are explicit additional gates.

## Highest-priority remaining work

1. Verify the final role-catalogue addition on both interpreters. It reads fixed
   basic/admin/reviewer/curator roles; arbitrary Django group/permission mutation
   is still unresolved. Fresh IDs1–4 are documented, not historic group IDs.
2. Finish contract coverage. Remaining gaps include published editable study
   GET/PUT/source roundtrip; administrative reference/file/vocabulary operations;
   association analysis detail IDs for groups/individuals/outputs/data; full
   filter/operator/error/media-permission matrices. Do not guess association IDs:
   legacy used association rows while new schema uses composite joins. Canonical
   storage currently does not preserve original study/reference JSON templates.
3. Resolve corpus compatibility and obtain explicit source dispositions. A pending
   optional question asked whether to keep strict rejection or prepare proposed
   source/vocabulary corrections for review; **no answer was received**. Current
   assumption is strict validation, no source edits, no approved exclusions.
4. Refresh full HTTP rebuild after decisions settle. Processing version is5,
   schema head276e94c58ad1. The existing full HTTP checkpoint is processing4 plus
   two individually verified version5 publications, not a completed current rebuild.
5. Finish acceptance, one fresh whole-branch review, then perform the planned
   backend-next→backend move and CI/compose/legacy retirement only after gates pass.
   Do not push, merge, deploy or discard production data without authorization.

## Corpus, performance and restore evidence

- All1,579 folders audited read-only at processing5:1,093 valid,486 invalid,
  zero unexpected exceptions. Duplicate-SID folders are included, so validation
  count is not publication count. `corpus-audit-v5.json` and
  `corpus-failures-v5.tsv` record fingerprint and sampled errors (first10/folder).
- Full historical HTTP rebuild:1,072 published,446 failed,61 blocked,zero pending/
  HTTP500; complete:false. Two additional version5 studies (Levy1983 and McCrea1999)
  published individually, giving1,074 in the rehearsal DB. No accepted exclusions.
- Known apixaban blockers: Frost2013a missing Tab3 image; Frost2014a unknown
  measurements; Frost2015 negative concentration mean; Frost2018 missing vocabulary/
  method definitions, forbidden negatives and percent data against hours definition.
- Full snapshot restore verified33 tables,1,470,887 rows,11,916 files,
  2,618,745,722 bytes, all ordered row/file hashes equal. Durable checkpoint committed.
- `performance.json` and performance/ contain same-source local Frost2014 evidence:
  fresh-application cold run, excluded warmup, five measured warm runs per runtime.
  All measured median/p95 budgets pass legacy×1.10; warm upload medians1.775s(3.13)
  and1.485s(3.14). This is not production/cold-storage capacity evidence.
- Four actual full-corpus PostgreSQL query plans are committed; study-page statement
  count is tested independent of page length. No claim all queries use GIN indexes.
- Existing frontend exercised login, browse/search, detail/figures, output rows,
  four timecourse plots, ZIP and protected TSV. Temporary copy replaced obsolete
  node-sass with sass under Node22; original frontend source untouched.

## Machine-local resources left intact

Original Docker test PG15435, rebuild PG15436, legacy characterization PG15434/
ES19224 and benchmark legacy ES19228 are disposable local services. New runtime
never uses Elasticsearch. Original full rebuild attachments (~2.5GB), raw report,
backup/restore DB and files remain under the ignored worktree directory
`.superpowers/sdd/2026-09-21-backend-replacement/rebuild-runtime/` and Docker volumes.
They are not needed to resume code work, but transfer dumps **plus attachment
volumes** separately if preserving those exact local databases. Do not delete them
before final review. Durable evidence is committed; selected raw reports accompany
the transfer folder. Rehearsal scripts use old-machine absolute paths and must be
adapted before execution.

Temporary browser/API/legacy services may remain running on the original machine;
no rebuild or benchmark is running at handoff. No new work should be started there.
