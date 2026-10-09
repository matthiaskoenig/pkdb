---
search:
  exclude: true
---

# Study format 2 migration, part C: study lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `pkdb new`, `pkdb move`, `pkdb release` and `pkdb registry` create, rename, release and list study format 2 studies of a pkdb_data checkout, and the server keeps a moved study's row by taking it over through its GitHub issue number.

**Architecture:** A new package `python/src/pkdb/lifecycle/` holds name rules, the scan of release blocks and issue numbers, and one module per command; `python/src/pkdb/lifecycle_cli.py` registers the four top-level commands. `pkdb new` and `pkdb move` reach GitHub through a small helper in `pkdb/issues/single.py` built on the part B client. On the server, the format 2 upload path in `backend/src/pkdb_server/services/ingestion.py` gains a takeover by `issue` beside the existing takeover by `pkdb_id`, and an Alembic migration adds a partial unique index on `studies.issue`.

**Tech Stack:** Python 3.14, Pydantic 2, argparse, httpx2 (`MockTransport`), FastAPI, SQLAlchemy, Alembic, PostgreSQL, pytest, ruff, ty.

**Spec:** `docs/superpowers/specs/2026-10-08-study-format-v2-05-migration-design.md` (section 6, section 8 "Lifecycle", "Backend") and `docs/superpowers/specs/2026-10-05-study-format-v2-design.md` (sections 6, 10.1, 12, 13).

## Global Constraints

- **Python:** 3.14. Run from `python/`: `uv run --locked pytest -q -x`, `uv run --locked ruff check .`, `uv run --locked ruff format --check .`, `uv run --locked ty check`. Every commit keeps them green.
- **Backend:** tests need the disposable test database (`pkdb-tests-db-1` on `127.0.0.1:15439`): from the repository root `export PKDB_TEST_DATABASE_URL=postgresql+psycopg://pkdb_test:local-test-only@127.0.0.1:15439/pkdb_test` and `uv run --project backend pytest backend/tests -q -x`; ruff and ty from `backend/`. Commit Alembic migrations. Never touch deployment data volumes.
- **Docs:** when a Markdown file changes, run `uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean` from the repository root; it must print no warning.
- **Writing:** never use the em dash character; Markdown paragraphs on one source line; no attribution lines in commits, docs or code; user-facing text in plain, short English sentences.
- **Generated files:** never hand-edit `docs/study-format.md`, any `CHANGELOG.md`, or the curation contract fixtures.
- **Tests:** never call the real GitHub API (use `python/tests/fake_github.py`), never write into pkdb_data, never resolve references online (use `ReferenceResolver(offline=True)` with a seeded cache or a fake resolver).
- **Writes:** `study.json` and `review.json` of an existing study are written only through the revision-checked writers (`patch_metadata`, `write_metadata` with a revision, `write_checked`); a `RevisionConflict` is a refusal, never a retry without the revision.
- **Values from the spec:**
  - `pkdb new <substance>/<name> (--pmid N | --doi D) --licence open|closed --access public|private [--user U] [--agent A] [--no-issue]`; licence and access are required.
  - `pkdb move <old> <new>` refuses an existing target and an open workbook, renames the folder and every file named after the study, rewrites the file names of review targets, runs `format`, renames the issue right away and warns without a GitHub token.
  - `pkdb release <study>... [--date D]` requires `approved`, no open review items and no validation errors, refuses a study that already has a `pkdb_id`, numbers in argument order after the largest `pkdb_id`, today's date unless `--date`.
  - `pkdb registry [--check]` lists released studies by `pkdb_id` with location and date; `--check` exits non-zero when two studies share a `pkdb_id` or an issue number.
  - Commands that scan all studies find the repository by walking up to the folder that contains `studies/`, or take `--root`.
  - Server: an upload whose sid matches no stored study and whose `pkdb_id` claims none takes over a stored format 2 study with the same `issue` number and another sid, when the uploader may write it; a unique index on `studies.issue` for rows where it is set.
- **Plan decisions where the spec is silent:**
  - Name rules for new studies and move targets: substance `[A-Za-z0-9][A-Za-z0-9_-]*`, study name `[A-Za-z0-9][A-Za-z0-9_-]*` with at most 24 characters (raw table sheets `<study>_Tab..` must fit Excel's 31 characters), not a reserved name (`RESERVED_NAMES` of `studyformat/layout.py`). Existing folders that break the rule keep working; only new names are checked.
  - The output flag is `--format human|json` like the other commands (the spec's `pkdb registry --json` becomes `--format json`).
  - `pkdb release` checks every named study first and writes nothing when one fails; the next number also counts the identifiers of `studies/study_identifiers.json` while that file exists (before the cutover finishes).
  - `pkdb new --agent A` writes provenance `automatic_curation` with `method` A, `version` from `--agent-version` and `run_id` from `--run-id` (both required with `--agent`), and as assets the study PDF and every `--asset FILE` (file name and SHA-256); without any asset it refuses, because the model requires one.
  - `pkdb new` writes the author as `creator` and no curators; the new issue gets the substance label and `curate`; `pkdb issues sync` sets the assignees later.
  - `pkdb new` moves `<name>.pdf` and the images `<name>_<source>.png` (source as in `SOURCE_PATTERN`) out of `papers/<substance>/<name>/`; other files stay and are named in the output; an emptied paper folder and an emptied substance folder below `papers/` are removed.
  - `pkdb move` refuses a workbook that is open or holds edits that are not in the tables (sync check), and otherwise deletes the workbook and its `.pkdb-base` state file (`pkdb tables open` regenerates them). An emptied old substance folder is removed. A `.wpd.json` file holds no image name, so it is only renamed.
  - Without a GitHub token, `pkdb new` refuses before writing anything unless `--no-issue`; a GitHub failure after the folder was written leaves the folder, exits 1 and says to run `pkdb issues sync --adopt`.
  - A located old sid does not redirect after a takeover by issue, as after a takeover by `pkdb_id` today.
  - The migration refuses to add the index when stored studies share an issue number and names them.

## Review Focus

1. **A move of a study whose workbook holds edits that are not in the tables** (a curator saved the workbook but did not sync): the move refuses and changes nothing, because deleting the workbook would lose the edits. Test in Task 6 (`test_a_workbook_with_unsynced_edits_refuses_the_move`).
2. **A release of several studies where one fails a check** (not approved, an open item, a validation error, an existing `pkdb_id`): no study gets a number, so numbers never get gaps or half-done releases. Test in Task 3 (`test_one_refused_study_stops_the_whole_release`).
3. **`pkdb new` when GitHub fails after the folder was written** (rate limit, network): the folder is complete and valid, the command exits 1 with the hint to run `pkdb issues sync --adopt`, and a second `pkdb new` refuses the existing folder instead of writing over it. Test in Task 5 (`test_a_github_failure_after_writing_keeps_the_folder`).
4. **An upload that takes over by issue a study the uploader may not write**: refused with 409, the other study is named only when the uploader can read it, and nothing is renamed. Test in Task 1 (`test_issue_takeover_needs_edit_rights`).
5. **The next PKDB number before the cutover finished**, when some released studies are still format 1 and only listed in `study_identifiers.json`: the number is higher than every identifier of the registry file too. Test in Task 2 (`test_the_next_identifier_counts_the_registry_file`).

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/src/pkdb_server/services/ingestion.py` | Takeover by issue in `stored_study`, lock in `lock_publication`, refusal of a duplicate issue. |
| `backend/src/pkdb_server/db/models/studies.py` | Partial unique index `uq_studies_issue`. |
| `backend/alembic/versions/p007issueunique_unique_issue.py` | The migration. |
| `backend/src/pkdb_server/app.py` | `SCHEMA_REVISION = "p007issueunique"`. |
| `backend/tests/fixtures/study_folders.py` | `write_study(..., issue=None)`. |
| `python/src/pkdb/lifecycle/__init__.py` | Package docstring. |
| `python/src/pkdb/lifecycle/names.py` | Name rules of new studies and move targets. |
| `python/src/pkdb/lifecycle/registry.py` | Scan of release blocks and issue numbers, duplicates, next PKDB identifier. |
| `python/src/pkdb/lifecycle/release.py` | Checks and writes of `pkdb release`. |
| `python/src/pkdb/lifecycle/new.py` | Folder creation of `pkdb new`, papers move, reference. |
| `python/src/pkdb/lifecycle/move.py` | Folder and file renames of `pkdb move`. |
| `python/src/pkdb/issues/single.py` | Create or adopt one issue; rename one issue. |
| `python/src/pkdb/lifecycle_cli.py` | `pkdb new`, `move`, `release`, `registry`. |
| `python/src/pkdb/cli.py` | Register and dispatch. |
| `docs/api.md`, `docs/data-model.md`, `docs/python-client.md`, `docs/local-curation.md`, `docs/study-format-2-cutover.md` | Documentation. |

---

### Task 1: Server takeover by issue number and a unique index

**Files:**
- Modify: `backend/src/pkdb_server/services/ingestion.py` (`lock_publication` line 60, `former_sids` line 101, `stored_study` lines 129-261), `backend/src/pkdb_server/db/models/studies.py` (`__table_args__` lines 85-103), `backend/src/pkdb_server/app.py:71`, `backend/tests/fixtures/study_folders.py:20-31`, `backend/tests/integration/test_migrations.py:28-29`, `backend/tests/integration/test_study_format_fields.py` (tests that rely on issue 2158), `docs/api.md` (upload paragraph near line 118, identifiers section near line 47), `docs/data-model.md` (lines 17-19, migration paragraph near line 69)
- Create: `backend/alembic/versions/p007issueunique_unique_issue.py`, tests in `backend/tests/api/test_study_format_uploads.py`

**Interfaces:**
- Consumes: `stored_study(session, study, principal, *, lock=False, locked=None)`, `is_located(sid)`, `publication_studies`, `PublicationConflict`, `allowed`/`readable` helpers inside `stored_study`, `write_study(root, name, *, pmid, release)`, `multipart(folder)`.
- Produces: `write_study(root, name="Example", *, pmid="123", release=None, issue=None)`; index `uq_studies_issue` (`issue`, unique, `postgresql_where issue IS NOT NULL`); revision `p007issueunique` with `down_revision = "p006studyformat"`.

Behavior of `stored_study` (after the lookup by sid and by `pkdb_id`, before the publication takeover):
- When `root is None`, the upload has no `pkdb_id`, `is_located(study.sid)` and `study.metadata.issue` is set: the candidates are the stored rows with `Study.issue == issue` and a located sid. One candidate: when `allowed("write", match)`, `root = match` (the existing rename path in `_publish_once` renames it, and `ReplacementResult.renamed_from` names the old sid); otherwise raise `PublicationConflict` with `f"The study {match.sid} has issue #{issue}; uploading it as {study.sid} needs edit rights on {match.sid}"` when `readable(match)`, else `"A study already has this issue"`.
- After `root` is settled: any other row (`Study.id != root.id` when root exists) with the same `issue` is a refusal `fail("duplicate_issue", f"Issue #{issue} belongs to the study {other.sid}", SourceLocation(file=STUDY_JSON, path=...), field="issue")` when readable, else without the sid, so the unique index never surfaces as a misleading `IntegrityError`.
- `former_sids` (or `lock_publication`'s caller) also locks the sid of an issue match, so a concurrent upload cannot race the takeover.

- [ ] **Step 1: Give the fixture an issue parameter.** `write_study(root, name="Example", *, pmid="123", release=None, issue=None)` writes `"issue": issue` only when it is not None. Update the tests that relied on 2158 (search `2158` in `backend/tests`) to pass `issue=2158` explicitly. Run the backend suite: it must stay green before any behavior change.

- [ ] **Step 2: Write the failing tests** in `backend/tests/api/test_study_format_uploads.py` (use the file's `stored`, `multipart`, `other_headers` fixtures and helpers):

```python
def test_a_moved_study_takes_over_its_row_by_issue(client, creator_headers, tmp_path, session_factory):
    before = write_study(tmp_path / "a", "Before", issue=4711)
    assert client.put("/api/v2/studies/caffeine/Before", headers=creator_headers, **multipart(before)).status_code == 201
    [row] = stored(session_factory)
    after = write_study(tmp_path / "b", "After", pmid="456", issue=4711)
    response = client.put("/api/v2/studies/caffeine/After", headers=creator_headers, **multipart(after))
    assert response.status_code == 200, response.text
    assert (response.json()["renamed_from"], response.json()["created"]) == ("caffeine/Before", False)
    [moved] = stored(session_factory)
    assert (moved.id, moved.sid, moved.issue) == (row.id, "caffeine/After", 4711)
    assert client.get("/api/v2/studies/caffeine/Before", headers=creator_headers).status_code == 404


def test_issue_takeover_needs_edit_rights(client, creator_headers, other_headers, tmp_path, session_factory):
    before = write_study(tmp_path / "a", "Before", issue=4711)
    assert client.put("/api/v2/studies/caffeine/Before", headers=creator_headers, **multipart(before)).status_code == 201
    after = write_study(tmp_path / "b", "After", pmid="456", issue=4711)
    response = client.put("/api/v2/studies/caffeine/After", headers=other_headers, **multipart(after))
    assert response.status_code == 409
    assert "caffeine/Before" not in response.text
    assert [row.sid for row in stored(session_factory)] == ["caffeine/Before"]


def test_an_issue_of_another_study_is_refused(client, creator_headers, tmp_path, session_factory):
    first = write_study(tmp_path / "a", "First", issue=1)
    second = write_study(tmp_path / "b", "Second", pmid="456", issue=2)
    for folder, name in ((first, "First"), (second, "Second")):
        assert client.put(f"/api/v2/studies/caffeine/{name}", headers=creator_headers, **multipart(folder)).status_code == 201
    again = write_study(tmp_path / "c", "Second", pmid="456", issue=1)
    response = client.put("/api/v2/studies/caffeine/Second", headers=creator_headers, **multipart(again))
    assert response.status_code == 409
    assert "Issue #1 belongs to the study caffeine/First" in response.text


def test_a_released_study_still_takes_over_by_pkdb_id(client, creator_headers, tmp_path, session_factory):
    before = write_study(tmp_path / "a", "Before", release="PKDB00198", issue=9)
    assert client.put("/api/v2/studies/caffeine/Before", headers=creator_headers, **multipart(before)).status_code == 201
    after = write_study(tmp_path / "b", "After", release="PKDB00198", issue=9)
    response = client.put("/api/v2/studies/caffeine/After", headers=creator_headers, **multipart(after))
    assert response.status_code == 200 and response.json()["renamed_from"] == "caffeine/Before"
```

If `other_headers` is not readable access to the first study in this file's setup, assert the generic message instead and keep the "nothing renamed" assertion. Adapt the expected texts to the response format the file's other 409 tests assert (detail string or report).

- [ ] **Step 3: Run them to verify they fail**: `uv run --project backend pytest backend/tests/api/test_study_format_uploads.py -q -k issue` -> FAIL (201 instead of 200, or an IntegrityError 409 with the misleading message).

- [ ] **Step 4: Implement** the behavior above. Add to `Study.__table_args__`: `Index("uq_studies_issue", "issue", unique=True, postgresql_where=text("issue IS NOT NULL"))` (import `text`). Create the migration:

```python
"""Unique issue numbers of studies.

Revision ID: p007issueunique
Revises: p006studyformat
"""

import sqlalchemy as sa
from alembic import op

revision = "p007issueunique"
down_revision = "p006studyformat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    shared = op.get_bind().execute(
        sa.text(
            "SELECT issue, string_agg(sid, ', ' ORDER BY sid) FROM studies "
            "WHERE issue IS NOT NULL GROUP BY issue HAVING count(*) > 1 ORDER BY issue"
        )
    ).all()
    if shared:
        names = "; ".join(f"#{issue}: {sids}" for issue, sids in shared)
        raise RuntimeError(f"Studies share an issue number; give each study its own issue first ({names})")
    op.create_index(
        "uq_studies_issue", "studies", ["issue"], unique=True,
        postgresql_where=sa.text("issue IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_studies_issue", table_name="studies")
```

Set `SCHEMA_REVISION = "p007issueunique"` in `app.py`; in `test_migrations.py` the revision count becomes 7. Add a migration test: with two rows sharing an issue at `p006studyformat`, `command.upgrade(config, "head")` raises and names both sids; without them the index exists (query `pg_indexes` like the file's `search_index` helper).

Docs: `docs/api.md` upload paragraph: an upload whose identifier matches no stored study and whose `study.json` has no `release` takes over the stored study format 2 study with the same `issue` (a study moved with `pkdb move`), when you may edit it; the old identifier then answers 404; an issue that belongs to another study is refused (409). `docs/data-model.md`: issue numbers are unique among studies, and a paragraph on migration `p007issueunique` (it refuses to run while studies share an issue number and names them). Build the docs.

- [ ] **Step 5: Run** the backend suite, ruff, ty (backend), docs build -> PASS.

- [ ] **Step 6: Commit**

```bash
git add backend docs/api.md docs/data-model.md
git commit -m "Take over a moved study by its issue number and keep issue numbers unique"
```

---

### Task 2: Name rules, the release scan and `pkdb registry`

**Files:**
- Create: `python/src/pkdb/lifecycle/__init__.py`, `python/src/pkdb/lifecycle/names.py`, `python/src/pkdb/lifecycle/registry.py`, `python/src/pkdb/lifecycle_cli.py`, `python/tests/lifecycle/__init__.py` (empty), `python/tests/lifecycle/test_names.py`, `python/tests/lifecycle/test_registry.py`, `python/tests/lifecycle_fixtures.py`
- Modify: `python/src/pkdb/cli.py` (import tuple, `register`, dispatch), `python/tests/test_cli.py` (help test command list), `docs/python-client.md` (command table near line 199)

**Interfaces:**
- Consumes: `pkdb.repository` (`repository_root`, `study_folders`, `location`), `pkdb.studyformat.validation.is_v2_folder`, `pkdb.studyformat.metadata.read_metadata`, `pkdb.studyformat.layout.RESERVED_NAMES`, `pkdb.migration.registry.Registry` (reads `studies/study_identifiers.json`: `Registry.read(path)`, `.identifiers`), `study_cli.add_format`/`is_human`/`emit`/`fail`, `studyformat_cli.say`.
- Produces:
  - `names.NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")`, `names.MAX_STUDY_NAME = 24`, `names.parse_location(value: str) -> tuple[str, str]` (raises `ValueError` with a plain message for a value that is not `<substance>/<name>`, a substance or name outside `NAME`, a name longer than 24 characters, or a reserved name).
  - `registry.Released` (frozen dataclass): `pkdb_id: str`, `location: str`, `date: datetime.date`.
  - `registry.Scan` (frozen dataclass): `released: list[Released]` (sorted by `pkdb_id`), `issues: dict[int, list[str]]` (issue number to locations), `errors: list[str]` (unreadable `study.json`, as `"<location>: <message>"`).
  - `registry.scan(root: Path) -> Scan` (format 2 studies only).
  - `registry.duplicates(scan: Scan) -> list[str]`: `"PKDB00001 is the identifier of several studies: a, b"` and `"Issue #7 is named by several studies: a, b"`, sorted.
  - `registry.next_identifier(scan: Scan, root: Path) -> int`: one more than the largest number among the `release` blocks and, when `root/studies/study_identifiers.json` exists, its identifiers; 1 when there is none.
  - `registry.identifier(number: int) -> str`: `f"PKDB{number:05d}"`.
  - `lifecycle_cli.register(commands)`, `lifecycle_cli.run(args) -> int` (commands `registry` now; later tasks add `release`, `new`, `move`).

`pkdb registry [--root PATH] [--check] [--format human|json]`: human output one line per released study `PKDB00001  caffeine/Harder1988  2026-09-28`, then the problems; JSON `{"released": [{"pkdb_id", "location", "date"}], "problems": [...], "errors": [...]}`. Exit 0; with `--check` exit 1 when `duplicates(scan)` or `scan.errors` is not empty; 2 for usage errors (no checkout).

- [ ] **Step 1: Write the fixtures and failing tests.**

`python/tests/lifecycle_fixtures.py`:

```python
"""Format 2 study folders of a pkdb_data checkout for the lifecycle tests."""

from pathlib import Path

from pkdb.studyformat.jsonio import dump_json


def released_study(root: Path, location: str, *, pkdb_id=None, date="2026-09-28", issue=None, status="draft") -> Path:
    folder = root / "studies" / location
    folder.mkdir(parents=True)
    metadata = {"format": 2, "reference": {"pmid": "123"}, "creator": "ana", "licence": "open", "access": "private"}
    if issue is not None:
        metadata["issue"] = issue
    if pkdb_id is not None:
        metadata["release"] = {"pkdb_id": pkdb_id, "date": date}
    (folder / "study.json").write_text(dump_json(metadata), encoding="utf-8")
    review = {"status": status}
    if status == "approved":
        review |= {"reviewers": ["bo"], "approved_by": "bo", "approved": "2026-10-01T00:00:00Z"}
    (folder / "review.json").write_text(dump_json(review), encoding="utf-8")
    return folder
```

`python/tests/lifecycle/test_names.py`:

```python
import pytest

from pkdb.lifecycle.names import parse_location


def test_valid_locations():
    assert parse_location("caffeine/Harder1988") == ("caffeine", "Harder1988")
    assert parse_location("Gd-EOB-DTPA/Al-Hadidi1994") == ("Gd-EOB-DTPA", "Al-Hadidi1994")
    assert parse_location("acetaminophen_mice/Smith_2020b") == ("acetaminophen_mice", "Smith_2020b")


@pytest.mark.parametrize(
    "value, message",
    [
        ("Harder1988", "<substance>/<name>"),
        ("caffeine/Harder 1988", "letters, digits"),
        ("caffeine/.hidden", "letters, digits"),
        ("caffeine/a/b", "<substance>/<name>"),
        ("caffeine/" + "A" * 25, "24 characters"),
        ("caffeine/outputs", "reserved"),
    ],
)
def test_invalid_locations(value, message):
    with pytest.raises(ValueError, match=message):
        parse_location(value)
```

`python/tests/lifecycle/test_registry.py`:

```python
import json
from datetime import date

from lifecycle_fixtures import released_study

from pkdb.cli import main
from pkdb.lifecycle.registry import duplicates, identifier, next_identifier, scan


def test_scan_lists_released_studies_and_issues(tmp_path):
    released_study(tmp_path, "caffeine/B", pkdb_id="PKDB00002", issue=7)
    released_study(tmp_path, "caffeine/A", pkdb_id="PKDB00001", issue=8)
    released_study(tmp_path, "codeine/C", issue=9)
    result = scan(tmp_path)
    assert [(r.pkdb_id, r.location, r.date) for r in result.released] == [
        ("PKDB00001", "caffeine/A", date(2026, 9, 28)),
        ("PKDB00002", "caffeine/B", date(2026, 9, 28)),
    ]
    assert result.issues == {7: ["caffeine/B"], 8: ["caffeine/A"], 9: ["codeine/C"]}
    assert duplicates(result) == [] and next_identifier(result, tmp_path) == 3
    assert identifier(3) == "PKDB00003"


def test_duplicates_are_named(tmp_path):
    released_study(tmp_path, "caffeine/A", pkdb_id="PKDB00001", issue=7)
    released_study(tmp_path, "caffeine/B", pkdb_id="PKDB00001", issue=7)
    assert duplicates(scan(tmp_path)) == [
        "Issue #7 is named by several studies: caffeine/A, caffeine/B",
        "PKDB00001 is the identifier of several studies: caffeine/A, caffeine/B",
    ]


def test_the_next_identifier_counts_the_registry_file(tmp_path):
    released_study(tmp_path, "caffeine/A", pkdb_id="PKDB00004")
    (tmp_path / "studies" / "study_identifiers.json").write_text(
        json.dumps({"PKDB01237": ["albuterol/Guo2016", "2026-09-28"]}), encoding="utf-8"
    )
    assert next_identifier(scan(tmp_path), tmp_path) == 1238


def test_registry_command_checks_duplicates(tmp_path, monkeypatch, capsys):
    released_study(tmp_path, "caffeine/A", pkdb_id="PKDB00001", issue=7)
    monkeypatch.chdir(tmp_path / "studies")
    assert main(["registry", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["released"][0]["location"] == "caffeine/A"
    released_study(tmp_path, "caffeine/B", issue=7)
    assert main(["registry", "--check", "--format", "human"]) == 1
    assert "Issue #7" in capsys.readouterr().out
```

The problems are sorted as plain strings, so "Issue ..." comes before "PKDB...". Check the exact shape of `study_identifiers.json` against `pkdb/migration/registry.py` and adapt the fixture, not the meaning.

- [ ] **Step 2: Run to verify they fail**: `uv run --locked pytest -q tests/lifecycle` -> FAIL, modules not found.

- [ ] **Step 3: Implement** `names.py`, `registry.py` (read each format 2 `study.json` with `read_metadata`; `MetadataError` is an entry of `errors`; reuse `pkdb.migration.registry.Registry` for the registry file, or read its keys directly if that class is too migration-specific, and say which in the report), and `lifecycle_cli.py` with the `registry` command (lazy imports inside `run`; exit codes as above). Register it in `cli.py` (`lifecycle_cli.register(commands)`; `if args.command in {"new", "move", "release", "registry"}: return lifecycle_cli.run(args)`), add `registry` to the help test's command list, and add the command table row `| pkdb registry [--check] | List released studies by PKDB identifier; --check fails on a shared identifier or issue number |` to `docs/python-client.md`. Build the docs.

- [ ] **Step 4: Run** `uv run --locked pytest -q tests/lifecycle tests/test_cli.py` -> PASS; full suite, ruff, ty.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/lifecycle python/src/pkdb/lifecycle_cli.py python/src/pkdb/cli.py python/tests/lifecycle python/tests/lifecycle_fixtures.py python/tests/test_cli.py docs/python-client.md
git commit -m "List released studies with pkdb registry and check shared identifiers"
```

---

### Task 3: `pkdb release`

**Files:**
- Create: `python/src/pkdb/lifecycle/release.py`, `python/tests/lifecycle/test_release.py`
- Modify: `python/src/pkdb/lifecycle_cli.py`, `docs/python-client.md`, `docs/local-curation.md:107` (replace "the `pkdb release` command for this is planned" by how to release)

**Interfaces:**
- Consumes: Task 2 `scan`, `next_identifier`, `identifier`, `repository_root`; `read_metadata`, `read_review`, `patch_metadata(folder, patch, revision)`, `RevisionConflict`, `MetadataError`, `ReviewError`, `validate_folder(folder, vocabulary)`, `tables_cli._vocabulary_options`/`_vocabulary` (vocabulary chosen as `pkdb validate` does).
- Produces:
  - `release.Refusal` (frozen dataclass): `location: str`, `reasons: list[str]`.
  - `release.check(folder: Path, vocabulary) -> list[str]`: the reasons a study cannot be released: `"The review status is draft; a study must be approved"`, `"2 review items are open"`, `"Validation has 3 errors"`, `"The study is already released as PKDB00007"`; empty when it can.
  - `release.release(root: Path, folders: list[Path], vocabulary, *, on: datetime.date) -> list[tuple[str, str]]`: checks every folder first and raises `ReleaseRefused(refusals: list[Refusal])` when any fails (nothing written); otherwise assigns `identifier(next_identifier(...) + i)` in argument order, writes `{"release": {"pkdb_id": ..., "date": on.isoformat()}}` with `patch_metadata` and the revision read before the checks, and returns `[(location, pkdb_id), ...]`. A `RevisionConflict` stops with an error naming the study; studies written before it keep their numbers (say so in the message).

`pkdb release STUDY... [--date YYYY-MM-DD] [--vocabulary ...] [--endpoint ...] [--offline] [--format human|json]`: each `STUDY` is a study folder path; all must lie in one checkout. Human output `caffeine/A: PKDB00012`; refusals list each study with its reasons; exit 0, 1 when refused or on a conflict, 2 for usage errors (a path that is not a format 2 study, studies of two checkouts, a duplicate argument, a bad date).

- [ ] **Step 1: Write the failing tests** `python/tests/lifecycle/test_release.py` (use `sf_vocabulary` from `python/tests/conftest.py`; the approved fixture must validate: build it from the `valid_files` fixture of `conftest.py` written into `studies/<substance>/<name>` with `review.json` approved, or extend `released_study`; adapt helpers, not assertions):

```python
from datetime import date

import pytest

from pkdb.lifecycle.release import ReleaseRefused, release
from pkdb.studyformat.metadata import read_metadata


def test_studies_are_numbered_in_argument_order(approved_studies, sf_vocabulary):
    root, first, second = approved_studies("caffeine/B", "caffeine/A", highest="PKDB00009")
    assert release(root, [first, second], sf_vocabulary, on=date(2026, 10, 10)) == [
        ("caffeine/B", "PKDB00010"),
        ("caffeine/A", "PKDB00011"),
    ]
    released = read_metadata(second).metadata.release
    assert (released.pkdb_id, released.date) == ("PKDB00011", date(2026, 10, 10))


def test_one_refused_study_stops_the_whole_release(approved_studies, sf_vocabulary):
    root, first, second = approved_studies("caffeine/A", "caffeine/B")
    (second / "review.json").write_text('{"status": "in_review"}\n', encoding="utf-8")
    with pytest.raises(ReleaseRefused) as refused:
        release(root, [first, second], sf_vocabulary, on=date(2026, 10, 10))
    assert [(r.location, r.reasons) for r in refused.value.refusals] == [
        ("caffeine/B", ["The review status is in_review; a study must be approved"])
    ]
    assert read_metadata(first).metadata.release is None


def test_an_open_item_a_validation_error_and_a_release_refuse(approved_studies, sf_vocabulary):
    ...
```

Write the third test fully: one study with an open review item (`pkdb.studyformat.review_edit.add_item` or a hand-written item), one with a validation error (delete `subjects.tsv`'s `all` row's required cell or remove `reference.json`), one already released; assert each reason text. Add a CLI test: `main(["release", str(first), "--date", "2026-10-10", "--format", "json"])` returns 0 and prints the number; a refusal returns 1 and writes nothing. Define the `approved_studies(*locations, highest=None)` fixture in the test file: it writes valid approved studies under `tmp_path/studies` and, with `highest`, one more released study with that identifier.

- [ ] **Step 2: Run to verify they fail**: `uv run --locked pytest -q tests/lifecycle/test_release.py` -> FAIL.

- [ ] **Step 3: Implement** `release.py` and the `release` command. Docs: command table row `| pkdb release STUDY... [--date D] | Give approved studies the next PKDB identifiers |` and a paragraph in the study format 2 section: requirements (approved, no open review items, no validation errors), numbering in argument order after the largest identifier (also of `study_identifiers.json` while it exists), nothing is written when one study is refused, a release goes through a pull request. Update `docs/local-curation.md:107`. Build the docs.

- [ ] **Step 4: Run** `uv run --locked pytest -q tests/lifecycle` -> PASS; full suite, ruff, ty.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/lifecycle/release.py python/src/pkdb/lifecycle_cli.py python/tests/lifecycle/test_release.py docs/python-client.md docs/local-curation.md
git commit -m "Release approved studies with the next PKDB identifiers"
```

---

### Task 4: `pkdb new` without the issue

**Files:**
- Create: `python/src/pkdb/lifecycle/new.py`, `python/tests/lifecycle/test_new.py`
- Modify: `python/src/pkdb/lifecycle_cli.py`, `docs/python-client.md`, `docs/study-format-2-cutover.md` (section "Papers", line 83)

**Interfaces:**
- Consumes: Task 2 `parse_location`, `repository_root`; `StudyMetadata`, `StudyReference`, `canonical_study_json`, `canonical_review_json`, `Review`, `pkdb.schemas.provenance` (`ManualCuration`, `AutomaticCuration`, `SourceAsset`), `TABLES`/`SUBJECTS`, `render_tsv`, `ROOT` (`"all"`), `sync_reference(folder, resolver)`, `ReferenceResolver`, `ReferenceError`, `format_folder`, `SOURCE_PATTERN`, `pkdb.identity.Author`.
- Produces:
  - `new.NewStudy` (frozen dataclass): `folder: Path`, `moved: list[str]` (files taken from papers), `left: list[str]` (files left in papers), `reference: str | None` (the change text of `sync_reference`).
  - `new.create_study(root: Path, location: str, *, pmid: str | None, doi: str | None, licence: str, access: str, author: Author, resolver: ReferenceResolver, agent_version: str | None = None, run_id: str | None = None, assets: list[Path] = []) -> NewStudy`.
  - `new.NewStudyRefused(ValueError)` for refusals that wrote nothing.

Behavior of `create_study`:
1. `parse_location(location)`; refuse an existing `studies/<location>` folder (`NewStudyRefused("caffeine/X exists already")`), exactly one of `pmid`/`doi` (`StudyReference` validates their form), `licence` and `access` from the spec values, and with `author.agent` require `agent_version` and `run_id`.
2. Build everything in a temporary folder next to the target (`studies/<substance>/.<name>.new`), then rename it into place, so an error never leaves a half-written study: `study.json` (`format 2`, `reference`, `creator=author.user`, `licence`, `access`, provenance `ManualCuration()` or `AutomaticCuration(method=author.agent, version=agent_version, run_id=run_id, assets=[SourceAsset(url=<file name>, sha256=<hex>) for the study PDF and each asset])`), `review.json` (`Review(status="draft")`), `subjects.tsv` with the row `all`, then `sync_reference(tmp, resolver)` (a `ReferenceError` refuses with its message), then `format_folder(tmp)` (not ok: refuse with the issue messages).
3. Papers: when `papers/<location>/` exists, `<name>.pdf` and `<name>_<source>.png` (source matching `SOURCE_PATTERN`) are copied into the temporary folder before the reference step; after the rename into place they are deleted from papers, the emptied paper folder and an emptied `papers/<substance>/` are removed; other files are listed in `left`. With `--agent` and no PDF and no `--asset`, refuse ("An automatic curation names what it read: put <name>.pdf into papers/<location>/ or pass --asset FILE").
4. On any refusal, the temporary folder is removed and papers are untouched.

`pkdb new LOCATION (--pmid N | --doi D) --licence open|closed --access public|private [--user U] [--agent A --agent-version V --run-id R] [--asset FILE]... [--root PATH] [--offline] [--no-issue] [--format human|json]`: in this task the command always behaves as with `--no-issue` (Task 5 adds the issue). The author comes from `author_from(args.user, args.agent)`. Human output: `Created studies/caffeine/X`, moved and left files, the reference line. Exit 0; 1 on a refusal; 2 for usage errors.

- [ ] **Step 1: Write the failing tests** `python/tests/lifecycle/test_new.py`. Use a fake resolver: a `ReferenceResolver(offline=True, cache_dir=...)` with a seeded cache entry for PMID 123 (see how `python/tests` seed reference caches, for example in `tests/test_references.py`), or a tiny object with the methods `sync_reference` calls; say which in the report.

```python
import pytest

from pkdb.identity import Author
from pkdb.lifecycle.new import NewStudyRefused, create_study
from pkdb.studyformat.metadata import read_metadata
from pkdb.studyformat.review_edit import read_review
from pkdb.studyformat.validation import is_v2_folder


def test_a_new_study_is_a_valid_draft(checkout, resolver):
    result = create_study(checkout, "caffeine/Smith2020", pmid="123", doi=None, licence="open", access="private", author=Author("ana"), resolver=resolver)
    folder = checkout / "studies" / "caffeine" / "Smith2020"
    assert result.folder == folder and is_v2_folder(folder)
    metadata = read_metadata(folder).metadata
    assert (metadata.creator, metadata.licence, metadata.access, metadata.reference.pmid) == ("ana", "open", "private", "123")
    assert metadata.provenance.kind == "manual_curation" and metadata.issue is None
    assert read_review(folder).review.status == "draft"
    assert "all" in (folder / "subjects.tsv").read_text(encoding="utf-8")
    assert (folder / "reference.json").exists()
    assert not list((checkout / "studies" / "caffeine").glob(".*"))


def test_papers_move_into_the_study(checkout, resolver):
    paper = checkout / "papers" / "caffeine" / "Smith2020"
    paper.mkdir(parents=True)
    for name in ("Smith2020.pdf", "Smith2020_Tab1.png", "Smith2020_notes.png", "Smith2020.xlsx"):
        (paper / name).write_bytes(b"x")
    result = create_study(checkout, "caffeine/Smith2020", pmid="123", doi=None, licence="open", access="private", author=Author("ana"), resolver=resolver)
    assert sorted(result.moved) == ["Smith2020.pdf", "Smith2020_Tab1.png"]
    assert sorted(result.left) == ["Smith2020.xlsx", "Smith2020_notes.png"]
    assert (result.folder / "Smith2020_Tab1.png").exists() and not (paper / "Smith2020.pdf").exists()


def test_an_agent_records_an_automatic_curation(checkout, resolver):
    paper = checkout / "papers" / "caffeine" / "Smith2020"
    paper.mkdir(parents=True)
    (paper / "Smith2020.pdf").write_bytes(b"%PDF")
    result = create_study(checkout, "caffeine/Smith2020", pmid="123", doi=None, licence="closed", access="private", author=Author("ana", agent="claude"), resolver=resolver, agent_version="5.5", run_id="run-1")
    provenance = read_metadata(result.folder).metadata.provenance
    assert (provenance.kind, provenance.method, provenance.version, provenance.run_id) == ("automatic_curation", "claude", "5.5", "run-1")
    assert provenance.assets[0].url == "Smith2020.pdf"


@pytest.mark.parametrize(
    "options, message",
    [
        ({"pmid": "123", "doi": "10.1000/x"}, "PubMed ID or a DOI"),
        ({"pmid": None, "doi": None}, "PubMed ID or a DOI"),
        ({"pmid": "123", "doi": None, "author": Author("ana", agent="claude")}, "--agent-version"),
    ],
)
def test_refusals_write_nothing(checkout, resolver, options, message):
    arguments = {"licence": "open", "access": "private", "author": Author("ana"), **options}
    with pytest.raises(NewStudyRefused, match=message):
        create_study(checkout, "caffeine/Smith2020", resolver=resolver, **arguments)
    assert not (checkout / "studies" / "caffeine" / "Smith2020").exists()
    assert not list((checkout / "studies").rglob(".*.new"))


def test_an_existing_study_is_refused(checkout, resolver):
    create_study(checkout, "caffeine/Smith2020", pmid="123", doi=None, licence="open", access="private", author=Author("ana"), resolver=resolver)
    with pytest.raises(NewStudyRefused, match="exists"):
        create_study(checkout, "caffeine/Smith2020", pmid="123", doi=None, licence="open", access="private", author=Author("ana"), resolver=resolver)
```

`checkout` makes `tmp_path/studies`; `resolver` resolves PMID 123 offline. Add a CLI test: `main(["new", "caffeine/Smith2020", "--pmid", "123", "--licence", "open", "--access", "private", "--user", "ana", "--no-issue", "--offline", "--format", "json"])` from inside the checkout returns 0, and without `--licence` argparse exits 2.

- [ ] **Step 2: Run to verify they fail**: `uv run --locked pytest -q tests/lifecycle/test_new.py` -> FAIL.

- [ ] **Step 3: Implement** `new.py` and the `new` command (the resolver from `ReferenceResolver(args.cache_dir, offline=args.offline)`; check `pkdb reference resolve` for the cache directory option). Docs: command row `| pkdb new SUBSTANCE/NAME (--pmid N \| --doi D) --licence ... --access ... | Create a study folder with study.json, reference.json, subjects.tsv and review.json |` and a paragraph: name rules, required licence and access, files taken from `papers/`, `--agent` with `--agent-version`, `--run-id` and assets. `docs/study-format-2-cutover.md` "Papers": name exactly which files `pkdb new` takes. Build the docs.

- [ ] **Step 4: Run** `uv run --locked pytest -q tests/lifecycle` -> PASS; full suite, ruff, ty.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/lifecycle/new.py python/src/pkdb/lifecycle_cli.py python/tests/lifecycle/test_new.py docs/python-client.md docs/study-format-2-cutover.md
git commit -m "Create study format 2 folders with pkdb new"
```

---

### Task 5: The issue of a new study

**Files:**
- Create: `python/src/pkdb/issues/single.py`, `python/tests/issues/test_single.py`
- Modify: `python/src/pkdb/lifecycle_cli.py` (`new`), `python/tests/lifecycle/test_new.py` (CLI tests), `docs/python-client.md`

**Interfaces:**
- Consumes: `pkdb.issues.github` (`GitHub`, `GitHubError`, `Issue`, `repository_from`, `token_from`), `pkdb.issues.state` (`WORKFLOW`, `LABEL_COLORS`, `SUBSTANCE_COLOR`), `pkdb.studyformat.metadata.read_metadata`, `patch_metadata`, `python/tests/fake_github.py` (`FakeGitHub`).
- Produces:
  - `single.issue_for_new_study(github: GitHub, location: str) -> tuple[Issue, bool]`: the issue whose title is exactly `location` (open before closed, then the lowest number; pull requests are already excluded by `issues()`), or a new issue with title `location` and labels `[<substance>, "curate"]` (missing labels created with their colors); the bool is True when it was created.
  - `single.rename_issue(github: GitHub, number: int, location: str) -> Issue`.
  - `issues_cli`-style factory `lifecycle_cli.github_client(repository: str, token: str | None) -> GitHub` that tests replace.

`pkdb new` without `--no-issue`: before writing anything, require a token (`GH_TOKEN` or `GITHUB_TOKEN`; exit 2 with `Set GH_TOKEN or GITHUB_TOKEN, or pass --no-issue`); after `create_study`, `issue_for_new_study(...)`, then `patch_metadata(folder, {"issue": number}, revision)` with the revision of the freshly written `study.json`. A `GitHubError` after the folder exists exits 1 with `Created studies/<location>, but its issue failed: <message>. Run pkdb issues sync --adopt to give it one.` Human output adds `Issue #N (created)` or `Issue #N (adopted)`.

- [ ] **Step 1: Write the failing tests** `python/tests/issues/test_single.py`:

```python
from fake_github import FakeGitHub

from pkdb.issues.single import issue_for_new_study, rename_issue


def test_an_existing_issue_with_the_exact_title_is_adopted():
    github = FakeGitHub(issues=[{"number": 3, "title": "Curate caffeine/A"}, {"number": 5, "title": "caffeine/A", "state": "closed", "state_reason": "completed"}, {"number": 8, "title": "caffeine/A"}])
    with github.client() as client:
        issue, created = issue_for_new_study(client, "caffeine/A")
    assert (issue.number, created) == (8, False) and github.writes == []


def test_without_a_match_an_issue_is_created_with_labels():
    github = FakeGitHub()
    with github.client() as client:
        issue, created = issue_for_new_study(client, "caffeine/A")
    assert created and github.issues[issue.number]["title"] == "caffeine/A"
    assert sorted(github.issues[issue.number]["labels"]) == ["caffeine", "curate"]
    assert sorted(github.labels) == ["caffeine", "curate"]


def test_rename():
    github = FakeGitHub(issues=[{"number": 2, "title": "caffeine/A"}])
    with github.client() as client:
        rename_issue(client, 2, "codeine/B")
    assert github.issues[2]["title"] == "codeine/B"
```

Check `FakeGitHub`'s constructor and issue storage (it lives in `python/tests/fake_github.py`) and adapt the setup lines, not the meaning. In `python/tests/lifecycle/test_new.py` add CLI tests with `monkeypatch.setattr("pkdb.lifecycle_cli.github_client", lambda repository, token: fake.client())`:
- `test_new_records_the_issue`: exit 0 and `study.json` has the issue number.
- `test_new_needs_a_token_unless_no_issue`: without token exit 2 and no folder written.
- `test_a_github_failure_after_writing_keeps_the_folder`: the fake fails `POST /issues` (`fake.fail`), exit 1, the message names `pkdb issues sync --adopt`, the folder exists and validates, `study.json` has no issue, and a second `pkdb new` of the same location exits 1 with "exists".

- [ ] **Step 2: Run to verify they fail**: `uv run --locked pytest -q tests/issues/test_single.py tests/lifecycle/test_new.py` -> FAIL.

- [ ] **Step 3: Implement** `single.py` and the issue step of `new`. Docs: `pkdb new` creates or adopts the issue titled `<substance>/<name>` and records its number; `--no-issue` leaves that to `pkdb issues sync --adopt`; it needs `GH_TOKEN` or `GITHUB_TOKEN`. Build the docs.

- [ ] **Step 4: Run** `uv run --locked pytest -q tests/issues tests/lifecycle` -> PASS; full suite, ruff, ty.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/issues/single.py python/src/pkdb/lifecycle_cli.py python/tests/issues/test_single.py python/tests/lifecycle/test_new.py docs/python-client.md
git commit -m "Give a new study its GitHub issue"
```

---

### Task 6: `pkdb move`

**Files:**
- Create: `python/src/pkdb/lifecycle/move.py`, `python/tests/lifecycle/test_move.py`
- Modify: `python/src/pkdb/lifecycle_cli.py`, `docs/python-client.md`, release note after the pull request exists

**Interfaces:**
- Consumes: Task 2 `parse_location`, `repository_root`, `location`; Task 5 `rename_issue`, `lifecycle_cli.github_client`; `pkdb.studyformat.workbook.base` (`workbook_path(folder)`, `open_lock(workbook)`, `state_path(workbook)`), `pkdb.studyformat.sync.sync_study(folder, vocabulary, check=True) -> SyncResult` (`changes`, `conflicts`, `lock`, `issues`), `read_review`/`canonical_review_json`/`write_checked`, `read_metadata`, `format_folder`, `raw_file`/`parse_raw_file`, `digitization_file`/`parse_digitization_file`, `image_file`, `SOURCE_PATTERN`.
- Produces:
  - `move.Moved` (frozen dataclass): `folder: Path`, `renamed: list[tuple[str, str]]` (old and new file names), `targets: int` (review targets rewritten), `issue: int | None`.
  - `move.MoveRefused(ValueError)`.
  - `move.move_study(root: Path, old: str, new: str, vocabulary) -> Moved`.

Behavior of `move_study`:
1. `old` must be a format 2 study of the checkout; `parse_location(new)`; refuse an existing `studies/<new>` and `old == new`.
2. Workbook: when `workbook_path(old_folder)` exists, refuse when `open_lock(...)` finds a lock, or when `sync_study(old_folder, vocabulary, check=True)` reports `changes`, `conflicts` or error issues ("The workbook holds edits that are not in the tables; run pkdb tables sync first"); otherwise delete the workbook and its state file.
3. Rename the folder (create `studies/<new substance>/` when needed; the rename refuses an existing target, never merges), then inside it every file whose name is `<old name>.pdf`, `<old name>_<source>.png` (images), a raw table `parse_raw_file(name, old name)`, or a digitization `parse_digitization_file(name, old name)`, to the same name with the new study name.
4. `review.json`: every `item.target.file` (and acknowledgement target file, see `studyformat/validation.py:132`) that is one of the renamed files gets its new name; write with `write_checked` and the revision read before.
5. `format_folder(new_folder)` (rewrites the `study` column); not ok is an error naming the issues, and the folder stays at its new place (say so).
6. Remove an emptied old substance folder.

`pkdb move OLD NEW [--root PATH] [--vocabulary ...] [--endpoint ...] [--offline] [--format human|json]`: `OLD` and `NEW` are locations `<substance>/<name>` within the checkout. After the move, when `study.json` has an issue: with a token, `rename_issue(github, issue, new)`; without a token, a warning `Set GH_TOKEN or GITHUB_TOKEN to rename issue #N now; pkdb issues sync renames it later`; a `GitHubError` is a warning too (the sync aligns titles), exit 0. Human output: the new folder, the renamed files, the review targets, the issue line.

- [ ] **Step 1: Write the failing tests** `python/tests/lifecycle/test_move.py`. Build the study from the `valid_files` fixture of `python/tests/conftest.py` in `tmp_path/studies/caffeine/Example`, add `Example_Tab9.tsv` (a raw table: headerless grid, see `studyformat/raw.py`), `Example_Fig1.wpd.json` (copy a fixture project from `python/tests/digitize_fixtures.py`), and a `review.json` item whose target file is `Example_Fig1.wpd.json` (add it with `pkdb.studyformat.review_edit.add_item`):

```python
from pathlib import Path

import pytest

from pkdb.lifecycle.move import MoveRefused, move_study
from pkdb.studyformat.review_edit import read_review
from pkdb.studyformat.validation import validate_folder


def test_a_move_renames_the_folder_and_every_file_of_the_study(moved_checkout, sf_vocabulary):
    root = moved_checkout
    result = move_study(root, "caffeine/Example", "codeine/Renamed", sf_vocabulary)
    folder = root / "studies" / "codeine" / "Renamed"
    assert result.folder == folder and not (root / "studies" / "caffeine").exists()
    names = sorted(p.name for p in folder.iterdir())
    assert "Renamed.pdf" in names and "Renamed_Tab1.png" in names
    assert "Renamed_Tab9.tsv" in names and "Renamed_Fig1.wpd.json" in names
    assert not [n for n in names if n.startswith("Example")]
    [item] = read_review(folder).review.items
    assert item.target.file == "Renamed_Fig1.wpd.json"
    assert "\tRenamed\t" in (folder / "subjects.tsv").read_text(encoding="utf-8") or "Renamed" in (folder / "subjects.tsv").read_text(encoding="utf-8").splitlines()[1]
    assert not [i for i in validate_folder(folder, sf_vocabulary).issues if i.severity == "error"]


def test_an_existing_target_is_refused(moved_checkout, sf_vocabulary):
    (moved_checkout / "studies" / "codeine" / "Renamed").mkdir(parents=True)
    with pytest.raises(MoveRefused, match="exists"):
        move_study(moved_checkout, "caffeine/Example", "codeine/Renamed", sf_vocabulary)
    assert (moved_checkout / "studies" / "caffeine" / "Example").is_dir()


def test_an_open_workbook_refuses_the_move(moved_checkout, sf_vocabulary):
    folder = moved_checkout / "studies" / "caffeine" / "Example"
    ...  # generate the workbook with sync_study(folder, sf_vocabulary), add the LibreOffice lock file ".~lock.Example.xlsx#"
    with pytest.raises(MoveRefused, match="open"):
        move_study(moved_checkout, "caffeine/Example", "codeine/Renamed", sf_vocabulary)


def test_a_workbook_with_unsynced_edits_refuses_the_move(moved_checkout, sf_vocabulary):
    folder = moved_checkout / "studies" / "caffeine" / "Example"
    ...  # generate the workbook, then change one cell with openpyxl and save it
    with pytest.raises(MoveRefused, match="pkdb tables sync"):
        move_study(moved_checkout, "caffeine/Example", "codeine/Renamed", sf_vocabulary)
    assert (folder / "Example.xlsx").exists()


def test_a_synced_workbook_is_removed(moved_checkout, sf_vocabulary):
    ...  # generate the workbook, move, assert no .xlsx and no .pkdb-base state file in the new folder
```

Write the elided setup lines fully, using the workbook helpers the tests of `python/tests/studyformat/test_workbook_*.py` and `test_tables_cli.py` use (generate with `sync_study`, edit with openpyxl). Replace the loose `subjects.tsv` assertion by an exact check of the `study` column with `pkdb.studyformat` table reading. Add CLI tests with the fake GitHub: the issue is renamed with a token; without a token the move succeeds and warns.

- [ ] **Step 2: Run to verify they fail**: `uv run --locked pytest -q tests/lifecycle/test_move.py` -> FAIL.

- [ ] **Step 3: Implement** `move.py` and the `move` command. Docs: command row `| pkdb move OLD NEW | Rename or move a study with its files, review targets and GitHub issue |` and a paragraph (workbook refusal and regeneration, the server keeps the study's row through its issue number on the next upload, the old identifier answers 404). Build the docs.

- [ ] **Step 4: Run** `uv run --locked pytest -q tests/lifecycle tests/issues` -> PASS; full suite, ruff, ty.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/lifecycle/move.py python/src/pkdb/lifecycle_cli.py python/tests/lifecycle/test_move.py docs/python-client.md
git commit -m "Rename and move studies with pkdb move"
```

- [ ] **Step 6: Release note after the pull request exists**

Add to the top of `release-notes/unreleased.md`:

```markdown
- Create, move, release and list study format 2 studies (#N). `pkdb new <substance>/<name>` writes a draft study with `study.json`, `reference.json`, `subjects.tsv` and `review.json`, takes the PDF and images from `papers/`, and creates or adopts its GitHub issue; `pkdb move` renames a study with its files, review targets and issue; `pkdb release` gives approved studies the next PKDB identifiers; `pkdb registry` lists released studies and `--check` fails on a shared identifier or issue number. An upload of a moved study keeps its stored row through its issue number, and issue numbers are unique among studies (migration `p007issueunique`).
```

Commit it as "Add the release note of the study lifecycle commands" and push.

---

## Self-Review

- **Spec coverage (section 6):** `pkdb new` with required licence and access, name refusal, papers move, creator and provenance, `reference.json`, `subjects.tsv`, draft review, issue create or adopt, `--no-issue` (Tasks 4, 5); `pkdb move` with refusals, file renames, review targets, `format`, issue rename and warning (Task 6; the `.wpd.json` rewrite of the spec is not needed because the file holds no image name, stated in the plan decisions); `pkdb release` with checks, numbering and date (Task 3); `pkdb registry` and `--check` (Task 2); repository discovery and `--root` (Tasks 2 to 6); server takeover by issue and the unique index with its migration (Task 1). Section 8 "Lifecycle" and "Backend" are covered by the tests of Tasks 1 to 6.
- **Placeholders:** the `...` lines in Task 3's third test and Task 6's workbook tests are setup steps described in words with the helpers to use; the implementer writes them fully (the plan names the helpers and files).
- **Types:** `parse_location`, `Scan`, `Released`, `next_identifier`, `identifier`, `ReleaseRefused`, `NewStudy`, `NewStudyRefused`, `issue_for_new_study`, `rename_issue`, `Moved`, `MoveRefused` are the same in every task that uses them.
