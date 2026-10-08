---
search:
  exclude: true
---

# Study format 2 migration, part A: converter, equivalence gate and report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `pkdb migrate` converts study format 1 folders of pkdb_data into study format 2 folders, proves each conversion with an equivalence gate against the current v1 parser, replaces only proven folders in place, moves folders without `study.json` to `papers/`, and writes a JSON and a Markdown report for review.

**Architecture:** A new package `python/src/pkdb/migration/` converts from the entities that the v1 importer already resolved (`importers/folder.load_folder` and `parse_bundle`), never from the template mini-language. The converter is the inverse of the format 2 reader (`studyformat/reader.py`): it writes table rows, images, `study.json`, `reference.json` and `review.json` into a work folder and formats it with `format_folder`. The gate prepares the v1 folder (A) and the converted folder (B) with today's `prepare()`, normalizes both canonical studies and compares them with a relative tolerance of 1e-9 after the intended transformations. A runner walks the given paths, converts studies in a process pool, swaps proven studies into place one at a time, and writes the report.

**Tech Stack:** Python 3.14, Pydantic 2, openpyxl 3.1, Pillow 12 (new direct dependency, already locked through matplotlib), argparse, pytest, ruff, ty.

**Spec:** `docs/superpowers/specs/2026-10-08-study-format-v2-05-migration-design.md` (sections 2, 3, 4, 7, 8) and `docs/superpowers/specs/2026-10-05-study-format-v2-design.md` (sections 4, 5, 6, 7, 15.1, 15.2, 15.3).

## Global Constraints

- **Python:** 3.14. Run from `python/`: `uv run --locked pytest -q -x`, `uv run --locked ruff check .`, `uv run --locked ruff format --check .`, `uv run --locked ty check`. Every commit keeps them green.
- **Docs:** when a Markdown file changes, run `uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean` from the repository root; it must print no warning.
- **Writing:** never use the em dash character; Markdown paragraphs on one source line; no attribution lines in commits, docs or code; user-facing text in plain, short English sentences.
- **Generated files:** never hand-edit `docs/study-format.md`, any `CHANGELOG.md`, or the curation contract fixtures.
- **pkdb_data is never written by tests.** Unit tests build synthetic v1 folders in `tmp_path`. The opt-in corpus test copies studies from `PKDB_STUDY_CORPUS` into `tmp_path` before it converts anything.
- **No new data copies:** the real studies `acetaminophen/Abernethy1982` and `caffeine/Harder1988` have licence `closed`; nothing of them goes into the repository.
- **v1 reading:** the converter reads v1 data only through `load_folder`, `parse_bundle` and, for formulas, openpyxl on the same workbook. It never re-implements template expansion.
- **Format 2 writing:** tables through `TABLES[kind].names` and `render_tsv`, numbers through `format_number`, `study.json` through `StudyMetadata` and `canonical_study_json`, `review.json` through `Review` and `canonical_review_json`, then `format_folder`.
- **Tolerance:** numbers compare with a relative tolerance of 1e-9 (`math.isclose(a, b, rel_tol=1e-9, abs_tol=0)`), text compares exactly.
- **Write mode:** only `identical` and `intended` studies replace their v1 folder. `--dry-run` writes only the report.

## Review Focus

1. **A run that is interrupted while it swaps a study** (Ctrl-C, a crash): the study must afterwards be either the complete v1 folder or the complete format 2 folder, and the next run must finish or undo the swap and say so. Test in Task 8 (`test_an_interrupted_swap_is_restored_on_the_next_run`).
2. **A second run after a partial run:** format 2 folders are skipped and listed, never converted again or deleted, and studies that stayed v1 are tried again. Test in Task 8 (`test_a_rerun_skips_converted_studies_and_retries_the_rest`).
3. **Cell text that format 2 cannot hold:** v1 comments with line breaks or tabs, names with `;` or `,`, a group and an individual with one name. The converter writes one line per row or refuses the study with a reason, and never crashes the run. Tests in Task 3 (`test_comments_lose_line_breaks_and_tabs`, `test_subject_names_that_format_2_cannot_hold_refuse_the_study`).
4. **An exception inside the converter or the gate for one study** (a bug, an unreadable workbook): the run goes on, the study stays v1 and is listed as `not_converted` with reason `converter_error` and the exception text. Test in Task 8 (`test_an_exception_in_one_study_does_not_stop_the_run`).
5. **A stale hidden TSV beside a workbook:** v1 reads the workbook, so the converter must use the workbook rows and remove the stale TSV, and the gate must agree. Test in Task 5 (`test_a_stale_hidden_tsv_beside_the_workbook_is_ignored_and_removed`).

---

## File Structure

| File | Responsibility |
|---|---|
| `python/src/pkdb/migration/__init__.py` | Package docstring only. |
| `python/src/pkdb/migration/model.py` | Shared types: `NotConverted`, `Decision`, `Change`, `Difference`, `StudyResult`, `PaperMove`, `RegistryFindings`, `MigrationReport`. |
| `python/src/pkdb/migration/registry.py` | Read `study_identifiers.json`; release per study location; registry findings. |
| `python/src/pkdb/migration/metadata.py` | v1 `study.json` to `StudyMetadata` and `Review`; section notes to table notes. |
| `python/src/pkdb/migration/sources.py` | Source of a row or an image; image copy and JPG to PNG conversion. |
| `python/src/pkdb/migration/rows.py` | Table rows of a parsed v1 study: subjects, characteristica, interventions, outputs, timecourses, scatters. |
| `python/src/pkdb/migration/formulas.py` | `ABS(X - mean)` error bars from the workbook formulas. |
| `python/src/pkdb/migration/convert.py` | `convert_study`: one v1 folder into a format 2 work folder. |
| `python/src/pkdb/migration/gate.py` | Equivalence gate: normalization, intended changes, differences, class. |
| `python/src/pkdb/migration/report.py` | `migration.json` and `migration.md`. |
| `python/src/pkdb/migration/run.py` | `migrate`: discovery, paper moves, process pool, atomic swaps, recovery, registry deletion. |
| `python/src/pkdb/migration_cli.py` | `pkdb migrate` command. |
| `python/src/pkdb/cli.py` | Register and dispatch `migrate`. |
| `python/pyproject.toml`, `python/uv.lock` | Direct dependency `pillow>=12.3.0,<13`. |
| `python/tests/migration_fixtures.py` | Builders of synthetic v1 studies. |
| `python/tests/migration/test_*.py` | Tests per module. |
| `python/tests/test_migration_corpus.py` | Opt-in corpus test (`PKDB_STUDY_CORPUS`). |
| `docs/study-format-2-cutover.md` | Cutover runbook. |
| `zensical.toml` | Navigation entry of the runbook. |

---

### Task 1: Report types, registry and metadata

**Files:**
- Create: `python/src/pkdb/migration/__init__.py`, `python/src/pkdb/migration/model.py`, `python/src/pkdb/migration/registry.py`, `python/src/pkdb/migration/metadata.py`
- Create: `python/tests/migration/__init__.py` (empty), `python/tests/migration/test_registry.py`, `python/tests/migration/test_metadata.py`

**Interfaces:**
- Consumes: `pkdb.schemas.review.Release`, `Review`, `User`; `pkdb.studyformat.models.StudyMetadata`, `StudyReference`, `Curator`, `Comment`, `Notes`, `canonical_study_json`, `canonical_review_json`.
- Produces:
  - `model.NotConverted(code: str, message: str)` exception with attributes `code`, `message`.
  - `model.Decision(kind: str, detail: str)`, `model.Change(kind: str, count: int, examples: list[str])`, `model.Difference(path: str, a: str, b: str)` (Pydantic models, `extra="forbid"`).
  - `model.Outcome = Literal["identical", "intended", "mismatch", "invalid_v1", "not_converted"]`.
  - `model.StudyResult(study: str, outcome: Outcome, reason: str | None = None, changes: list[Change] = [], differences: list[Difference] = [], issues: list[str] = [], decisions: list[Decision] = [], written: bool = False)`.
  - `model.PaperMove(source: str, target: str, files: list[str], workbook: bool)`, `model.RegistryFindings(double_identifiers: dict[str, list[str]] = {}, missing_paths: list[str] = [], deleted: bool = False)`, `model.MigrationReport(dry_run: bool, studies: list[StudyResult] = [], skipped: list[str] = [], papers: list[PaperMove] = [], removed_empty: list[str] = [], recovered: list[str] = [], registry: RegistryFindings)`.
  - `registry.Registry` with `Registry.read(path: Path | None) -> Registry`, `release(location: str) -> Release | None` (raises `NotConverted("double_identifier", ...)` when a location has two identifiers), `identifiers -> dict[str, str]` (pkdb_id to location), `findings(root: Path) -> RegistryFindings`.
  - `metadata.study_metadata(v1: dict, reference: dict, release: Release | None, creator_fallback: str) -> tuple[StudyMetadata, list[Decision]]`.
  - `metadata.review(release: Release | None, approver: str | None) -> Review`.

- [ ] **Step 1: Write the failing registry tests**

`python/tests/migration/test_registry.py`:

```python
import json
from datetime import date

import pytest

from pkdb.migration.model import NotConverted
from pkdb.migration.registry import Registry


def write(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_the_release_of_a_registered_study(tmp_path):
    registry = Registry.read(
        write(tmp_path / "ids.json", {"PKDB01237": ["albuterol/Guo2016", "2026-09-28"]})
    )
    release = registry.release("albuterol/Guo2016")
    assert release is not None
    assert (release.pkdb_id, release.date) == ("PKDB01237", date(2026, 9, 28))
    assert registry.release("albuterol/Other2000") is None


def test_no_registry_releases_nothing():
    assert Registry.read(None).release("caffeine/Example") is None


def test_two_identifiers_of_one_study_refuse_it(tmp_path):
    registry = Registry.read(
        write(
            tmp_path / "ids.json",
            {
                "PKDB00001": ["caffeine/Example", "2020-01-01"],
                "PKDB00002": ["caffeine/Example", "2021-01-01"],
            },
        )
    )
    with pytest.raises(NotConverted) as error:
        registry.release("caffeine/Example")
    assert error.value.code == "double_identifier"
    assert "PKDB00001" in error.value.message and "PKDB00002" in error.value.message


def test_findings_name_double_identifiers_and_missing_paths(tmp_path):
    root = tmp_path
    (root / "studies" / "caffeine" / "Example").mkdir(parents=True)
    registry = Registry.read(
        write(
            tmp_path / "ids.json",
            {
                "PKDB00001": ["caffeine/Example", "2020-01-01"],
                "PKDB00002": ["caffeine/Example", "2021-01-01"],
                "PKDB00003": ["caffeine/Gone1999", "2021-01-01"],
            },
        )
    )
    findings = registry.findings(root)
    assert findings.double_identifiers == {"caffeine/Example": ["PKDB00001", "PKDB00002"]}
    assert findings.missing_paths == ["caffeine/Gone1999"]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/migration/test_registry.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkdb.migration'`.

- [ ] **Step 3: Implement `model.py` and `registry.py`**

`python/src/pkdb/migration/__init__.py`:

```python
"""Conversion of study format 1 folders into study format 2 (`pkdb migrate`)."""
```

`python/src/pkdb/migration/model.py`:

```python
"""Results of a migration run, shared by the converter, the gate, the runner and the report."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Outcome = Literal["identical", "intended", "mismatch", "invalid_v1", "not_converted"]


class NotConverted(Exception):
    """The converter cannot write a study; `code` names the reason in the report."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Decision(Model):
    """Something a person should check by hand, such as a converted dosing schedule."""

    kind: str
    detail: str


class Change(Model):
    """An intended change of the conversion, counted per kind with a few examples."""

    kind: str
    count: int
    examples: list[str] = Field(default_factory=list)


class Difference(Model):
    """A difference between the v1 study (A) and the converted study (B)."""

    path: str
    a: str
    b: str


class StudyResult(Model):
    study: str
    outcome: Outcome
    reason: str | None = None
    changes: list[Change] = Field(default_factory=list)
    differences: list[Difference] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    written: bool = False


class PaperMove(Model):
    """A folder without study.json moved to papers/."""

    source: str
    target: str
    files: list[str]
    workbook: bool


class RegistryFindings(Model):
    double_identifiers: dict[str, list[str]] = Field(default_factory=dict)
    missing_paths: list[str] = Field(default_factory=list)
    deleted: bool = False


class MigrationReport(Model):
    dry_run: bool
    studies: list[StudyResult] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)
    papers: list[PaperMove] = Field(default_factory=list)
    removed_empty: list[str] = Field(default_factory=list)
    recovered: list[str] = Field(default_factory=list)
    registry: RegistryFindings = Field(default_factory=RegistryFindings)
```

`python/src/pkdb/migration/registry.py`:

```python
"""The registry `studies/study_identifiers.json` of released format 1 studies."""

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from pkdb.migration.model import NotConverted, RegistryFindings
from pkdb.schemas.review import Release


@dataclass(frozen=True)
class Registry:
    """PKDB identifiers with the `<substance>/<name>` location and the release date."""

    entries: dict[str, tuple[str, date]] = field(default_factory=dict)

    @classmethod
    def read(cls, path: Path | None) -> "Registry":
        if path is None:
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            {
                pkdb_id: (location, date.fromisoformat(day))
                for pkdb_id, (location, day) in sorted(data.items())
            }
        )

    @property
    def identifiers(self) -> dict[str, str]:
        return {pkdb_id: location for pkdb_id, (location, _) in self.entries.items()}

    def _by_location(self) -> dict[str, list[str]]:
        located = defaultdict(list)
        for pkdb_id, (location, _) in self.entries.items():
            located[location].append(pkdb_id)
        return located

    def release(self, location: str) -> Release | None:
        ids = self._by_location().get(location, [])
        if len(ids) > 1:
            raise NotConverted(
                "double_identifier",
                f"{location} has the PKDB identifiers {', '.join(ids)} in the registry; "
                "keep one",
            )
        if not ids:
            return None
        return Release(pkdb_id=ids[0], date=self.entries[ids[0]][1])

    def findings(self, root: Path) -> RegistryFindings:
        """Studies with two identifiers and locations without a folder below root/studies."""
        located = self._by_location()
        return RegistryFindings(
            double_identifiers={
                location: ids for location, ids in sorted(located.items()) if len(ids) > 1
            },
            missing_paths=sorted(
                location
                for location in located
                if not (root / "studies" / location).is_dir()
            ),
        )
```

- [ ] **Step 4: Run the registry tests to verify they pass**

Run: `cd python && uv run --locked pytest -q tests/migration/test_registry.py`
Expected: 4 passed.

- [ ] **Step 5: Write the failing metadata tests**

Read first: `python/src/pkdb/studyformat/models.py` (StudyMetadata, Curator, Comment, Notes, StudyReference, ReferenceSnapshot), `python/src/pkdb/schemas/provenance.py`, and the v1 metadata parsing in `python/src/pkdb/importers/folder.py:307-360` (curators as `[user, rating]`, string or dict; comments as `[user, text]` or text; section notes in `groupset`, `individualset`, `interventionset`, `outputset`, `dataset`).

`python/tests/migration/test_metadata.py`:

```python
from datetime import UTC, date, datetime

from pkdb.migration.metadata import review, study_metadata
from pkdb.schemas.review import Release
from pkdb.studyformat.models import canonical_review_json, canonical_study_json

V1 = {
    "sid": "PKDB00198",
    "name": "Harder1988",
    "reference": "3402561",
    "date": "2020-05-05",
    "creator": "mkoenig",
    "curators": [["mkoenig", 1], ["janekg", 0.5], "dimitra"],
    "collaborators": ["Jan Grzegorzewski"],
    "licence": "closed",
    "access": "public",
    "descriptions": ["Caffeine pharmacokinetics.\nSecond line."],
    "comments": [["janekg", "Check Fig2"], "No user"],
    "groupset": {"descriptions": ["Healthy volunteers"], "groups": []},
    "individualset": {"comments": [["mkoenig", "Ages from Tab1"]], "individuals": []},
    "outputset": {"descriptions": ["Plasma"], "outputs": []},
}
REFERENCE = {"sid": "3402561", "name": "Harder1988", "pmid": "3402561", "doi": "10.1111/x.1"}


def test_study_json_from_v1_metadata():
    metadata, decisions = study_metadata(
        V1,
        REFERENCE,
        Release(pkdb_id="PKDB00198", date=date(2020, 5, 5)),
        creator_fallback="mkoenig",
    )
    assert metadata.reference is not None
    assert (metadata.reference.pmid, metadata.reference.doi) == ("3402561", "10.1111/x.1")
    assert metadata.creator == "mkoenig"
    assert [(c.user, c.rating) for c in metadata.curators] == [
        ("mkoenig", 1),
        ("janekg", 0.5),
        ("dimitra", 0),
    ]
    assert metadata.collaborators == ["Jan Grzegorzewski"]
    assert (metadata.licence, metadata.access) == ("closed", "public")
    assert metadata.release is not None and metadata.release.pkdb_id == "PKDB00198"
    # Line breaks become spaces: study.json texts are single lines in the app.
    assert metadata.descriptions == ["Caffeine pharmacokinetics. Second line."]
    # A comment without a user is the creator's.
    assert [(c.user, c.text) for c in metadata.comments] == [
        ("janekg", "Check Fig2"),
        ("mkoenig", "No user"),
    ]
    # groupset and individualset both describe subjects.
    assert metadata.notes["subjects"].descriptions == ["Healthy volunteers"]
    assert [c.text for c in metadata.notes["subjects"].comments] == ["Ages from Tab1"]
    assert metadata.notes["outputs"].descriptions == ["Plasma"]
    assert decisions == []
    canonical_study_json(metadata)  # serializes


def test_a_v1_date_other_than_the_release_date_is_a_decision():
    _, decisions = study_metadata(
        V1,
        REFERENCE,
        Release(pkdb_id="PKDB00198", date=date(2021, 1, 1)),
        creator_fallback="mkoenig",
    )
    assert [d.kind for d in decisions] == ["registry_date"]
    assert "2020-05-05" in decisions[0].detail and "2021-01-01" in decisions[0].detail


def test_a_pkdb_sid_that_the_registry_does_not_hold_is_a_decision():
    _, decisions = study_metadata(V1, REFERENCE, None, creator_fallback="mkoenig")
    assert [d.kind for d in decisions] == ["registry_sid"]


def test_a_reference_without_pmid_or_doi_is_a_manual_reference():
    v1 = {**V1, "reference": "Harder1988"}
    metadata, _ = study_metadata(
        v1, {"sid": "Harder1988", "name": "Harder1988"}, None, creator_fallback="x"
    )
    assert metadata.reference is None


def test_registered_studies_are_approved_by_the_approver_on_the_release_date():
    released = review(Release(pkdb_id="PKDB00198", date=date(2020, 5, 5)), "mkoenig")
    assert released.status == "approved"
    assert released.reviewers == ["mkoenig"]
    assert released.approved_by == "mkoenig"
    assert released.approved == datetime(2020, 5, 5, tzinfo=UTC)
    assert review(None, "mkoenig").status == "draft"
    assert review(None, None).reviewers == []
    canonical_review_json(released)
```

- [ ] **Step 6: Run them to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/migration/test_metadata.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkdb.migration.metadata'`.

- [ ] **Step 7: Implement `metadata.py`**

```python
"""study.json and review.json of a converted study from its format 1 study.json."""

import re
from datetime import UTC, datetime, time

from pkdb.migration.model import Decision
from pkdb.schemas.provenance import ManualCuration
from pkdb.schemas.review import Release, Review
from pkdb.studyformat.models import Comment, Curator, Notes, StudyMetadata, StudyReference

# Format 1 sections and the table kind whose notes they become.
SECTION_KINDS = {
    "groupset": "subjects",
    "individualset": "subjects",
    "interventionset": "interventions",
    "outputset": "outputs",
    "dataset": "scatters",
}
PKDB_ID = re.compile(r"PKDB[0-9]{5}")
PMID = re.compile(r"[1-9][0-9]*")


def single_line(text: object) -> str:
    """Text on one line: format 2 cells and study.json texts hold no line breaks or tabs."""
    return " ".join(str(text).split())


def _comments(values: object, user: str) -> list[Comment]:
    pairs = []
    for value in values or []:
        if isinstance(value, list) and len(value) == 2:
            pairs.append((str(value[0]), single_line(value[1])))
        elif isinstance(value, dict):
            pairs.append((str(value.get("user") or user), single_line(value["text"])))
        else:
            pairs.append((user, single_line(value)))
    return [Comment(user=author, text=text) for author, text in pairs if text]


def _descriptions(values: object) -> list[str]:
    texts = [single_line(v["text"] if isinstance(v, dict) else v) for v in values or []]
    return [text for text in texts if text]


def _curators(values: object) -> list[Curator]:
    curators = []
    for value in values or []:
        if isinstance(value, str):
            curators.append(Curator(user=value))
        elif isinstance(value, list):
            curators.append(Curator(user=value[0], rating=value[1]))
        else:
            curators.append(Curator.model_validate(value))
    return curators


def _reference(v1: dict, reference: dict) -> StudyReference | None:
    pmid = next(
        (
            str(value)
            for value in (reference.get("pmid"), v1.get("reference"))
            if value is not None and PMID.fullmatch(str(value))
        ),
        None,
    )
    doi = reference.get("doi") or None
    if pmid is None and doi is None:
        return None
    return StudyReference(pmid=pmid, doi=doi)


def study_metadata(
    v1: dict, reference: dict, release: Release | None, *, creator_fallback: str
) -> tuple[StudyMetadata, list[Decision]]:
    """The metadata of the converted study and what a person should check."""
    creator = str(v1.get("creator") or creator_fallback)
    notes: dict[str, Notes] = {}
    for section, kind in SECTION_KINDS.items():
        content = v1.get(section) or {}
        descriptions = _descriptions(content.get("descriptions"))
        comments = _comments(content.get("comments"), creator)
        if descriptions or comments:
            merged = notes.setdefault(kind, Notes())
            merged.descriptions.extend(descriptions)
            merged.comments.extend(comments)
    decisions = []
    sid = str(v1.get("sid", ""))
    if release is not None and v1.get("date") and str(v1["date"]) != release.date.isoformat():
        decisions.append(
            Decision(
                kind="registry_date",
                detail=f"study.json date {v1['date']}, registry date {release.date.isoformat()}",
            )
        )
    if release is None and PKDB_ID.fullmatch(sid):
        decisions.append(
            Decision(kind="registry_sid", detail=f"study.json sid {sid} is not in the registry")
        )
    elif release is not None and PKDB_ID.fullmatch(sid) and sid != release.pkdb_id:
        decisions.append(
            Decision(
                kind="registry_sid",
                detail=f"study.json sid {sid}, registry identifier {release.pkdb_id}",
            )
        )
    provenance = v1.get("provenance")
    metadata = StudyMetadata.model_validate(
        {
            "format": 2,
            "reference": _reference(v1, reference),
            "creator": creator,
            "curators": _curators(v1.get("curators")),
            "collaborators": [single_line(c) for c in v1.get("collaborators") or []],
            "licence": v1.get("licence", "closed"),
            "access": v1.get("access", "private"),
            "provenance": provenance if provenance else ManualCuration(),
            "release": release,
            "descriptions": _descriptions(v1.get("descriptions")),
            "comments": _comments(v1.get("comments"), creator),
            "notes": notes,
        }
    )
    return metadata, decisions


def review(release: Release | None, approver: str | None) -> Review:
    """Released studies are approved by the approver on their release date; others are drafts."""
    if release is None:
        return Review(status="draft")
    assert approver is not None, "a registered study needs an approver"
    return Review(
        status="approved",
        reviewers=[approver],
        approved_by=approver,
        approved=datetime.combine(release.date, time(), UTC),
    )
```

If `StudyMetadata` refuses a v1 field value (for example a licence outside `open` and `closed`), let the `ValidationError` propagate; Task 5 turns it into `NotConverted("metadata", ...)`.

- [ ] **Step 8: Run the tests to verify they pass, then lint and types**

Run: `cd python && uv run --locked pytest -q tests/migration && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked ty check`
Expected: 9 passed; no lint or type errors.

- [ ] **Step 9: Commit**

```bash
git add python/src/pkdb/migration python/tests/migration
git commit -m "Read the study registry and map format 1 metadata for pkdb migrate"
```

---

### Task 2: Sources and images

**Files:**
- Create: `python/src/pkdb/migration/sources.py`, `python/tests/migration/test_sources.py`
- Modify: `python/pyproject.toml` (dependencies), `python/uv.lock`

**Interfaces:**
- Consumes: `pkdb.schemas.source.SourceLocation`; `pkdb.studyformat.tables.SOURCE_PATTERN`, `TEXT_SOURCE`, `image_file`; `model.NotConverted`, `model.Decision`.
- Produces:
  - `sources.sheet_of(location: SourceLocation, study: str) -> str | None`: the v1 sheet of a row; None for an entity of `study.json`.
  - `sources.image_source(image: str | None, study: str) -> str | None`: `Example_Fig1.png` gives `Fig1`; None when the name does not start with `<study>_` or has no source after it.
  - `sources.observation_source(location: SourceLocation, image: str | None, study: str) -> str`: source of a row of an outputs, timecourses or scatters table; raises `NotConverted("sheet_name", ...)` or `NotConverted("image_name", ...)`.
  - `sources.curator_source(location: SourceLocation, image: str | None, study: str) -> str`: source column of subjects, interventions and characteristica rows.
  - `sources.copy_images(v1: Path, target: Path, study: str, used: set[str]) -> list[Decision]`: writes `<study>_<source>.png` for every used source except `Text`; converts JPG; raises `NotConverted("missing_image", ...)` or `NotConverted("image_type", ...)`.
  - `sources.IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg")`.

- [ ] **Step 1: Add Pillow as a direct dependency**

In `python/pyproject.toml`, add to `dependencies` after the `matplotlib` line:

```toml
  "pillow>=12.3.0,<13",
```

Run: `cd python && uv lock && uv sync --locked`
Expected: `uv.lock` changes only in the dependency list of `pkdb` (Pillow 12.3.0 is already locked).

- [ ] **Step 2: Write the failing tests**

`python/tests/migration/test_sources.py`:

```python
import pytest
from PIL import Image

from pkdb.migration.model import NotConverted
from pkdb.migration.sources import (
    copy_images,
    curator_source,
    image_source,
    observation_source,
    sheet_of,
)
from pkdb.schemas.source import SourceLocation

WORKBOOK = SourceLocation(file="Example.xlsx", sheet="Fig1", row=3)
HIDDEN = SourceLocation(file=".Example_Tab2.tsv", row=3)
PLAIN = SourceLocation(file="Results.tsv", row=3)
INLINE = SourceLocation(file="study.json", path=("outputset", "outputs", 0))


def test_the_sheet_of_a_row():
    assert sheet_of(WORKBOOK, "Example") == "Fig1"
    assert sheet_of(HIDDEN, "Example") == "Tab2"
    assert sheet_of(PLAIN, "Example") == "Results"
    assert sheet_of(INLINE, "Example") is None


def test_the_source_of_an_image():
    assert image_source("Example_Fig1.png", "Example") == "Fig1"
    assert image_source("Example_TabS1.jpg", "Example") == "TabS1"
    assert image_source("Other_Fig1.png", "Example") is None
    assert image_source(None, "Example") is None


def test_observation_rows_take_the_sheet_or_the_image_or_text():
    assert observation_source(WORKBOOK, None, "Example") == "Fig1"
    assert observation_source(INLINE, "Example_Fig3.png", "Example") == "Fig3"
    assert observation_source(INLINE, None, "Example") == "Text"


def test_a_sheet_outside_the_source_pattern_refuses_the_study():
    with pytest.raises(NotConverted) as error:
        observation_source(PLAIN, None, "Example")
    assert error.value.code == "sheet_name"
    assert "Results" in error.value.message


def test_an_inline_image_outside_the_naming_refuses_the_study():
    with pytest.raises(NotConverted) as error:
        observation_source(INLINE, "figure.png", "Example")
    assert error.value.code == "image_name"


def test_curator_sources_fall_back_to_the_image_then_empty():
    groups = SourceLocation(file="Example.xlsx", sheet="TabGroups", row=3)
    assert curator_source(groups, "Example_Tab1.png", "Example") == "Tab1"
    assert curator_source(groups, None, "Example") == ""
    assert curator_source(WORKBOOK, None, "Example") == "Fig1"
    assert curator_source(INLINE, None, "Example") == "Text"


def test_images_are_copied_and_jpg_becomes_png(tmp_path):
    v1, target = tmp_path / "v1", tmp_path / "v2"
    v1.mkdir()
    target.mkdir()
    (v1 / "Example_Fig1.png").write_bytes(b"\x89PNG data")
    Image.new("RGB", (4, 3), "red").save(v1 / "Example_Tab1.jpg")
    decisions = copy_images(v1, target, "Example", {"Fig1", "Tab1", "Text"})
    assert (target / "Example_Fig1.png").read_bytes() == b"\x89PNG data"
    with Image.open(target / "Example_Tab1.png") as image:
        assert (image.format, image.size) == ("PNG", (4, 3))
    assert [(d.kind, d.detail) for d in decisions] == [
        ("image_converted", "Example_Tab1.jpg to Example_Tab1.png")
    ]


def test_a_missing_or_unsupported_image_refuses_the_study(tmp_path):
    v1, target = tmp_path / "v1", tmp_path / "v2"
    v1.mkdir()
    target.mkdir()
    with pytest.raises(NotConverted) as missing:
        copy_images(v1, target, "Example", {"Fig1"})
    assert missing.value.code == "missing_image"
    (v1 / "Example_Fig1.svg").write_text("<svg/>")
    with pytest.raises(NotConverted) as unsupported:
        copy_images(v1, target, "Example", {"Fig1"})
    assert unsupported.value.code == "image_type"
```

- [ ] **Step 3: Run them to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/migration/test_sources.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkdb.migration.sources'`.

- [ ] **Step 4: Implement `sources.py`**

```python
"""The source of each converted row, and the images of the sources."""

import shutil
from pathlib import Path

from PIL import Image

from pkdb.migration.model import Decision, NotConverted
from pkdb.schemas.source import SourceLocation
from pkdb.studyformat.tables import SOURCE_PATTERN, TEXT_SOURCE, image_file

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg")
STUDY_JSON = "study.json"


def sheet_of(location: SourceLocation, study: str) -> str | None:
    """The workbook sheet or TSV file of a format 1 row; None for an entity of study.json."""
    if location.file == STUDY_JSON:
        return None
    if location.sheet is not None:
        return location.sheet
    stem = location.file.removesuffix(".tsv")
    hidden = f".{study}_"
    return stem.removeprefix(hidden) if stem.startswith(hidden) else stem


def image_source(image: str | None, study: str) -> str | None:
    """`Fig1` of `<study>_Fig1.png`; None for another name."""
    if not image:
        return None
    stem = Path(image).stem
    prefix = f"{study}_"
    source = stem.removeprefix(prefix) if stem.startswith(prefix) else ""
    return source or None


def observation_source(location: SourceLocation, image: str | None, study: str) -> str:
    """The source of a row of an outputs, timecourses or scatters table, which names its file."""
    sheet = sheet_of(location, study)
    if sheet is not None:
        if not SOURCE_PATTERN.fullmatch(sheet):
            raise NotConverted(
                "sheet_name",
                f"Sheet {sheet} is not a source name such as Tab2 or Fig3A; rename it",
            )
        return sheet
    if image is None:
        return TEXT_SOURCE
    source = image_source(image, study)
    if source is None or not SOURCE_PATTERN.fullmatch(source):
        raise NotConverted(
            "image_name",
            f"Image {image} is not named {study}_<source> with a source such as Fig3A",
        )
    return source


def curator_source(location: SourceLocation, image: str | None, study: str) -> str:
    """The `source` column of subjects, interventions and characteristica: curator data."""
    sheet = sheet_of(location, study)
    if sheet is not None and SOURCE_PATTERN.fullmatch(sheet):
        return sheet
    source = image_source(image, study)
    if source is not None and SOURCE_PATTERN.fullmatch(source):
        return source
    return TEXT_SOURCE if sheet is None else ""


def copy_images(v1: Path, target: Path, study: str, used: set[str]) -> list[Decision]:
    """Write `<study>_<source>.png` for each used source; JPG images are converted."""
    decisions = []
    for source in sorted(used - {TEXT_SOURCE, ""}):
        name = image_file(study, source)
        candidates = {
            path.suffix.lower(): path
            for path in v1.glob(f"{study}_{source}.*")
            if path.stem == f"{study}_{source}"
        }
        if ".png" in candidates:
            shutil.copyfile(candidates[".png"], target / name)
        elif jpg := candidates.get(".jpg") or candidates.get(".jpeg"):
            with Image.open(jpg) as image:
                image.save(target / name, format="PNG")
            decisions.append(
                Decision(kind="image_converted", detail=f"{jpg.name} to {name}")
            )
        elif candidates:
            found = ", ".join(sorted(path.name for path in candidates.values()))
            raise NotConverted(
                "image_type", f"The image of {source} is {found}; convert it to PNG"
            )
        else:
            raise NotConverted("missing_image", f"No image {name} for source {source}")
    return decisions
```

- [ ] **Step 5: Run the tests, lint and types**

Run: `cd python && uv run --locked pytest -q tests/migration && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked ty check`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add python/pyproject.toml python/uv.lock python/src/pkdb/migration/sources.py python/tests/migration/test_sources.py
git commit -m "Name the sources of converted rows and convert their images to PNG"
```

---

### Task 3: Table rows of subjects, characteristica, interventions, outputs and timecourses

**Files:**
- Create: `python/src/pkdb/migration/rows.py`, `python/tests/migration_fixtures.py`, `python/tests/migration/test_rows.py`

**Interfaces:**
- Consumes: `pkdb.schemas.study` (`CanonicalStudy`, `Group`, `Individual`, `Intervention`, `Measurement`, `Observation`, `Statistics`); `pkdb.studyformat.text.format_number`; `pkdb.studyformat.cells.NOT_REPORTED`, `NAME_PATTERN`; `pkdb.studyformat.tables.TABLES`, `table_file`; `sources.observation_source`, `sources.curator_source`; `metadata.single_line`; `model.NotConverted`, `model.Decision`.
- Produces:
  - `rows.Tables = dict[str, list[dict[str, str]]]`: table file name to rows of cells, column name to text.
  - `rows.ErrorBars = Mapping[str, tuple[float, str]]`: record key to (`error_bar`, `error_type`), filled by Task 4.
  - `rows.study_tables(study: CanonicalStudy, name: str, error_bars: ErrorBars = {}) -> tuple[Tables, list[Decision]]`.
  - `rows.render(tables: Tables) -> dict[str, str]`: file name to TSV text through `render_tsv` with `TABLES[kind].names`.
  - `rows.used_sources(tables: Tables) -> set[str]`.
  - Test helper `migration_fixtures.v1_example(root: Path, *, workbook: bool = True) -> Path`: a format 1 twin of the `valid_files` fixture of `python/tests/conftest.py`, at `root/caffeine/Example`.

The cell rules, the inverse of `studyformat/reader.py`:

| Column | From |
|---|---|
| `measurement`, `calculation`, `substance`, `tissue`, `method`, `choice`, `unit`, `route`, `form`, `application` | the record field, empty for None |
| `time`, `time_unit` | `NR` when `time_not_reported` / `time_unit_not_reported`, else the number or text |
| `count` and every statistic | `format_number`; `cv` and `gcv` in percent (value times 100 by decimal shift, not by float multiplication) |
| intervention `time` | one number, or the list joined with `;` |
| `subjects` (outputs, timecourses, characteristica) | the `group` or `individual` of the record, or the owning subject |
| `subjects` (interventions) | the intervention's `subject` |
| `interventions` | the names joined with `;` |
| `label` | timecourses only |
| `comment` | descriptions, then comments as `user: text`, joined with ` / `, on one line |
| `source` | `observation_source` for outputs and timecourses, `curator_source` for the others |
| `name`, `parent`, `count` (subjects) | groups: their name, parent and count; individuals: name, group as parent, count 1 |

- [ ] **Step 1: Write the format 1 fixture builder**

`python/tests/migration_fixtures.py` builds the v1 twin of `valid_files` without scatters (Task 4 adds them). Read `valid_files` in `python/tests/conftest.py` first; the converted tables must equal its formatted tables byte for byte.

```python
"""Synthetic format 1 studies for the migration tests."""

import json
from pathlib import Path

import openpyxl

STUDY = {
    "sid": "Example",
    "name": "Example",
    "reference": "123",
    "creator": "curator",
    "curators": [["curator", 3]],
    "licence": "open",
    "access": "private",
    "groupset": {
        "groups": [
            {
                "name": "all",
                "count": 2,
                "image": "Tab1",
                "characteristica": [
                    {"measurement_type": "species", "choice": "Homo sapiens", "image": "Tab1"},
                    {"measurement_type": "healthy", "choice": "Y", "image": "Tab1"},
                    {"measurement_type": "sex", "choice": "M", "image": "Tab1"},
                ],
            }
        ]
    },
    "individualset": {
        "individuals": [
            {
                "name": name,
                "group": "all",
                "image": "TabA",
                "characteristica": [
                    {"measurement_type": "age", "value": age, "unit": "yr", "image": "TabA"}
                ],
            }
            for name, age in (("S1", 30), ("S2", 40))
        ]
    },
    "interventionset": {
        "interventions": [
            {
                "name": "D1",
                "measurement_type": "dosing",
                "substance": "drug",
                "route": "oral",
                "form": "tablet",
                "application": "single dose",
                "time": 0,
                "time_unit": "h",
                "value": 100,
                "unit": "mg",
            }
        ]
    },
    "outputset": {
        "outputs": [
            {
                "source": "Tab2",
                "image": "Tab2",
                "output_type": "output",
                "group": "all",
                "interventions": ["D1"],
                "measurement_type": "cmax",
                "substance": "drug",
                "tissue": "plasma",
                "mean": "col==mean",
                "sd": "col==sd",
                "unit": "mg/l",
            },
            {
                "source": "Fig1",
                "image": "Fig1",
                "output_type": "timecourse",
                "label": "drug_plasma",
                "group": "all",
                "interventions": ["D1"],
                "measurement_type": "concentration",
                "substance": "drug",
                "tissue": "plasma",
                "time": "col==time",
                "time_unit": "h",
                "mean": "col==mean",
                "unit": "mg/l",
            },
        ]
    },
}
SHEETS = {
    "Tab2": [["mean", "sd"], [2.5, 0.5]],
    "Fig1": [["time", "mean"], [0, 0], [1, 2], [2, 1]],
}
IMAGES = ("Tab1", "TabA", "Tab2", "Fig1")


def write_sheets(folder: Path, name: str, sheets: dict, *, workbook: bool) -> None:
    """Format 1 tables: a workbook with a notes row above the header, or hidden TSVs."""
    if workbook:
        book = openpyxl.Workbook()
        book.remove(book.active)
        for title, rows in sheets.items():
            sheet = book.create_sheet(title)
            sheet.append(["Curator notes"])
            for row in rows:
                sheet.append(row)
        book.save(folder / f"{name}.xlsx")
        book.close()
    else:
        for title, rows in sheets.items():
            text = "".join("\t".join(str(c) for c in row) + "\n" for row in rows)
            (folder / f".{name}_{title}.tsv").write_text(text, encoding="utf-8")


def v1_study(
    root: Path,
    study: dict,
    sheets: dict,
    images: tuple[str, ...],
    *,
    substance: str = "caffeine",
    workbook: bool = True,
    reference: dict | None = None,
) -> Path:
    name = study["name"]
    folder = root / "studies" / substance / name
    folder.mkdir(parents=True)
    (folder / "study.json").write_text(json.dumps(study), encoding="utf-8")
    (folder / "reference.json").write_text(
        json.dumps(
            reference
            or {"sid": "123", "name": name, "pmid": "123", "title": "Example study"}
        ),
        encoding="utf-8",
    )
    write_sheets(folder, name, sheets, workbook=workbook)
    (folder / f"{name}.pdf").write_bytes(b"%PDF")
    for source in images:
        (folder / f"{name}_{source}.png").write_bytes(b"png")
    return folder


def v1_example(root: Path, *, workbook: bool = True) -> Path:
    return v1_study(root, STUDY, SHEETS, IMAGES, workbook=workbook)
```

Hidden TSVs of format 1 have the header in their first line (no notes row); check `python/src/pkdb/importers/workbook.py:read_table` and adjust `write_sheets` so that both branches give the same rows to `parse_bundle`. The test in Step 2 proves it.

- [ ] **Step 2: Write the failing tests**

`python/tests/migration/test_rows.py`:

```python
import pytest

from migration_fixtures import STUDY, v1_example, v1_study
from pkdb.importers.folder import load_folder, parse_bundle
from pkdb.migration.model import NotConverted
from pkdb.migration.rows import render, study_tables


def parsed(folder):
    return parse_bundle(load_folder(folder))
```

The rows are compared as cells, without the formatter-owned `study` column and in any order, because `format_folder` (Task 5) fills owned columns and sorts rows; Task 5 adds the byte-for-byte test of the whole folder:

```python
def cells(text):
    header, *rows = [line.split("\t") for line in text.splitlines()]
    return sorted(
        {k: v for k, v in zip(header, row, strict=True) if k != "study" and v}
        .items()
        for row in rows
    )


@pytest.mark.parametrize("workbook", [True, False])
def test_rows_equal_the_rows_of_the_format_2_twin(tmp_path, valid_study, workbook):
    folder = v1_example(tmp_path / "v1", workbook=workbook)
    tables, decisions = study_tables(parsed(folder), "Example")
    rendered = render(tables)
    assert set(rendered) == {
        "subjects.tsv",
        "characteristica.tsv",
        "interventions.tsv",
        "outputs_Tab2.tsv",
        "timecourses_Fig1.tsv",
    }
    for name, text in rendered.items():
        assert cells(text) == cells((valid_study / name).read_text()), name
    assert decisions == []
```

Add these tests to the same file:

```python
def test_comments_lose_line_breaks_and_tabs(tmp_path):
    study = {
        **STUDY,
        "interventionset": {
            "interventions": [
                {
                    **STUDY["interventionset"]["interventions"][0],
                    "descriptions": ["Given\twith water.\nFasted."],
                    "comments": [["curator", "Dose from\nTab1"]],
                }
            ]
        },
    }
    folder = v1_study(tmp_path, study, {}, ("Tab1", "TabA"))
    tables, _ = study_tables(parsed(folder), "Example")
    [row] = tables["interventions.tsv"]
    assert row["comment"] == "Given with water. Fasted. / curator: Dose from Tab1"


def test_percent_statistics_are_written_in_percent(tmp_path):
    study = {
        **STUDY,
        "outputset": {
            "outputs": [
                {**STUDY["outputset"]["outputs"][0], "sd": None, "cv": 0.123}
            ]
        },
    }
    folder = v1_study(tmp_path, study, {"Tab2": [["mean"], [2.5]]}, ("Tab1", "TabA", "Tab2"))
    tables, _ = study_tables(parsed(folder), "Example")
    [row] = tables["outputs_Tab2.tsv"]
    assert row["cv"] == "12.3"


def test_schedules_and_dose_lists_are_decisions(tmp_path):
    intervention = {
        **STUDY["interventionset"]["interventions"][0],
        "time": "S0T12R3",
        "application": "multiple dose",
    }
    study = {**STUDY, "interventionset": {"interventions": [intervention]}}
    folder = v1_study(tmp_path, study, {}, ("Tab1", "TabA"))
    tables, decisions = study_tables(parsed(folder), "Example")
    [row] = tables["interventions.tsv"]
    assert (row["time"], row["interval"], row["doses"]) == ("0", "12", "3")
    assert [(d.kind, d.detail) for d in decisions] == [
        ("schedule", "D1: time 0, interval 12, doses 3")
    ]


def test_a_group_with_count_one_becomes_an_individual_and_a_decision(tmp_path):
    groups = [{"name": "all", "count": 1, "image": "Tab1"}]
    study = {**STUDY, "groupset": {"groups": groups}, "individualset": {}}
    folder = v1_study(tmp_path, study, {}, ("Tab1",))
    tables, decisions = study_tables(parsed(folder), "Example")
    assert tables["subjects.tsv"] == [
        {"name": "all", "parent": "", "count": "1", "source": "Tab1", "comment": ""}
    ]
    assert ("group_count_1", "all") in {(d.kind, d.detail) for d in decisions}


@pytest.mark.parametrize(
    ("groups", "individuals", "code"),
    [
        ([{"name": "a;b", "count": 2}], [], "subject_name"),
        ([{"name": "S1", "count": 2}], [{"name": "S1", "group": "S1"}], "subject_name"),
    ],
)
def test_subject_names_that_format_2_cannot_hold_refuse_the_study(
    tmp_path, groups, individuals, code
):
    study = {
        **STUDY,
        "groupset": {"groups": groups},
        "individualset": {"individuals": individuals},
        "outputset": {},
        "interventionset": {},
    }
    folder = v1_study(tmp_path, study, {}, ())
    with pytest.raises(NotConverted) as error:
        study_tables(parsed(folder), "Example")
    assert error.value.code == code
```

Make `python/tests/migration_fixtures.py` importable as `migration_fixtures`: check how `python/tests/curation_http.py` is imported by other tests (rootdir on `sys.path` through `pyproject.toml` `[tool.pytest.ini_options]`) and follow it.

- [ ] **Step 3: Run them to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/migration/test_rows.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkdb.migration.rows'`.

- [ ] **Step 4: Implement `rows.py`**

```python
"""Table rows of a parsed format 1 study: the inverse of the format 2 reader."""

from collections.abc import Mapping
from decimal import Decimal

from pkdb.migration.metadata import single_line
from pkdb.migration.model import Decision, NotConverted
from pkdb.migration.sources import curator_source, observation_source
from pkdb.schemas.study import (
    CanonicalStudy,
    Group,
    Individual,
    Intervention,
    Measurement,
    Notes,
    Observation,
    Statistics,
)
from pkdb.studyformat.cells import NAME_PATTERN, NOT_REPORTED
from pkdb.studyformat.tables import TABLES, table_file
from pkdb.studyformat.text import format_number, render_tsv

Tables = dict[str, list[dict[str, str]]]
ErrorBars = Mapping[str, tuple[float, str]]
STATISTICS = tuple(name for name in Statistics.model_fields if name != "error_type")
PERCENT = frozenset({"cv", "gcv"})
LIST = ";"


def number(value: float | int | None) -> str:
    return "" if value is None else format_number(float(value))


def percent(value: float | None) -> str:
    """A fraction in percent, shifted in decimal so that 0.123 gives 12.3."""
    if value is None:
        return ""
    return format_number(float(Decimal(format_number(value)).scaleb(2)))


def comment(record: Notes) -> str:
    parts = [d.text for d in record.descriptions]
    parts += [f"{c.user}: {c.text}" if c.user else c.text for c in record.comments]
    return single_line(" / ".join(part for part in parts if part.strip()))


def text(value: object) -> str:
    return "" if value is None else single_line(value)


def statistics(record: Observation, error_bars: ErrorBars) -> dict[str, str]:
    stats = record.statistics
    cells = {
        name: percent(getattr(stats, name)) if name in PERCENT else number(getattr(stats, name))
        for name in STATISTICS
    }
    cells["error_type"] = text(stats.error_type)
    if record.key in error_bars:
        bar, kind = error_bars[record.key]
        cells.update({"error_bar": number(bar), "error_type": kind, kind: ""})
    return cells


def observation(record: Observation, error_bars: ErrorBars) -> dict[str, str]:
    return {
        "measurement": text(record.measurement_type),
        "calculation": text(record.calculation_type),
        "substance": text(record.substance),
        "tissue": text(record.tissue),
        "method": text(record.method),
        "choice": text(record.choice),
        "time": NOT_REPORTED if record.time_not_reported else number(record.time),
        "time_unit": NOT_REPORTED if record.time_unit_not_reported else text(record.time_unit),
        "unit": text(record.unit),
        "comment": comment(record),
        **statistics(record, error_bars),
    }


def _name(name: str) -> str:
    if not NAME_PATTERN.fullmatch(name) or name != name.strip():
        raise NotConverted(
            "subject_name", f"Name {name!r} cannot be a format 2 name: no ',', ';' or tabs"
        )
    return name


def _subjects(study: CanonicalStudy, name: str, decisions: list[Decision]) -> list[dict]:
    rows, seen = [], set()
    subjects: list[Group | Individual] = [*study.groups, *study.individuals]
    for subject in subjects:
        if subject.name in seen:
            raise NotConverted(
                "subject_name", f"{subject.name} names a group and an individual"
            )
        seen.add(subject.name)
        if isinstance(subject, Group):
            parent, count = subject.parent, subject.count
            if count == 1:
                decisions.append(Decision(kind="group_count_1", detail=subject.name))
        else:
            parent, count = subject.group, 1
        assert subject.source is not None
        rows.append(
            {
                "name": _name(subject.name),
                "parent": text(parent),
                "count": number(count),
                "source": curator_source(subject.source, subject.image, name),
                "comment": comment(subject),
            }
        )
    return rows


def _characteristica(study: CanonicalStudy, name: str, error_bars: ErrorBars) -> list[dict]:
    rows = []
    for subject in [*study.groups, *study.individuals]:
        for record in subject.characteristica:
            assert record.source is not None
            rows.append(
                {
                    **observation(record, error_bars),
                    "subjects": subject.name,
                    "source": curator_source(record.source, record.image, name),
                }
            )
    return rows


def _interventions(
    study: CanonicalStudy, name: str, error_bars: ErrorBars, decisions: list[Decision]
) -> list[dict]:
    rows = []
    for record in study.interventions:
        times = record.time if isinstance(record.time, list) else [record.time]
        time = LIST.join(number(t) for t in times if t is not None)
        if record.interval is not None or record.doses is not None or len(times) > 1:
            decisions.append(
                Decision(
                    kind="schedule",
                    detail=(
                        f"{record.name}: time {time}, interval {number(record.interval)}, "
                        f"doses {number(record.doses)}"
                    ),
                )
            )
        assert record.source is not None
        rows.append(
            {
                **observation(record, error_bars),
                "name": record.name,
                "subjects": text(record.subject),
                "route": text(record.route),
                "form": text(record.form),
                "application": text(record.application),
                "time": time,
                "time_end": number(record.time_end),
                "interval": number(record.interval),
                "doses": number(record.doses),
                "source": curator_source(record.source, record.image, name),
            }
        )
    return rows


def _measurement(record: Measurement, name: str, error_bars: ErrorBars) -> tuple[str, dict]:
    assert record.source is not None
    source = observation_source(record.source, record.image, name)
    return source, {
        **observation(record, error_bars),
        "subjects": text(record.group or record.individual),
        "interventions": LIST.join(record.interventions),
        "source": source,
    }


def study_tables(
    study: CanonicalStudy, name: str, error_bars: ErrorBars = {}
) -> tuple[Tables, list[Decision]]:
    """The format 2 tables of a parsed format 1 study and the decisions to check."""
    decisions: list[Decision] = []
    tables: Tables = {
        "subjects.tsv": _subjects(study, name, decisions),
        "characteristica.tsv": _characteristica(study, name, error_bars),
        "interventions.tsv": _interventions(study, name, error_bars, decisions),
    }
    for record in study.measurements:
        if record.output_type == "timecourse":
            source, row = _measurement(record, name, error_bars)
            tables.setdefault(table_file("timecourses", source), []).append(
                {**row, "label": text(record.label)}
            )
        elif record.output_type == "output":
            source, row = _measurement(record, name, error_bars)
            tables.setdefault(table_file("outputs", source), []).append(row)
    return {file: rows for file, rows in tables.items() if rows}, decisions


def render(tables: Tables) -> dict[str, str]:
    """TSV text of each table, columns in template order."""
    rendered = {}
    for file, rows in tables.items():
        kind = file.removesuffix(".tsv").partition("_")[0]
        names = TABLES[kind].names
        rendered[file] = render_tsv(
            names, [tuple(row.get(column, "") for column in names) for row in rows]
        )
    return rendered


def used_sources(tables: Tables) -> set[str]:
    return {row["source"] for rows in tables.values() for row in rows if row.get("source")}
```

Notes for the implementer:
- `parse_bundle` resolves `image` to a file name (`Example_Tab1.png`) only for entries that carry `image`; characteristica take their own `image`. If the parser gives characteristica no image of their own, fall back to the subject's image in `_characteristica`.
- Array outputs (`output_type == "array"`) and scatter points are handled in Task 4; skipping them here is intended for now.
- `subjects.tsv` is not sorted here: `format_folder` sorts rows (Task 5).

- [ ] **Step 5: Run the tests to verify they pass, then lint and types**

Run: `cd python && uv run --locked pytest -q tests/migration && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked ty check`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add python/src/pkdb/migration/rows.py python/tests/migration_fixtures.py python/tests/migration/test_rows.py
git commit -m "Write the format 2 table rows of parsed format 1 studies"
```

---

### Task 4: Scatters, array outputs, geometric means and error bar formulas

**Files:**
- Create: `python/src/pkdb/migration/formulas.py`, `python/tests/migration/test_formulas.py`
- Modify: `python/src/pkdb/migration/rows.py`, `python/tests/migration_fixtures.py`, `python/tests/migration/test_rows.py`

**Interfaces:**
- Consumes: Task 3 (`study_tables`, `observation`, `_measurement`, `ErrorBars`); `pkdb.domain.datasets` for how format 1 pairs scatter points (read `compile_datasets`, lines 38-146).
- Produces:
  - `formulas.error_bars(workbook: Path, study: CanonicalStudy) -> dict[str, tuple[float, str]]`: record key to (`X`, `"sd"` or `"se"`) for every record whose `sd` or `se` cell holds `=ABS(X - mean)` with `mean` the mean cell of the same row, in either order of the operands.
  - `rows.study_tables` additionally writes `scatters_<source>.tsv`, writes `array` outputs (to `timecourses_<source>.tsv` with their label, else to `outputs_<source>.tsv`, with a decision `array_output`), and moves the mean of a record with calculation `geometric mean` and no `gmean` to `gmean` (decision `geometric_spread` when it also has `sd`, `se` or `cv`).

- [ ] **Step 1: Write the failing formula tests**

`python/tests/migration/test_formulas.py`:

```python
import json

import openpyxl

from pkdb.importers.folder import load_folder, parse_bundle
from pkdb.migration.formulas import error_bars


def study_with(tmp_path, sd_formula, *, column="sd"):
    folder = tmp_path / "Example"
    folder.mkdir()
    (folder / "study.json").write_text(
        json.dumps(
            {
                "sid": "Example",
                "name": "Example",
                "reference": "123",
                "creator": "curator",
                "groupset": {"groups": [{"name": "all", "count": 4}]},
                "outputset": {
                    "outputs": [
                        {
                            "source": "Tab2",
                            "output_type": "output",
                            "group": "all",
                            "measurement_type": "cmax",
                            "substance": "drug",
                            "tissue": "plasma",
                            "mean": "col==mean",
                            column: f"col=={column}",
                            "unit": "mg/l",
                        }
                    ]
                },
            }
        )
    )
    (folder / "reference.json").write_text(json.dumps({"sid": "123", "name": "Example"}))
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Tab2"
    sheet.append(["notes"])
    sheet.append(["mean", column, "upper"])
    sheet.append([2.5, sd_formula, 3.25])
    book.save(folder / "Example.xlsx")
    # Cached values as Excel would store them: openpyxl writes none, so the
    # tests set the cached value through the importer's data-only reading path.
    return folder
```

openpyxl does not compute formulas, so a workbook saved by openpyxl has no cached values and the v1 importer reads `None` for formula cells. Build the fixture workbook in two steps so that both views exist: save the formula workbook, then write the cached values the way `python/tests` already does for formula cells (search `python/tests/studyformat` for `cached` or `data_only` and reuse that helper; the sync engine tests of sub-project 3 cover formula cells with and without cached values). The tests are:

```python
def test_abs_of_a_difference_with_the_mean_is_an_error_bar(tmp_path):
    folder = study_with(tmp_path, "=ABS(C3-A3)")
    study = parse_bundle(load_folder(folder))
    [record] = study.measurements
    assert error_bars(folder / "Example.xlsx", study) == {record.key: (3.25, "sd")}


def test_operands_in_either_order_and_spaces_are_accepted(tmp_path):
    folder = study_with(tmp_path, "= ABS( A3 - C3 )", column="se")
    study = parse_bundle(load_folder(folder))
    [record] = study.measurements
    assert error_bars(folder / "Example.xlsx", study) == {record.key: (3.25, "se")}


def test_other_formulas_are_no_error_bars(tmp_path):
    for formula in ("=C3-A3", "=ABS(C3-B4)", "=ABS(C3-A3)/2", "=0.75"):
        folder = study_with(tmp_path / formula.replace("/", "_"), formula)
        study = parse_bundle(load_folder(folder))
        assert error_bars(folder / "Example.xlsx", study) == {}
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/migration/test_formulas.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkdb.migration.formulas'`.

- [ ] **Step 3: Implement `formulas.py`**

```python
"""Error bars that format 1 workbooks compute as ABS(X - mean)."""

import re
from pathlib import Path

import openpyxl

from pkdb.schemas.study import CanonicalStudy, Observation

CELL = r"\$?([A-Z]{1,3})\$?([0-9]+)"
ABS = re.compile(rf"=\s*ABS\(\s*{CELL}\s*-\s*{CELL}\s*\)\s*", re.IGNORECASE)


def _records(study: CanonicalStudy) -> list[Observation]:
    records: list[Observation] = [*study.interventions, *study.measurements]
    for subject in [*study.groups, *study.individuals]:
        records.extend(subject.characteristica)
    return records


def error_bars(workbook: Path, study: CanonicalStudy) -> dict[str, tuple[float, str]]:
    """Record key to (error bar, `sd` or `se`) for spreads computed as ABS(X - mean)."""
    formulas = openpyxl.load_workbook(workbook, data_only=False, read_only=True)
    values = openpyxl.load_workbook(workbook, data_only=True, read_only=True)
    found = {}
    try:
        for record in _records(study):
            source = record.source
            if source is None or source.sheet is None or source.sheet not in formulas.sheetnames:
                continue
            mean = source.for_field("mean").cell
            for kind in ("sd", "se"):
                cell = source.for_field(kind).cell
                if mean is None or cell is None or source.for_field(kind) is source:
                    continue
                formula = formulas[source.sheet][cell].value
                match = ABS.fullmatch(formula) if isinstance(formula, str) else None
                if match is None:
                    continue
                first, second = match.group(1) + match.group(2), match.group(3) + match.group(4)
                other = second if first == mean else first if second == mean else None
                if other is None:
                    continue
                bar = values[source.sheet][other].value
                if isinstance(bar, (int, float)) and not isinstance(bar, bool):
                    found[record.key] = (float(bar), kind)
    finally:
        formulas.close()
        values.close()
    return found
```

`SourceLocation.for_field` returns the row location itself when the field has no cell, hence the `is source` check. Read-only workbooks give cells by coordinate through `sheet[cell]`; if that is slow on the corpus, load each sheet's rows once into a dict. The record key of characteristica, interventions and measurements comes from `parse_bundle`; it is the `ErrorBars` key that `rows.statistics` looks up.

- [ ] **Step 4: Run the formula tests to verify they pass**

Run: `cd python && uv run --locked pytest -q tests/migration/test_formulas.py`
Expected: 3 passed.

- [ ] **Step 5: Write the failing row tests for scatters, arrays and geometric means**

Extend `migration_fixtures.py` with the scatter of the format 2 twin (`scatters_Fig2.tsv` of `valid_files`: dataset `age_vs_cmax`, x age of S1 and S2, y cmax after D1):

```python
SCATTER_OUTPUTS = [
    {
        "source": "Fig2",
        "image": "Fig2",
        "output_type": "output",
        "label": "age_vs_cmax_x",
        "individual": "col==subject",
        "measurement_type": "age",
        "mean": "col==age",
        "unit": "yr",
    },
    {
        "source": "Fig2",
        "image": "Fig2",
        "output_type": "output",
        "label": "age_vs_cmax_y",
        "individual": "col==subject",
        "interventions": ["D1"],
        "measurement_type": "cmax",
        "substance": "drug",
        "tissue": "plasma",
        "mean": "col==cmax",
        "unit": "mg/l",
    },
]
DATASET = {
    "data": [
        {
            "name": "age_vs_cmax",
            "data_type": "scatter",
            "image": "Fig2",
            "subsets": [
                {
                    "name": "age_vs_cmax",
                    "dimensions": ["age_vs_cmax_x", "age_vs_cmax_y"],
                    "shared": ["individual"],
                }
            ],
        }
    ]
}
SCATTER_SHEET = {"Fig2": [["subject", "age", "cmax"], ["S1", 30, 2], ["S2", 40, 3]]}


def v1_full_example(root: Path, *, workbook: bool = True) -> Path:
    """The format 1 twin of the whole `valid_files` study, scatters included."""
    study = {
        **STUDY,
        "outputset": {"outputs": [*STUDY["outputset"]["outputs"], *SCATTER_OUTPUTS]},
        "dataset": DATASET,
    }
    return v1_study(
        root, study, {**SHEETS, **SCATTER_SHEET}, (*IMAGES, "Fig2"), workbook=workbook
    )
```

Check the format 1 dataset syntax against `importers/folder.py:600-650` and `domain/datasets.compile_datasets` and adapt the fixture until `prepare()` of the fixture has no errors; assert that in the test. Then add to `test_rows.py`:

```python
from migration_fixtures import v1_full_example
from pkdb.preparation import prepare


@pytest.mark.parametrize("workbook", [True, False])
def test_the_full_twin_with_scatters(tmp_path, valid_study, sf_vocabulary, workbook):
    folder = v1_full_example(tmp_path / "v1", workbook=workbook)
    assert not [i for i in prepare(folder, vocabulary=sf_vocabulary).report.issues if i.severity == "error"]
    tables, decisions = study_tables(parsed(folder), "Example")
    rendered = render(tables)
    assert "scatters_Fig2.tsv" in rendered
    for name, text in rendered.items():
        assert cells(text) == cells((valid_study / name).read_text()), name
    assert decisions == []


def test_array_outputs_become_outputs_or_timecourses(tmp_path):
    array = {**STUDY["outputset"]["outputs"][0], "output_type": "array"}
    labelled = {**STUDY["outputset"]["outputs"][1], "output_type": "array"}
    study = {**STUDY, "outputset": {"outputs": [array, labelled]}}
    folder = v1_study(tmp_path, study, SHEETS, IMAGES)
    tables, decisions = study_tables(parsed(folder), "Example")
    assert len(tables["outputs_Tab2.tsv"]) == 1
    assert [row["label"] for row in tables["timecourses_Fig1.tsv"]] == ["drug_plasma"] * 3
    assert {d.kind for d in decisions} == {"array_output"}


def test_a_geometric_mean_moves_to_gmean(tmp_path):
    output = {**STUDY["outputset"]["outputs"][0], "calculation_type": "geometric mean"}
    study = {**STUDY, "outputset": {"outputs": [output]}}
    folder = v1_study(tmp_path, study, SHEETS, IMAGES)
    tables, decisions = study_tables(parsed(folder), "Example")
    [row] = tables["outputs_Tab2.tsv"]
    assert (row["mean"], row["gmean"], row["calculation"]) == ("", "2.5", "geometric mean")
    # It also has sd: arithmetic or geometric is unclear.
    assert [d.kind for d in decisions] == ["geometric_spread"]
```

- [ ] **Step 6: Run them to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/migration/test_rows.py`
Expected: the three new tests FAIL (`scatters_Fig2.tsv` missing, `KeyError` for array tables, `mean` not moved).

- [ ] **Step 7: Implement scatters, arrays and geometric means in `rows.py`**

Add to `rows.py`:

```python
GEOMETRIC_MEAN = "geometric mean"


def _geometric(record: Observation, row: dict[str, str], decisions: list[Decision]) -> dict:
    stats = record.statistics
    if record.calculation_type == GEOMETRIC_MEAN and stats.gmean is None and stats.mean is not None:
        row = {**row, "gmean": row["mean"], "mean": ""}
        if any(getattr(stats, name) is not None for name in ("sd", "se", "cv")):
            decisions.append(
                Decision(
                    kind="geometric_spread",
                    detail=f"{record.key}: geometric mean with sd, se or cv",
                )
            )
    return row


def _scatter_rows(
    study: CanonicalStudy, name: str, decisions: list[Decision]
) -> tuple[Tables, set[str]]:
    """Rows of scatters_<source>.tsv, one per pair of x and y outputs of a subject."""
    by_label: dict[str, list[Measurement]] = {}
    for record in study.measurements:
        if record.label:
            by_label.setdefault(record.label, []).append(record)
    tables: Tables = {}
    used: set[str] = set()
    for dataset in study.scatters:
        assert dataset.source is not None
        source = observation_source(dataset.source, dataset.image, name)
        for subset in dataset.subsets:
            labels = [dimension.output for dimension in subset.dimensions]
            if len(labels) != 2:
                raise NotConverted(
                    "scatter_dimensions",
                    f"Scatter {dataset.name} has {len(labels)} dimensions; format 2 has x and y",
                )
            xs = {(r.group or r.individual): r for r in by_label.get(labels[0], [])}
            ys = {(r.group or r.individual): r for r in by_label.get(labels[1], [])}
            if set(xs) != set(ys):
                raise NotConverted(
                    "scatter_pairs",
                    f"Scatter {dataset.name}: the x and y outputs do not pair by subject",
                )
            for subject in xs:
                row = {"name": subset.name or dataset.name, "subjects": text(subject), "source": source}
                for prefix, record in (("x", xs[subject]), ("y", ys[subject])):
                    stats = record.statistics
                    spread = [n for n in STATISTICS if n not in ("mean", "count") and getattr(stats, n) is not None]
                    if spread:
                        raise NotConverted(
                            "scatter_statistics",
                            f"Scatter {dataset.name} reports {', '.join(spread)}; format 2 scatters hold the mean only",
                        )
                    row |= {
                        f"{prefix}_interventions": LIST.join(record.interventions),
                        f"{prefix}_measurement": text(record.measurement_type),
                        f"{prefix}_substance": text(record.substance),
                        f"{prefix}_tissue": text(record.tissue),
                        f"{prefix}_method": text(record.method),
                        f"{prefix}_time": NOT_REPORTED if record.time_not_reported else number(record.time),
                        f"{prefix}_time_unit": NOT_REPORTED if record.time_unit_not_reported else text(record.time_unit),
                        f"{prefix}_mean": number(stats.mean),
                        f"{prefix}_unit": text(record.unit),
                    }
                    used.add(record.key)
                tables.setdefault(table_file("scatters", source), []).append(row)
            if labels != [f"{dataset.name}_x", f"{dataset.name}_y"]:
                decisions.append(
                    Decision(
                        kind="scatter_label",
                        detail=f"{dataset.name}: {labels[0]}, {labels[1]} become {dataset.name}_x, {dataset.name}_y",
                    )
                )
    return tables, used
```

Change `study_tables` so that it writes the scatter rows first, skips the measurements used by scatters, writes `array` outputs and applies `_geometric` to every observation row (outputs, timecourses, characteristica, interventions):

```python
def study_tables(
    study: CanonicalStudy, name: str, error_bars: ErrorBars = {}
) -> tuple[Tables, list[Decision]]:
    decisions: list[Decision] = []
    scatters, used = _scatter_rows(study, name, decisions)
    tables: Tables = {
        "subjects.tsv": _subjects(study, name, decisions),
        "characteristica.tsv": _characteristica(study, name, error_bars, decisions),
        "interventions.tsv": _interventions(study, name, error_bars, decisions),
    }
    for record in study.measurements:
        if record.key in used:
            continue
        source, row = _measurement(record, name, error_bars)
        row = _geometric(record, row, decisions)
        if record.output_type == "array":
            decisions.append(
                Decision(kind="array_output", detail=f"{record.key} in {source}")
            )
        if record.label and record.output_type in ("timecourse", "array"):
            tables.setdefault(table_file("timecourses", source), []).append(
                {**row, "label": text(record.label)}
            )
        else:
            tables.setdefault(table_file("outputs", source), []).append(row)
    tables |= scatters
    return {file: rows for file, rows in tables.items() if rows}, decisions
```

Pass `decisions` into `_characteristica` and `_interventions` and wrap each of their rows with `_geometric(record, row, decisions)`. One `array_output` decision per record is too many for a whole table: collapse them per file before returning (`detail=f"{count} array outputs in {file}"`). Adjust `test_array_outputs_become_outputs_or_timecourses` to the collapsed form and keep `{d.kind for d in decisions} == {"array_output"}`.

The two format 1 subjects with the same name in a scatter (one group and one individual) cannot occur here: Task 3 refuses them.

- [ ] **Step 8: Run all migration tests, lint and types**

Run: `cd python && uv run --locked pytest -q tests/migration && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked ty check`
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add python/src/pkdb/migration python/tests/migration_fixtures.py python/tests/migration
git commit -m "Convert scatters, array outputs, geometric means and ABS error bar formulas"
```

---

### Task 5: Convert one study into a work folder

**Files:**
- Create: `python/src/pkdb/migration/convert.py`, `python/tests/migration/test_convert.py`

**Interfaces:**
- Consumes: Tasks 1 to 4; `pkdb.importers.folder.load_folder`, `parse_bundle`; `pkdb.references.ReferenceResolver`, `sync_reference`; `pkdb.studyformat.formatter.format_folder`; `pkdb.studyformat.models.canonical_study_json`, `canonical_review_json`; `pkdb.studyformat.tables.STUDY_JSON`, `REFERENCE_JSON`, `REVIEW_JSON`.
- Produces:
  - `convert.Conversion(folder: Path, decisions: list[Decision])` (frozen dataclass).
  - `convert.convert_study(v1: Path, target: Path, *, registry: Registry, approver: str | None, resolver: ReferenceResolver) -> Conversion`: writes the format 2 study into `target` (an empty or missing folder named like `v1`), raises `NotConverted`.
  - `convert.V1_FILES`: the predicate `is_v1_file(name: str, study: str) -> bool` for files that a converted study drops (v1 `study.json` is rewritten; `<study>.xlsx`, `.xls`, hidden `.<study>_*.tsv`, other `.tsv`, `.csv`, `.json` files other than `reference.json`).

Behavior:
1. `bundle = load_folder(v1)`, `study = parse_bundle(bundle)`. A `StudyValidationError` here raises `NotConverted("unreadable", <first issue messages>)`; Task 7 classifies these studies as `invalid_v1` from the gate's own preparation, so the converter only needs a reason.
2. `error_bars(...)` when `<name>.xlsx` exists.
3. `tables, decisions = study_tables(study, name, bars)`; `rendered = render(tables)`.
4. Write every rendered table, `study.json` (`canonical_study_json` of `study_metadata(...)`), `review.json` (`canonical_review_json` of `review(...)`), `subjects.tsv` even when empty is not allowed: a study without subjects raises `NotConverted("no_subjects", ...)`.
5. Copy `reference.json` when it exists; then `sync_reference(target, resolver)`, which keeps a snapshot that describes the publication and resolves a missing or mismatched one. A `ReferenceError` raises `NotConverted("reference", ...)`.
6. `copy_images(v1, target, name, used_sources(tables))` and copy every other attachment (PDF, documents, PNG images that no source uses) unchanged. Files for which `is_v1_file` holds are not copied; each dropped file other than the workbook, the hidden TSVs and `study.json` is a decision `removed_file`. Sheets of the workbook and hidden TSVs that no row came from are decisions `unreferenced_sheet`.
7. `result = format_folder(target)`; if `not result.ok`, raise `NotConverted("format", <issue messages>)`.
8. A pydantic `ValidationError` from `study_metadata` raises `NotConverted("metadata", ...)`.

- [ ] **Step 1: Write the failing tests**

`python/tests/migration/test_convert.py`:

```python
import json
from datetime import date

import pytest

from migration_fixtures import v1_full_example, write_sheets
from pkdb.migration.convert import convert_study
from pkdb.migration.model import NotConverted
from pkdb.migration.registry import Registry
from pkdb.references import ReferenceResolver


class NoNetwork(ReferenceResolver):
    def resolve(self, *args, **kwargs):
        raise AssertionError("the converter must keep an existing reference.json")


def files(folder):
    return {path.name: path.read_bytes() for path in sorted(folder.iterdir())}


@pytest.mark.parametrize("workbook", [True, False])
def test_the_converted_folder_equals_the_format_2_twin(tmp_path, valid_study, workbook):
    v1 = v1_full_example(tmp_path / "v1", workbook=workbook)
    target = tmp_path / "v2" / "caffeine" / "Example"
    conversion = convert_study(
        v1, target, registry=Registry(), approver=None, resolver=NoNetwork(offline=True)
    )
    assert files(target) == files(valid_study)
    assert conversion.decisions == []


def test_a_registered_study_is_released_and_approved(tmp_path):
    v1 = v1_full_example(tmp_path / "v1")
    registry = Registry({"PKDB00042": ("caffeine/Example", date(2020, 1, 2))})
    target = tmp_path / "v2" / "caffeine" / "Example"
    convert_study(v1, target, registry=registry, approver="mkoenig", resolver=NoNetwork(offline=True))
    metadata = json.loads((target / "study.json").read_text())
    assert metadata["release"] == {"pkdb_id": "PKDB00042", "date": "2020-01-02"}
    review = json.loads((target / "review.json").read_text())
    assert (review["status"], review["approved_by"]) == ("approved", "mkoenig")


def test_a_stale_hidden_tsv_beside_the_workbook_is_ignored_and_removed(tmp_path):
    v1 = v1_full_example(tmp_path / "v1", workbook=True)
    write_sheets(v1, "Example", {"Tab2": [["mean", "sd"], [99, 9]]}, workbook=False)
    target = tmp_path / "v2" / "caffeine" / "Example"
    convert_study(v1, target, registry=Registry(), approver=None, resolver=NoNetwork(offline=True))
    assert not list(target.glob(".*.tsv"))
    assert "2.5" in (target / "outputs_Tab2.tsv").read_text()


def test_other_tables_and_json_files_are_removed_and_listed(tmp_path):
    v1 = v1_full_example(tmp_path / "v1")
    (v1 / "notes.csv").write_text("a,b\n")
    (v1 / "Example_supplement.docx").write_bytes(b"doc")
    target = tmp_path / "v2" / "caffeine" / "Example"
    conversion = convert_study(
        v1, target, registry=Registry(), approver=None, resolver=NoNetwork(offline=True)
    )
    assert (target / "Example_supplement.docx").exists()
    assert not (target / "notes.csv").exists()
    assert [(d.kind, d.detail) for d in conversion.decisions] == [("removed_file", "notes.csv")]


def test_unreferenced_sheets_are_listed(tmp_path):
    v1 = v1_full_example(tmp_path / "v1")
    import openpyxl

    book = openpyxl.load_workbook(v1 / "Example.xlsx")
    book.create_sheet("Fig9").append(["time", "mean"])
    book.save(v1 / "Example.xlsx")
    target = tmp_path / "v2" / "caffeine" / "Example"
    conversion = convert_study(
        v1, target, registry=Registry(), approver=None, resolver=NoNetwork(offline=True)
    )
    assert ("unreferenced_sheet", "Fig9") in {(d.kind, d.detail) for d in conversion.decisions}


def test_a_study_without_subjects_is_not_converted(tmp_path):
    v1 = v1_full_example(tmp_path / "v1")
    study = json.loads((v1 / "study.json").read_text())
    study["groupset"] = {}
    study["individualset"] = {}
    study["outputset"] = {}
    study["dataset"] = {}
    study["interventionset"] = {}
    (v1 / "study.json").write_text(json.dumps(study))
    with pytest.raises(NotConverted) as error:
        convert_study(
            v1,
            tmp_path / "v2" / "caffeine" / "Example",
            registry=Registry(),
            approver=None,
            resolver=NoNetwork(offline=True),
        )
    assert error.value.code == "no_subjects"
```

`files(target) == files(valid_study)` requires that the twin's `reference.json` and the formatted `reference.json` agree byte for byte; if `format_folder` rewrites the v1 `reference.json` into canonical JSON, compare after both are formatted (they are: `valid_study` is formatted too).

- [ ] **Step 2: Run them to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/migration/test_convert.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkdb.migration.convert'`.

- [ ] **Step 3: Implement `convert.py`**

```python
"""Convert one format 1 study folder into a format 2 work folder."""

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import openpyxl
from pydantic import ValidationError

from pkdb.importers.folder import load_folder, parse_bundle
from pkdb.migration.formulas import error_bars
from pkdb.migration.metadata import review, study_metadata
from pkdb.migration.model import Decision, NotConverted
from pkdb.migration.registry import Registry
from pkdb.migration.rows import render, study_tables, used_sources
from pkdb.migration.sources import IMAGE_SUFFIXES, copy_images, sheet_of
from pkdb.references import ReferenceError, ReferenceResolver, sync_reference
from pkdb.schemas.validation import StudyValidationError
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.models import canonical_review_json, canonical_study_json
from pkdb.studyformat.tables import REFERENCE_JSON, REVIEW_JSON, STUDY_JSON

DATA_SUFFIXES = (".tsv", ".csv", ".json", ".xls", ".xlsx")


@dataclass(frozen=True)
class Conversion:
    folder: Path
    decisions: list[Decision]


def is_v1_file(name: str, study: str) -> bool:
    """Files that a format 2 study does not keep: v1 tables, workbooks and other data files."""
    return name != REFERENCE_JSON and Path(name).suffix.lower() in DATA_SUFFIXES


def _quiet(name: str, study: str) -> bool:
    """Dropped files that need no decision: the v1 study.json, workbook and hidden TSVs."""
    return name in (STUDY_JSON, f"{study}.xlsx") or (
        name.startswith(f".{study}_") and name.endswith(".tsv")
    )


def _sheets(v1: Path, study: str) -> set[str]:
    sheets = {path.name.removeprefix(f".{study}_").removesuffix(".tsv") for path in v1.glob(f".{study}_*.tsv")}
    workbook = v1 / f"{study}.xlsx"
    if workbook.exists():
        book = openpyxl.load_workbook(workbook, read_only=True)
        sheets |= set(book.sheetnames)
        book.close()
    return sheets


def _messages(error: StudyValidationError) -> str:
    return "; ".join(issue.message for issue in error.report.issues[:3])


def convert_study(
    v1: Path,
    target: Path,
    *,
    registry: Registry,
    approver: str | None,
    resolver: ReferenceResolver,
) -> Conversion:
    name = v1.name
    location = f"{v1.parent.name}/{name}"
    try:
        bundle = load_folder(v1)
        study = parse_bundle(bundle)
    except StudyValidationError as error:
        raise NotConverted("unreadable", _messages(error)) from error
    workbook = v1 / f"{name}.xlsx"
    bars = error_bars(workbook, study) if workbook.exists() else {}
    tables, decisions = study_tables(study, name, bars)
    if not tables.get("subjects.tsv"):
        raise NotConverted("no_subjects", "The study has no groups or individuals")
    release = registry.release(location)
    try:
        metadata, metadata_decisions = study_metadata(
            bundle.study, bundle.reference, release, creator_fallback=approver or "pkdb"
        )
        decisions += metadata_decisions
        status = review(release, approver)
    except ValidationError as error:
        raise NotConverted("metadata", str(error).splitlines()[0]) from error
    target.mkdir(parents=True, exist_ok=False)
    for file, text in render(tables).items():
        (target / file).write_text(text, encoding="utf-8", newline="")
    (target / STUDY_JSON).write_text(canonical_study_json(metadata), encoding="utf-8")
    (target / REVIEW_JSON).write_text(canonical_review_json(status), encoding="utf-8")
    if (v1 / REFERENCE_JSON).exists():
        shutil.copyfile(v1 / REFERENCE_JSON, target / REFERENCE_JSON)
    try:
        sync_reference(target, resolver)
    except ReferenceError as error:
        raise NotConverted("reference", str(error)) from error
    sources = used_sources(tables)
    decisions += copy_images(v1, target, name, sources)
    images = {f"{name}_{source}" for source in sources}
    for path in sorted(v1.iterdir()):
        if path.name in (STUDY_JSON, REFERENCE_JSON) or not path.is_file():
            continue
        if Path(path.name).stem in images and path.suffix.lower() in IMAGE_SUFFIXES:
            continue  # written by copy_images
        if is_v1_file(path.name, name):
            if not _quiet(path.name, name):
                decisions.append(Decision(kind="removed_file", detail=path.name))
            continue
        shutil.copyfile(path, target / path.name)
    read = {sheet_of(r.source, name) for r in _all_records(study) if r.source is not None}
    for sheet in sorted(_sheets(v1, name) - read):
        decisions.append(Decision(kind="unreferenced_sheet", detail=sheet))
    result = format_folder(target)
    if not result.ok:
        raise NotConverted("format", "; ".join(i.message for i in result.issues[:3]))
    return Conversion(target, decisions)
```

Add `_all_records(study)` returning every subject, characteristic, intervention, measurement and dataset of the parsed study (subjects and datasets carry `source` too). Check the attribute names of `FormatResult` (`ok`, `issues`) in `python/src/pkdb/studyformat/formatter.py` and adapt. If `target` must not exist yet, create the parent with `target.parent.mkdir(parents=True, exist_ok=True)`.

- [ ] **Step 4: Run the tests, lint and types**

Run: `cd python && uv run --locked pytest -q tests/migration && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked ty check`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/migration/convert.py python/tests/migration/test_convert.py
git commit -m "Convert a format 1 study into a formatted format 2 folder"
```

---

### Task 6: Equivalence gate

**Files:**
- Create: `python/src/pkdb/migration/gate.py`, `python/tests/migration/test_gate.py`

**Interfaces:**
- Consumes: `pkdb.preparation.prepare`, `PreparedBundle`; `pkdb.schemas.study`; `pkdb.studyformat.formatter.format_folder` (`check=True`); `model.Change`, `model.Difference`, `model.StudyResult`.
- Produces:
  - `gate.TOLERANCE = 1e-9`, `gate.MAX_DIFFERENCES = 50`.
  - `gate.compare(a: CanonicalStudy, b: CanonicalStudy) -> tuple[list[Change], list[Difference]]`.
  - `gate.judge(v1: Path, converted: Path, vocabulary: Vocabulary) -> StudyResult`: prepares both, returns `invalid_v1` (A raises or has errors, with the issue codes), `mismatch` (B fails the format check, raises or has errors, or differs), `intended` (only changes) or `identical`. `study` is `<substance>/<name>` of `v1`.

Normalization (both studies are prepared, so counts are inherited and calculation types filled the same way on both sides):
- **Subjects:** name to `(kind, count, parent)`; kind `group` or `individual`. A format 1 group with count 1 is compared as an individual whose `group` is its parent, and every record of A with `group == name` as `individual == name`: change `group_count_1`.
- **Records:** every characteristic (with its subject), intervention and measurement with `origin == "reported"`. Key: `(table, subject, sorted interventions, measurement_type, calculation_type, choice, substance, tissue, method, time, time_unit, time_not_reported, time_unit_not_reported, unit, label, output_type, image)` for measurements and characteristica, plus `(name, route, form, application, time, time_end, interval, doses, subject)` for interventions. Values: the statistics. Records with the same key are matched after sorting by their statistics; numbers compare with `math.isclose(..., rel_tol=TOLERANCE, abs_tol=0)`.
- **Intended transformations** applied to A before comparing, each counted as a `Change` with up to three examples:
  - `array_output`: A `output_type == "array"` becomes `timecourse` when it has a label, else `output`.
  - `gmean`: A calculation `geometric mean`, `mean` set, `gmean` None, and B with `gmean` equal and `mean` None.
  - `error_bar`: B has `error_bar` X and `error_type` `sd` or `se` with that spread None, and A's spread equals `abs(X - mean)`.
  - `scatter_label`: labels of A's scatter outputs renamed to `<dataset>_x` and `<dataset>_y`.
  - `image_converted`: A image `.jpg` or `.jpeg` becomes `.png`.
- **Timecourses:** the set of `(label, image, frozenset of point keys)`.
- **Scatters:** per dataset name, the set of `(subject, x key, y key)` pairs, taken from `subsets[].points` (normalized keys) and mapped back to their reported records through `derived_from`; read `domain/datasets.py` to confirm how points name records.
- Metadata (sid, release, review, reference, attachments, section notes) is not compared.
- Differences have `path` like `measurements[outputs Tab2 all cmax drug plasma].sd`, `a` and `b` as text (`format_number` for numbers, `missing` for an absent record); at most `MAX_DIFFERENCES` are listed.

- [ ] **Step 1: Write the failing tests**

`python/tests/migration/test_gate.py`:

```python
import json
import shutil

from migration_fixtures import STUDY, v1_full_example, v1_study, SHEETS, IMAGES
from pkdb.migration.convert import convert_study
from pkdb.migration.gate import judge
from pkdb.migration.registry import Registry
from pkdb.references import ReferenceResolver


def converted(tmp_path, v1):
    target = tmp_path / "v2" / v1.parent.name / v1.name
    convert_study(v1, target, registry=Registry(), approver=None, resolver=ReferenceResolver(offline=True))
    return target


def test_an_exact_conversion_is_identical(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert (result.study, result.outcome, result.differences) == ("caffeine/Example", "identical", [])


def test_a_group_with_count_one_is_an_intended_change(tmp_path, sf_vocabulary):
    study = {**STUDY, "groupset": {"groups": [{**STUDY["groupset"]["groups"][0], "count": 1}]}, "individualset": {}}
    v1 = v1_study(tmp_path / "v1", study, SHEETS, IMAGES)
    result = judge(v1, converted(tmp_path, v1), sf_vocabulary)
    assert result.outcome == "intended"
    assert [c.kind for c in result.changes] == ["group_count_1"]


def test_a_changed_value_is_a_mismatch(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)
    table = v2 / "outputs_Tab2.tsv"
    table.write_text(table.read_text().replace("\t0.5\t", "\t0.6\t"))
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "mismatch"
    [difference] = result.differences
    assert difference.path.endswith(".sd") and (difference.a, difference.b) == ("0.5", "0.6")


def test_a_difference_within_the_tolerance_is_identical(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)
    table = v2 / "outputs_Tab2.tsv"
    table.write_text(table.read_text().replace("\t0.5\t", "\t0.5000000000001\t"))
    assert judge(v1, v2, sf_vocabulary).outcome == "identical"


def test_an_unformatted_converted_study_is_a_mismatch(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)
    (v2 / "subjects.tsv").write_text((v2 / "subjects.tsv").read_text() + "\n")
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "mismatch"
    assert result.differences[0].path == "format"


def test_a_v1_study_that_cannot_be_prepared_is_invalid_v1(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)
    study = json.loads((v1 / "study.json").read_text())
    study["outputset"]["outputs"][0]["group"] = "nobody"
    (v1 / "study.json").write_text(json.dumps(study))
    result = judge(v1, v2, sf_vocabulary)
    assert result.outcome == "invalid_v1"
    assert result.issues


def test_an_error_bar_formula_is_an_intended_change(tmp_path, sf_vocabulary):
    v1 = v1_full_example(tmp_path / "v1")
    v2 = converted(tmp_path, v1)
    table = v2 / "outputs_Tab2.tsv"
    header, row = table.read_text().splitlines()
    names, cells = header.split("\t"), row.split("\t")
    cells[names.index("sd")] = ""
    cells[names.index("error_bar")] = "3"
    cells[names.index("error_type")] = "sd"
    table.write_text("\t".join(names) + "\n" + "\t".join(cells) + "\n")
    result = judge(v1, v2, sf_vocabulary)
    assert (result.outcome, [c.kind for c in result.changes]) == ("intended", ["error_bar"])
```

Add one test per remaining intended change (`gmean`, `array_output`, `scatter_label`, `image_converted`) built the same way from the fixtures of Tasks 2 to 4, each asserting `outcome == "intended"` and the change kind; and one test that 60 differing rows list exactly `MAX_DIFFERENCES` differences.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/migration/test_gate.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkdb.migration.gate'`.

- [ ] **Step 3: Implement `gate.py`**

Structure the module as small functions, each tested through `judge`:

```python
"""Equivalence gate: the converted study must mean what the format 1 study meant."""

import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from pkdb.domain.vocabulary import Vocabulary
from pkdb.migration.model import Change, Difference, StudyResult
from pkdb.preparation import prepare
from pkdb.schemas.study import CanonicalStudy, Group, Observation, Statistics
from pkdb.schemas.validation import StudyValidationError
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.text import format_number

TOLERANCE = 1e-9
MAX_DIFFERENCES = 50
STATISTICS = tuple(Statistics.model_fields)


@dataclass
class Changes:
    """Intended changes found while normalizing A, by kind."""

    found: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def add(self, kind: str, example: str) -> None:
        self.found[kind].append(example)

    def listed(self) -> list[Change]:
        return [
            Change(kind=kind, count=len(examples), examples=examples[:3])
            for kind, examples in sorted(self.found.items())
        ]


def same(a: object, b: object) -> bool:
    if isinstance(a, float) and isinstance(b, float):
        return math.isclose(a, b, rel_tol=TOLERANCE, abs_tol=0)
    return a == b


def shown(value: object) -> str:
    if value is None:
        return "missing"
    if isinstance(value, float):
        return format_number(value)
    return str(value)
```

Then implement, in this order, with the rules listed above:
- `_individuals(a: CanonicalStudy, changes) -> set[str]`: names of A's groups with count 1 (change `group_count_1` per name).
- `_subjects(study, as_individuals: set[str]) -> dict[str, tuple]`.
- `_records(study, as_individuals, changes | None) -> dict[tuple, list[Statistics]]`: applies the A-side transformations when `changes` is given (`array_output`, `gmean` moves `mean` to `gmean`, `image_converted` rewrites the suffix, `scatter_label` renames labels by the dataset dimensions).
- `_error_bars(a_stats, b_stats, changes) -> Statistics`: when B has `error_bar` and `error_type` and the spread of that type is None, and A's spread equals `abs(error_bar - mean)`, copy A's spread into B's statistics and drop `error_bar` and `error_type` on both, adding change `error_bar`.
- `_timecourses(study, keys) -> set`, `_scatters(study, keys) -> set`.
- `compare(a, b)`: matches the records by key; for each key sorts both lists by `tuple(shown(getattr(s, n)) for n in STATISTICS)` and compares pairwise; unmatched records and differing statistics become `Difference`s; then subjects, timecourses and scatters.
- `judge(v1, converted, vocabulary)`:

```python
def _errors(bundle) -> list[str]:
    return [f"{i.code}" for i in bundle.report.issues if i.severity == "error"]


def judge(v1: Path, converted: Path, vocabulary: Vocabulary) -> StudyResult:
    study = f"{v1.parent.name}/{v1.name}"
    try:
        a = prepare(v1, vocabulary=vocabulary)
    except StudyValidationError as error:
        return StudyResult(study=study, outcome="invalid_v1", issues=sorted({i.code for i in error.report.issues}))
    if errors := _errors(a):
        return StudyResult(study=study, outcome="invalid_v1", issues=sorted(set(errors)))
    formatted = format_folder(converted, check=True)
    if not formatted.ok or formatted.changes:
        return StudyResult(
            study=study,
            outcome="mismatch",
            differences=[Difference(path="format", a="canonical", b="needs formatting")],
        )
    try:
        b = prepare(converted, vocabulary=vocabulary)
    except StudyValidationError as error:
        codes = sorted({i.code for i in error.report.issues})
        return StudyResult(study=study, outcome="mismatch", differences=[Difference(path="validation", a="valid", b=", ".join(codes))])
    if errors := _errors(b):
        return StudyResult(study=study, outcome="mismatch", differences=[Difference(path="validation", a="valid", b=", ".join(sorted(set(errors))))])
    changes, differences = compare(a.study, b.study)
    if differences:
        return StudyResult(study=study, outcome="mismatch", changes=changes, differences=differences[:MAX_DIFFERENCES])
    return StudyResult(study=study, outcome="intended" if changes else "identical", changes=changes)
```

Check the attribute names of `FormatResult` (the list of changed files) in `formatter.py`. `prepare` copies each folder into a snapshot, so the gate never changes `v1` or `converted`.

- [ ] **Step 4: Run the tests, lint and types**

Run: `cd python && uv run --locked pytest -q tests/migration && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked ty check`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/migration/gate.py python/tests/migration/test_gate.py
git commit -m "Compare converted studies with their format 1 originals in an equivalence gate"
```

---

### Task 7: Report files

**Files:**
- Create: `python/src/pkdb/migration/report.py`, `python/tests/migration/test_report.py`

**Interfaces:**
- Consumes: `model.MigrationReport` and its parts; `pkdb.cache.atomic_text`.
- Produces:
  - `report.write_report(report: MigrationReport, path: Path) -> Path`: writes `path` (JSON, `model_dump(mode="json")`, sorted studies, two-space indent, final newline) and `path.with_suffix(".md")`; returns the Markdown path.
  - `report.markdown(report: MigrationReport) -> str`.

Markdown layout (one paragraph per line, tables for lists):
1. `# Study format 2 migration` and one line: `Dry run.` or `Written.`
2. `## Summary`: a table `| Class | Studies |` for the five classes plus `Skipped (format 2)`, `Moved to papers/`, `Empty folders removed`, `Recovered swaps`.
3. One section per class that has studies, in the order `mismatch`, `not_converted`, `invalid_v1`, `intended`, `identical`: `mismatch` lists study and its differences (`path`, A, B); `not_converted` lists study and reason; `invalid_v1` study and issue codes; `intended` study and changes (`kind` x count); `identical` study names in one comma-separated paragraph.
4. `## Manual decisions`: one subsection per decision kind with a table `| Study | Detail |`, with these headings: `group_count_1` "Groups with count 1 (now individuals)", `array_output` "Array outputs", `geometric_spread` "Geometric means with sd, se or cv", `schedule` "Converted dosing schedules", `unreferenced_sheet` "Sheets that study.json never used", `registry_date` "Dates that differ from the registry", `registry_sid` "Identifiers that differ from the registry", `image_converted` "Converted images", `removed_file` "Removed data files", `scatter_label` "Renamed scatter outputs"; plus subsections from the report itself: "Studies with two PKDB identifiers", "Registry paths that do not exist", "Sheet names outside the source pattern" (the `not_converted` studies with reason code `sheet_name`), "Folders moved to papers/" (with a `workbook` column).
5. Table cells escape `|` as `\|` and never contain line breaks.

- [ ] **Step 1: Write the failing tests**

`python/tests/migration/test_report.py`:

```python
import json

from pkdb.migration.model import (
    Change,
    Decision,
    Difference,
    MigrationReport,
    PaperMove,
    RegistryFindings,
    StudyResult,
)
from pkdb.migration.report import markdown, write_report

REPORT = MigrationReport(
    dry_run=True,
    studies=[
        StudyResult(study="caffeine/B2000", outcome="identical", written=False),
        StudyResult(
            study="caffeine/A1999",
            outcome="mismatch",
            differences=[Difference(path="measurements[x].sd", a="0.5", b="0.6")],
            decisions=[Decision(kind="schedule", detail="D1: time 0, interval 12, doses 3")],
        ),
        StudyResult(study="caffeine/C2001", outcome="not_converted", reason="sheet_name: Sheet Fig1.2 is not a source name"),
        StudyResult(study="caffeine/D2002", outcome="intended", changes=[Change(kind="group_count_1", count=1, examples=["all"])]),
    ],
    skipped=["caffeine/E2003"],
    papers=[PaperMove(source="studies/caffeine/F2004", target="papers/caffeine/F2004", files=["F2004.pdf", "F2004.xlsx"], workbook=True)],
    registry=RegistryFindings(double_identifiers={"caffeine/A1999": ["PKDB00001", "PKDB00002"]}, missing_paths=["caffeine/Gone1990"]),
)


def test_the_json_report_is_sorted_and_complete(tmp_path):
    md = write_report(REPORT, tmp_path / "migration.json")
    data = json.loads((tmp_path / "migration.json").read_text())
    assert [s["study"] for s in data["studies"]] == [
        "caffeine/A1999",
        "caffeine/B2000",
        "caffeine/C2001",
        "caffeine/D2002",
    ]
    assert md == tmp_path / "migration.md"
    assert md.read_text() == markdown(REPORT)


def test_the_markdown_summary_and_sections():
    text = markdown(REPORT)
    assert text.startswith("# Study format 2 migration\n\nDry run.\n")
    assert "| mismatch | 1 |" in text
    assert "| Skipped (format 2) | 1 |" in text
    assert "| caffeine/A1999 | measurements[x].sd | 0.5 | 0.6 |" in text
    assert "| caffeine/C2001 | sheet_name: Sheet Fig1.2 is not a source name |" in text
    assert "### Converted dosing schedules" in text
    assert "| caffeine/A1999 | D1: time 0, interval 12, doses 3 |" in text
    assert "### Studies with two PKDB identifiers" in text
    assert "| caffeine/A1999 | PKDB00001, PKDB00002 |" in text
    assert "### Sheet names outside the source pattern" in text
    assert "| studies/caffeine/F2004 | papers/caffeine/F2004 | yes |" in text
    assert "\u2014" not in text


def test_cells_escape_pipes_and_line_breaks():
    report = MigrationReport(
        dry_run=False,
        studies=[StudyResult(study="x/Y", outcome="not_converted", reason="a|b\nc")],
    )
    assert "| x/Y | a\\|b c |" in markdown(report)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/migration/test_report.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkdb.migration.report'`.

- [ ] **Step 3: Implement `report.py`** following the layout above, with one function per section (`_summary`, `_classes`, `_decisions`, `_registry`, `_papers`) and a `_cell(text: str) -> str` that collapses whitespace and escapes `|`. Sort studies by `study` (natural order through `pkdb.studyformat.text.natural_key`) in both files. Write both files with `atomic_text` from `pkdb.cache`.

- [ ] **Step 4: Run the tests, lint and types**

Run: `cd python && uv run --locked pytest -q tests/migration && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked ty check`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/migration/report.py python/tests/migration/test_report.py
git commit -m "Write the migration report as JSON and as Markdown for review"
```

---

### Task 8: Runner: discovery, paper moves, process pool and atomic swaps

**Files:**
- Create: `python/src/pkdb/migration/run.py`, `python/tests/migration/test_run.py`

**Interfaces:**
- Consumes: Tasks 1 to 7; `pkdb.studyformat.validation.is_v2_folder`; `pkdb.vocabulary.bundled_vocabulary` (check the import path used by `preparation.py`); `pkdb.references.ReferenceResolver`.
- Produces:
  - `run.migrate(paths: list[Path], *, report: Path, registry: Path | None, approver: str | None, dry_run: bool = False, jobs: int | None = None, vocabulary: Vocabulary | None = None, resolver_factory: Callable[[], ReferenceResolver] = ReferenceResolver) -> MigrationReport`.
  - `run.repository_root(path: Path) -> Path`: the folder that contains `studies/`, found by walking up from `path`; `ValueError` when none.
  - `run.WORK = ".pkdb-migrate"`: the work folder below the repository root.

Behavior:
1. `root = repository_root(paths[0])`; every path must lie below `root / "studies"`.
2. **Recovery first:** for each `root/.pkdb-migrate/v1/<substance>/<name>` left by an interrupted swap: if `studies/<substance>/<name>` is missing, rename the backup back (the study stays v1); if it exists and is format 2, delete the backup (the swap had finished). Each case adds `<substance>/<name>` to `report.recovered`. Then delete `root/.pkdb-migrate`.
3. **Discovery:** the studies root gives every `studies/<substance>/<name>`; a substance folder gives its children; a study folder gives itself. Sort by natural key.
4. For each folder: empty (no files below it) is removed (`report.removed_empty`) unless `dry_run`; without `study.json` it moves to `root/papers/<substance>/<name>` with all its files (`report.papers`, `workbook` true when it holds an `.xlsx`; the move refuses an existing target and lists it as `not_converted` with reason `papers_exists`) unless `dry_run`; format 2 (`is_v2_folder`) is added to `report.skipped`; otherwise it is a task.
5. **Tasks** run through `multiprocessing.get_context("spawn").Pool(jobs or os.cpu_count())` with `imap_unordered` over a top-level function `_one(task) -> StudyResult` (a frozen dataclass `Task(v1: Path, work: Path, registry: Registry, approver: str | None, vocabulary: Vocabulary, dry_run: bool)`). `_one` converts into `work/<substance>/<name>` (a temporary folder for a dry run, `root/.pkdb-migrate/new/<substance>/<name>` otherwise), runs `judge`, and returns the result with the conversion decisions. `NotConverted` becomes `not_converted` with `reason=f"{code}: {message}"`; any other exception becomes `not_converted` with `reason=f"converter_error: {type(error).__name__}: {error}"`. With `jobs == 1`, run `_one` in the main process (the tests use it). `resolver_factory()` is called inside `_one`, once per study.
6. **Swaps** in the main process, one study at a time, only when not `dry_run` and the outcome is `identical` or `intended`: rename `studies/<substance>/<name>` to `.pkdb-migrate/v1/<substance>/<name>`, rename `.pkdb-migrate/new/<substance>/<name>` to `studies/<substance>/<name>`, then delete the backup; set `written=True`. Any other outcome deletes its work folder.
7. **Registry:** `report.registry = Registry.read(registry).findings(root)`; when not `dry_run` and every identifier of the registry is the `release.pkdb_id` of a format 2 `study.json` below `root/studies`, delete the registry file and set `deleted=True`.
8. Delete `root/.pkdb-migrate`, then `write_report(report, report_path)` and return the report.

- [ ] **Step 1: Write the failing tests**

`python/tests/migration/test_run.py`:

```python
import json

import pytest

from migration_fixtures import v1_full_example, v1_study, STUDY, SHEETS
from pkdb.migration import run as run_module
from pkdb.migration.run import migrate
from pkdb.references import ReferenceResolver
from pkdb.studyformat.validation import is_v2_folder


def offline():
    return ReferenceResolver(offline=True)


def go(root, vocabulary, **options):
    return migrate(
        [root / "studies"],
        report=root / "migration.json",
        registry=options.pop("registry", None),
        approver=options.pop("approver", None),
        jobs=1,
        vocabulary=vocabulary,
        resolver_factory=offline,
        **options,
    )


def test_a_proven_study_replaces_its_v1_folder(tmp_path, sf_vocabulary):
    folder = v1_full_example(tmp_path)
    report = go(tmp_path, sf_vocabulary)
    assert [(s.study, s.outcome, s.written) for s in report.studies] == [("caffeine/Example", "identical", True)]
    assert is_v2_folder(folder) and not (folder / "Example.xlsx").exists()
    assert not (tmp_path / ".pkdb-migrate").exists()
    assert (tmp_path / "migration.md").exists()


def test_a_dry_run_writes_only_the_report(tmp_path, sf_vocabulary):
    folder = v1_full_example(tmp_path)
    before = sorted(p.name for p in folder.iterdir())
    report = go(tmp_path, sf_vocabulary, dry_run=True)
    assert report.studies[0].written is False
    assert sorted(p.name for p in folder.iterdir()) == before
    assert (tmp_path / "migration.json").exists()


def test_a_mismatch_stays_v1(tmp_path, sf_vocabulary, monkeypatch):
    folder = v1_full_example(tmp_path)
    monkeypatch.setattr(run_module, "judge", lambda v1, v2, vocabulary: run_module.StudyResult(study="caffeine/Example", outcome="mismatch"))
    report = go(tmp_path, sf_vocabulary)
    assert report.studies[0].written is False
    assert (folder / "Example.xlsx").exists()


def test_a_rerun_skips_converted_studies_and_retries_the_rest(tmp_path, sf_vocabulary):
    v1_full_example(tmp_path)
    broken = {**STUDY, "name": "Broken", "sid": "Broken", "outputset": {"outputs": [{**STUDY["outputset"]["outputs"][0], "source": "Fig1.2"}]}}
    v1_study(tmp_path, broken, {"Fig1.2": SHEETS["Tab2"]}, ("Tab1", "TabA"))
    first = go(tmp_path, sf_vocabulary)
    assert {s.study: s.outcome for s in first.studies} == {"caffeine/Broken": "not_converted", "caffeine/Example": "identical"}
    second = go(tmp_path, sf_vocabulary)
    assert second.skipped == ["caffeine/Example"]
    assert [s.study for s in second.studies] == ["caffeine/Broken"]


def test_folders_without_study_json_move_to_papers_and_empty_ones_go(tmp_path, sf_vocabulary):
    paper = tmp_path / "studies" / "caffeine" / "Paper2001"
    paper.mkdir(parents=True)
    (paper / "Paper2001.pdf").write_bytes(b"%PDF")
    (paper / "Paper2001.xlsx").write_bytes(b"xlsx")
    (tmp_path / "studies" / "caffeine" / "Empty2002").mkdir()
    report = go(tmp_path, sf_vocabulary)
    assert [(m.target, m.workbook) for m in report.papers] == [("papers/caffeine/Paper2001", True)]
    assert (tmp_path / "papers" / "caffeine" / "Paper2001" / "Paper2001.xlsx").exists()
    assert not paper.exists()
    assert report.removed_empty == ["caffeine/Empty2002"]


def test_an_exception_in_one_study_does_not_stop_the_run(tmp_path, sf_vocabulary, monkeypatch):
    v1_full_example(tmp_path)

    def broken(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(run_module, "convert_study", broken)
    report = go(tmp_path, sf_vocabulary)
    [result] = report.studies
    assert (result.outcome, result.reason) == ("not_converted", "converter_error: RuntimeError: boom")


def test_an_interrupted_swap_is_restored_on_the_next_run(tmp_path, sf_vocabulary):
    folder = v1_full_example(tmp_path)
    backup = tmp_path / ".pkdb-migrate" / "v1" / "caffeine" / "Example"
    backup.parent.mkdir(parents=True)
    folder.rename(backup)  # interrupted after the first rename of a swap
    report = go(tmp_path, sf_vocabulary, dry_run=True)
    assert report.recovered == ["caffeine/Example"]
    assert (folder / "Example.xlsx").exists()


def test_the_registry_is_deleted_once_every_study_is_released(tmp_path, sf_vocabulary):
    v1_full_example(tmp_path)
    registry = tmp_path / "studies" / "study_identifiers.json"
    registry.write_text(json.dumps({"PKDB00042": ["caffeine/Example", "2020-01-02"]}))
    report = go(tmp_path, sf_vocabulary, registry=registry, approver="mkoenig")
    assert report.registry.deleted
    assert not registry.exists()


def test_paths_outside_a_studies_folder_are_refused(tmp_path, sf_vocabulary):
    with pytest.raises(ValueError, match="studies"):
        migrate([tmp_path], report=tmp_path / "r.json", registry=None, approver=None, jobs=1, vocabulary=sf_vocabulary)
```

Add one test that runs with `jobs=2` on two studies (the spawn pool), asserting both results; mark it with the existing slow marker if the suite has one (check `pyproject.toml`), else keep it, it should take a few seconds.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/migration/test_run.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkdb.migration.run'`.

- [ ] **Step 3: Implement `run.py`** with the behavior above. Keep each step a function: `repository_root`, `_recover(root, report)`, `_discover(paths, root) -> list[Path]`, `_triage(folders, root, report, dry_run) -> list[Path]` (empty, papers, skipped), `_one(task)`, `_swap(root, folder)`, `_registry(root, registry_path, report, dry_run)`. Use `shutil.move` only within the repository (same file system), so each rename is atomic. Import `convert_study`, `judge` and `StudyResult` into `run.py`'s namespace as the tests monkeypatch them there.

- [ ] **Step 4: Run the tests, lint and types**

Run: `cd python && uv run --locked pytest -q tests/migration && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked ty check`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/migration/run.py python/tests/migration/test_run.py
git commit -m "Run the migration over study folders with paper moves, a process pool and atomic swaps"
```

---

### Task 9: `pkdb migrate`, corpus test and cutover runbook

**Files:**
- Create: `python/src/pkdb/migration_cli.py`, `python/tests/migration/test_cli.py`, `python/tests/test_migration_corpus.py`, `docs/study-format-2-cutover.md`
- Modify: `python/src/pkdb/cli.py` (register and dispatch), `zensical.toml` (navigation), `docs/installation.md` (opt-in corpus test line, where the other corpus variables are documented; search for `PKDB_STUDY_CORPUS`)

**Interfaces:**
- Consumes: `run.migrate`, `report` paths.
- Produces: `migration_cli.register(commands) -> None`, `migration_cli.run(args) -> int`.

Command:

```
pkdb migrate PATH... [--registry FILE] [--approver USER] [--report FILE]
             [--dry-run] [--jobs N] [--format human|json]
```

- `--registry` defaults to `<root>/studies/study_identifiers.json` when that file exists.
- `--approver` is required when a registry is used; the error is `--approver is required with a registry: name the maintainer who approves released studies`.
- `--report` defaults to `migration.json` in the current folder.
- Human output: one line per class with its count, then `Report: <md path>`. JSON output: the report as JSON on stdout. Exit code 0 when no study is `mismatch`, `invalid_v1` or `not_converted`, else 1 (so the cutover loop can stop on 0).

- [ ] **Step 1: Write the failing CLI tests**

`python/tests/migration/test_cli.py`:

```python
import json

from migration_fixtures import v1_full_example
from pkdb.cli import main


def test_migrate_dry_run_prints_counts_and_exits_zero(tmp_path, monkeypatch, capsys, sf_vocabulary):
    v1_full_example(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("pkdb.migration_cli.bundled_vocabulary", lambda: sf_vocabulary)
    code = main(["migrate", "studies", "--dry-run", "--jobs", "1", "--format", "human"])
    out = capsys.readouterr().out
    assert code == 0
    assert "identical: 1" in out
    assert "Report: " in out and (tmp_path / "migration.md").exists()


def test_a_registry_needs_an_approver(tmp_path, monkeypatch, capsys):
    v1_full_example(tmp_path)
    (tmp_path / "studies" / "study_identifiers.json").write_text(json.dumps({}))
    monkeypatch.chdir(tmp_path)
    code = main(["migrate", "studies", "--dry-run"])
    assert code == 2
    assert "--approver is required with a registry" in capsys.readouterr().err
```

Check how `pkdb.cli.main` takes arguments and returns exit codes (other CLI tests in `python/tests/test_cli.py`) and adapt the calls. Make the vocabulary injectable the way other commands do in their tests if a monkeypatch of `bundled_vocabulary` is not the existing pattern.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/migration/test_cli.py`
Expected: FAIL (`invalid choice: 'migrate'`).

- [ ] **Step 3: Implement `migration_cli.py` and register it in `cli.py`** following `studyformat_cli.py` (a `register(commands)` that adds the parser, and a `run(args)` called from the dispatch chain in `cli.main`, next to `if args.command in {"format", "schema"}`). Description: "Convert study format 1 folders into study format 2, proven by an equivalence gate with the format 1 parser".

- [ ] **Step 4: Write the opt-in corpus test**

`python/tests/test_migration_corpus.py`:

```python
"""Convert real studies of pkdb_data, copied first: PKDB_STUDY_CORPUS=<pkdb_data>/studies."""

import os
import shutil
from pathlib import Path

import pytest

from pkdb.migration.run import migrate

CORPUS = os.environ.get("PKDB_STUDY_CORPUS")
STUDIES = (
    "acetaminophen/Abernethy1982",
    "caffeine/Harder1988",
    "albuterol/Guo2016",
)
pytestmark = pytest.mark.skipif(not CORPUS, reason="PKDB_STUDY_CORPUS is not set")


def copy(names, target):
    for name in names:
        shutil.copytree(Path(CORPUS) / name, target / "studies" / name)


def test_the_named_studies_convert_without_converter_errors(tmp_path):
    copy(STUDIES, tmp_path)
    report = migrate([tmp_path / "studies"], report=tmp_path / "migration.json", registry=None, approver=None, dry_run=True)
    assert len(report.studies) == len(STUDIES)
    assert not [s for s in report.studies if (s.reason or "").startswith("converter_error")]


@pytest.mark.skipif(not os.environ.get("PKDB_MIGRATION_FULL"), reason="PKDB_MIGRATION_FULL is not set")
def test_the_whole_corpus_converts_without_converter_errors(tmp_path):
    shutil.copytree(Path(CORPUS), tmp_path / "studies")
    report = migrate([tmp_path / "studies"], report=tmp_path / "migration.json", registry=None, approver=None, dry_run=True)
    errors = [s.study for s in report.studies if (s.reason or "").startswith("converter_error")]
    assert errors == []
```

Add a scatter study and an individual-level study of the caffeine folder to `STUDIES`: pick them by running `grep -l '"scatter"' studies/caffeine/*/study.json` and `grep -l '"individualset"' studies/caffeine/*/study.json` in pkdb_data (read only) and choose studies whose licence is open. Run the corpus test once locally with `PKDB_STUDY_CORPUS=/home/mkoenig/git/pkdb_data/studies`; fix converter errors it finds (each fix with its own unit test in the module's test file). Record the class counts of the five studies in the commit message.

- [ ] **Step 5: Write the cutover runbook**

`docs/study-format-2-cutover.md`, one paragraph per source line, with these sections:
1. `# Study format 2 cutover` and one paragraph: what the cutover does and that it runs after the pkdb_data tooling (pre-commit, CI, issue sync workflow) exists.
2. `## Before the run`: fix the 20 invalid `study.json` files and the studies that are invalid in format 1 by normal pull requests; merge or pause open curation pull requests.
3. `## Convert`: on a branch of pkdb_data, `pkdb migrate studies --approver <maintainer> --dry-run`, read `migration.md`, fix format 1 studies (sheet names, images, invalid studies) or report converter bugs; then run without `--dry-run`; repeat until `pkdb migrate` exits with 0 (no `mismatch`, `invalid_v1` or `not_converted`). Explain the classes in a table and that each run converts only the studies that pass, so reruns are safe. Mention that an interrupted run is finished or undone by the next run.
4. `## Review and merge`: tag `v1-final` on `develop`, review through `migration.md` (summary, manual decisions) and spot checks, merge one pull request with green CI.
5. `## After the merge`: `pkdb issues sync --adopt --dry-run`, review, run; re-upload all studies with processing version 9 to staging and compare counts and API output with production; delete the format 1 code once no format 1 branch is open.
6. `## Papers`: folders without `study.json` live in `papers/<substance>/<name>/`; `pkdb new` takes the PDF and images from there.

Add it to `zensical.toml` in the development navigation after "Local upload testing": `{ "Study format 2 cutover" = "study-format-2-cutover.md" },`. In `docs/installation.md`, next to the other opt-in corpus tests, add one paragraph: `PKDB_STUDY_CORPUS=<pkdb_data>/studies uv run --locked pytest -q tests/test_migration_corpus.py` converts named studies in a dry run, and `PKDB_MIGRATION_FULL=1` adds the whole corpus.

- [ ] **Step 6: Run every gate**

Run:
```bash
cd python && uv run --locked pytest -q -x && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked ty check
cd .. && uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean
```
Expected: all pass; the docs build prints no warning.

- [ ] **Step 7: Commit**

```bash
git add python/src/pkdb/migration_cli.py python/src/pkdb/cli.py python/tests/migration/test_cli.py python/tests/test_migration_corpus.py docs/study-format-2-cutover.md zensical.toml docs/installation.md
git commit -m "Add pkdb migrate, an opt-in corpus test and the study format 2 cutover runbook"
```

- [ ] **Step 8: Release note, once the pull request exists**

Add at the top of `release-notes/unreleased.md` one paragraph, with the number that `gh-axi pr create` printed in place of `NUMBER`: "- Convert study format 1 folders into study format 2 with `pkdb migrate` (#NUMBER). Each study is converted from the entities that the format 1 parser resolved, checked by an equivalence gate against that parser, and replaces its format 1 folder only when its data is identical or differs only by intended changes (groups with count 1 become individuals, `ABS(X - mean)` formulas become error bars, geometric means move to `gmean`, array outputs become outputs or timecourses, JPG images become PNG). Released studies take their PKDB identifier and date from `study_identifiers.json` and are approved by the maintainer given with `--approver`; folders without `study.json` move to `papers/`. `migration.json` and `migration.md` list every study with its class, differences and the decisions to check by hand; `--dry-run` writes only the report. See the new **Study format 2 cutover** page." Commit it with the message "Add the release note of pkdb migrate".

---

## Self-Review

- Spec coverage: converter steps 1 to 5 (Tasks 1 to 5), command and incremental write mode, papers, registry deletion, process pool (Task 8, Task 9), gate and five classes (Task 6), report files and decision lists (Task 7), runbook (Task 9), testing section 8 (synthetic fixtures in Tasks 3 to 8, corpus in Task 9). Parts B and C are separate plans.
- The intended change "empty count inherited" of the spec needs no transformation: both sides go through `prepare_study`, which fills counts the same way; the gate never sees it as a change. The sid, release and review changes are metadata, which the gate does not compare.
- Review Focus items have tests in Tasks 3, 5 and 8.
