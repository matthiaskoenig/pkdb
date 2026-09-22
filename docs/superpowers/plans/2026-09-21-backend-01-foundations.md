# Backend Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish executable compatibility evidence and a Django-free importer/scientific core on Python 3.13 and 3.14.

**Architecture:** Characterize legacy behavior in its own environment, then develop a separate installable replacement package. Canonical Pydantic records and pure domain functions are the boundary used by subsequent persistence and interface plans.

**Tech Stack:** uv, Ruff, ty, pytest, CPython 3.13/3.14, Pydantic v2, pandas, Pint, NumPy, SciPy, existing PK analysis library.

**Spec:** [Backend design](../specs/2026-09-21-backend-replacement-design.md). Read the [plan index](2026-09-21-backend-replacement.md) for workspace rules, budgets, and delivery order.

## Global Constraints

- Support CPython 3.13 and 3.14 on standard GIL-enabled builds.
- Declare `requires-python = ">=3.13,<3.15"` and Ruff `target-version = "py313"`.
- The server always performs its own validation.
- Existing study SIDs and vocabulary identifiers remain stable.
- Remove Django, DRF, Elasticsearch, and their integration dependencies.
- No source study modifications; no private fixture contents in git.

## Review Focus

1. Missing/zero/NaN cells and booleans interpreted as numbers — F3.
2. A sheet comment or skipped header changes provenance coordinates — F3.
3. Unit conversion mutates reported values or loses molecular-weight context — F4.
4. Python 3.14 installs but scientific/native imports fail — F2/F4.
5. Golden snapshots normalize away meaningful differences — F1 uses a narrow allowlist.

## File and interface map

- `tools/backend_migration/`: legacy evidence capture and comparison, not runtime dependencies.
- `backend-next/src/pkdb/schemas/`: `source.py`, `study.py`, `validation.py`.
- `backend-next/src/pkdb/importers/`: `folder.py`, `workbook.py`, `expressions.py`.
- `backend-next/src/pkdb/domain/`: `vocabulary.py`, `validation.py`, `units.py`,
  `normalization.py`, `statistics.py`, `pharmacokinetics.py`.
- `backend-next/tests/`: synthetic fixtures, pure unit tests, approved contract fixtures.

Define these interfaces in the task indicated; later plans must use these names:

```python
# F3: schemas/source.py
# SourceBundle: study: dict[str, object], reference: dict[str, object],
#               files: dict[str, pathlib.Path]
# SourceLocation: file: str, sheet: str | None, row: int | None,
#                 column: str | None, path: tuple[str | int, ...]
# schemas/validation.py
# ValidationIssue: code: str, severity: Literal['error', 'warning'],
#                  message: str, source: SourceLocation | None
# ValidationReport: issues: list[ValidationIssue], truncated: bool;
#                   valid property is false if any issue is an error.
# StudyValidationError(Exception): report: ValidationReport
# schemas/study.py
# CanonicalStudy: sid, metadata, reference, groups, individuals,
#   interventions, measurements, timecourses, scatters, descriptions,
#   comments, attachments, source_digest; nested entities are typed models.
# Entity source keys are unique within (study SID, entity kind).
# Measurement: key, subject reference, intervention references,
#   measurement_type, substance, tissue, method, statistics, unit,
#   source, origin ('reported'/'normalized'/'calculated'), derived_from.
# Timecourse: key, ordered point records and associated measurement metadata.
# Typed models reflect all fields in F1's inventory, with no arbitrary extras.

def load_folder(path: Path) -> SourceBundle: ...  # F3 importers/folder.py

def parse_bundle(bundle: SourceBundle) -> CanonicalStudy: ...  # F3

# F4: domain/vocabulary.py; immutable snapshot keyed by stable identifiers.
# Vocabulary: version, nodes, units, substances, choices and measurement rules.
# PreparedStudy: study: CanonicalStudy, report: ValidationReport,
#                vocabulary_version: str, processing_version: str

def prepare_study(study: CanonicalStudy, vocabulary: Vocabulary) -> PreparedStudy: ...
# F4 domain/validation.py; raises StudyValidationError on errors.
```

These are interface declarations, not permission to leave stub implementations.
F3 defines nested model fields from the captured contract before implementation;
each entity is tested separately. `dict[str, object]` is restricted to raw input,
not an escape hatch for canonical scientific models.

### F1: Capture behavior, corpus, and baseline

**Files:** Create `tools/backend_migration/{__init__,contracts,compare,benchmark}.py`,
`tools/backend_migration/test_compare.py`, and the five evidence documents named in
the plan index. Read legacy URLs/serializers/managers, frontend consumers, existing
unit tests, and `backend/pkdb_data/management/`.

**Interfaces:** `compare_records(expected: object, actual: object, *, ignored_paths:
frozenset[str]) -> list[str]` returns differing JSON paths. Contract records identify
request method/path, query/body fixture, response/status, role, and test owner.

- [ ] Write comparison tests before capturing any baseline:

```python
from tools.backend_migration.compare import compare_records

def test_missing_is_not_zero():
    assert compare_records({'mean': None}, {'mean': 0}, ignored_paths=frozenset())

def test_only_explicit_volatile_paths_are_ignored():
    assert compare_records({'sid': 'A'}, {'sid': 'B'},
                           ignored_paths=frozenset({'$.request_id'}))
```

- [ ] Run `uv run --project backend --extra dev pytest tools/backend_migration/test_compare.py -q`;
  expect missing-module failure. Implement recursive type/key/list comparisons and
  explicit path exclusions; rerun to PASS. Exclude only captured volatile fields
  such as timestamps/request IDs, not arrays, units, nulls, or scientific values.
- [ ] Add route enumeration from Django URL resolution and consumer references;
  create a contract row for every route/action, with read/write/auth/download
  variants. Capture synthetic public/private studies and actual apixaban outcomes
  against an isolated legacy service. Never write to production. Hash source files
  before/after to prove capture leaves them unchanged.
- [ ] Implement a benchmark CLI with `--base-url`, `--corpus`, `--output`,
  `--runs 5`; take credentials from environment without logging them. Wait for
  query visibility after each legacy index operation. Record input hashes,
  hardware, cold/warm times, memory observations, and reads. Compute concrete
  budgets using the index's 1.10 multiplier and commit shareable metrics only.
- [ ] Inventory failures and database-only content. Record which fixtures require
  authorized local/private data. A missing private corpus is reported as a blocked
  corpus gate, never silently replaced by a synthetic passing result.
- [ ] Commit only evidence tooling, synthetic fixtures, and shareable manifests:
  `git commit -m "test: characterize legacy backend contracts and performance"`.

### F2: Create the supported replacement package

**Files:** Create `backend-next/pyproject.toml`, `uv.lock`, `.python-version`,
`src/pkdb/__init__.py`, `src/pkdb/config.py`, `tests/test_runtime.py`, and
`tests/conftest.py`. Create `.github/workflows/backend-next.yml` as an additive
workflow; do not alter the old required CI checks yet.

**Interfaces:** Importable `pkdb` package; `Settings` in `pkdb.config` reads
`PKDB_DATABASE_URL`, `PKDB_FILE_ROOT`, `PKDB_UPLOAD_MAX_BYTES`,
`PKDB_UPLOAD_MAX_FILES`, `PKDB_UPLOAD_CONCURRENCY`, `PKDB_UPLOAD_MAX_ROWS`.
Production settings have no default password or production/test DB fallback.
Tests override file root and database URL explicitly.

- [ ] Add a package/runtime test:

```python
import importlib
import sys

def test_supported_runtime_and_scientific_imports():
    assert sys.version_info[:2] in {(3, 13), (3, 14)}
    for name in ('pkdb', 'pydantic', 'numpy', 'scipy', 'pandas', 'pint'):
        importlib.import_module(name)
```

- [ ] Create minimal Hatchling packaging so test collection can run and fail on
  missing `pkdb`. Use `src/pkdb`, static initial version `0.1.0`, and:

```toml
[project]
name = "pkdb"
version = "0.1.0"
requires-python = ">=3.13,<3.15"

[tool.ruff]
target-version = "py313"

[tool.ty.environment]
python-version = "3.13"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] Add stable dependencies with uv: Pydantic `>=2,<3`, pydantic-settings,
  pandas, NumPy, SciPy, Pint, openpyxl and the current PK analysis source at its
  immutable commit. Add pytest, HTTPX, Ruff and ty as development dependencies.
  Test `pkdb_analysis.pk.pharmacokinetics` import on both Pythons. If its locked
  transitive dependencies conflict, characterize and update that dependency with
  numerical regression evidence before proceeding; never suppress the matrix.
- [ ] Implement the empty package and validated `Settings`; require positive
  size/concurrency limits. Select conservative defaults: 256 MiB input, 256 files,
  1,000,000 expanded rows, two simultaneous uploads per process. These are
  configurable initial caps; F1 corpus sizes and A6 RSS measurements validate them.
- [ ] Run locked installation and tests with each interpreter using separate
  `.venv-py313`/`.venv-py314` directories via `UV_PROJECT_ENVIRONMENT`; run
  `uv build --project backend-next`. Add required matrix entries:

```yaml
strategy:
  fail-fast: false
  matrix:
    python: ["3.13", "3.14"]
```

  Each job syncs locked dependencies, runs tests and ty, builds a wheel, installs
  that wheel in a clean environment, and imports the package/scientific modules.
  Ruff checks target 3.13. Record exact resolved versions and both installation
  results in `docs/backend-migration/dependencies.md`.
- [ ] Commit package and additive CI as `build: establish Python 3.13 and 3.14 backend`.

### F3: Parse unchanged study folders with source provenance

**Files:** Create the three `schemas/` and three `importers/` files listed above;
`tests/unit/test_importer.py`, `tests/unit/test_expressions.py`,
`tests/fixtures/minimal/study.json`, `reference.json`, and
`tests/fixtures/make_workbook.py`. Update `tests/conftest.py`.

**Interfaces:** Produce F3 declarations above. The `synthetic_folder` pytest
fixture creates a temporary workbook with a header/comment row and two measurements
(one zero and one empty cell), a matching `col==mean` mapping, and a reference;
returns a `Path`. `valid_bundle` returns `load_folder(synthetic_folder)`.

- [ ] Add focused failing tests (import functions from `pkdb.importers.folder`):

```python
from pkdb.importers.folder import load_folder, parse_bundle

def test_missing_and_zero_are_distinct(synthetic_folder):
    study = parse_bundle(load_folder(synthetic_folder))
    assert [m.statistics.mean for m in study.measurements] == [0.0, None]
    assert all(m.source.row is not None for m in study.measurements)
```

- [ ] Run `uv run --project backend-next --locked pytest backend-next/tests/unit/test_importer.py -q`;
  expect missing parser failure. Define typed metadata, subject, intervention,
  statistics, measurement, timecourse, scatter, reference, and attachment models
  from F1, one model/test at a time. Canonical models use `extra='forbid'` and
  deliberate field coercion; raw folder aliases normalize before these models.
- [ ] Implement workbook parsing with existing skipped header/comment conventions,
  sheet-name and column rules; preserve raw row coordinates before dropping rows.
  Tokenize supported column/source expressions from legacy `MappingSerializer`
  using an explicit grammar/dispatch table, never `eval`. Resolve joined sources,
  filenames, group references, and curator variants from the characterized cases.
- [ ] Add tests for unknown expressions/keys, duplicate file basenames, unknown
  sheets/columns, traversal/symlink escape, empty sheets, boolean numeric values,
  unsupported non-finite values, and row expansion over the configured cap.
  Each expected failure raises `StudyValidationError` with a stable code and
  source coordinates where available. Explicitly test literal zero is retained.
- [ ] Run all unit tests on 3.13 and 3.14. Add a corpus-marked test parsing every
  apixaban folder from `PKDB_STUDY_CORPUS`; its absence fails the explicit corpus
  job rather than silently skipping it. Compare canonical source values against
  F1 captures; source hashes must remain unchanged.
- [ ] Commit as `feat: parse legacy study bundles into typed canonical records`.

### F4: Transfer scientific validation, normalization, and PK calculations

**Files:** Create the six domain files listed in the map plus
`schemas/prepared.py`, `tests/unit/test_scientific_rules.py`,
`tests/unit/test_normalization.py`, `tests/unit/test_pharmacokinetics.py`.
Read legacy `behaviours.py`, `error_measures.py`, `info_nodes/models.py`,
`info_nodes/units.py`, `outputs/pk_calculation.py`, and subject/data managers.

**Interfaces:** Produce `Vocabulary`, `PreparedStudy`, and `prepare_study` defined
above. `convert_value(value: float, source_unit: str, target_unit: str) -> float`
in `domain/units.py` uses the shared registry; context-dependent normalization
accepts explicit substance/body-size metadata through canonical records.
`calculate_sd`, `calculate_se`, and `calculate_cv` retain the legacy signatures.
`vocabulary` fixture loads a small versioned vocabulary covering synthetic cases.

- [ ] Write a numerical regression test before porting the corresponding function:

```python
import numpy as np
import pytest
from pkdb.domain.statistics import calculate_sd
from pkdb.domain.units import convert_value

def test_sd_from_se():
    assert calculate_sd(se=np.array([1.0]), count=np.array([4]),
                        cv=None, mean=None) == pytest.approx([2.0])

def test_mass_conversion():
    assert convert_value(1.0, 'mg', 'ug') == pytest.approx(1000.0)
```

- [ ] Run `uv run --project backend-next --locked pytest backend-next/tests/unit/test_scientific_rules.py backend-next/tests/unit/test_normalization.py -q`;
  expect missing functions. Port functions without ORM lookups. Preserve registry
  definitions, calculation-type distinctions, missing-value behavior, and input
  immutability. Test each legacy rule and boundary before its implementation.
- [ ] Implement `prepare_study` using in-memory key maps: validate references and
  cycles, validate measurement-specific statistics/choices/units, normalize, then
  derive PK values. Return warnings in the report; errors raise the typed
  exception. Derived records link to their source keys and processing versions.
  Never use `if value` where zero is valid. Validate calculated finite values.
- [ ] Add PK golden tests for no-dose and single-dose timecourses, missing/zero
  concentrations, non-monotonic/duplicate times, multiple interventions, incompatible
  dimensions, missing molecular weight, and missing normalization prerequisites.
  Use tolerances recorded per quantity in fixture metadata; start with `rtol=1e-9`
  for deterministic algebra and `rtol=1e-6` for fitted PK values, with dimensional
  absolute tolerances justified by F1 data. Differences require investigation.
- [ ] Ensure prepared data never mutates source records. Test aggregate issue cap,
  unknown vocabulary, hierarchy cycles, and warning-only new quality rules.
  Run all pure tests and apixaban numerical comparisons on both interpreters;
  subprocess-import the domain with no Django settings or database available.
- [ ] Commit as `feat: transfer scientific rules to framework-independent services`.

## Phase acceptance

- [ ] F1 artifacts contain real observed contracts/baselines, not guessed values.
- [ ] Both interpreter environments install/build/run pure scientific tests.
- [ ] Canonical models cover every inventoried entity without `Any` escape fields.
- [ ] Apixaban parsing and numerical comparison have no unexplained differences.
- [ ] Review the interfaces before moving to ingestion; update all downstream
  signatures together if a discovered legacy behavior requires a change.
