# Internal scientific data model

PK-DB stores groups and individuals as subjects, and characteristics and outputs as observations. The curation files and API response shapes remain compatible; group/individual and characteristic/output names at those interfaces are adapters over the shared storage.

## Publications, studies, and acquisition sources

A study is uniquely identified by `(publication_id, source_key)`. Publication identity is shared through normalized PMID/DOI aliases. Each study keeps its own citation snapshot, scientific graph, access controls, and attachments. Manual curation and an OSP import of the same paper therefore coexist; refreshing the import does not modify the manual study.

Study metadata has discriminated acquisition records: `ManualCuration` (`manual_curation`), `DataImport` (`data_import`), and `AutomaticCuration` (`automatic_curation`). Existing studies default to `pkdb.manual`. Import provenance records the stable provider key, release, revision, importer version, source URLs/checksums, and upstream dataset IDs. Acquisition is independent of the numerical representation (`reported`, `normalized`, `calculated`). New releases replace the same source study; a different SID for an existing publication/source pair is rejected.

Identifiers may be enriched with additional aliases, but contradictory aliases or publication/source changes require explicit reconciliation. Without a PMID or DOI, a source URL or explicit reference SID provides provisional identity; titles alone are not used to infer matches across sources. Migration `p004sources` backfills existing manual studies and stops on duplicate publication identities rather than silently merging them.

See [OSP import](osp-import.md) and [public dataset imports](public-dataset-imports.md) for conversion, validation, provenance, and known source limitations. `DataImport` additionally records `evidence_kind`, `reference_scope`, and `source_terms`; missing classifications default to `unknown`. The attached report links native records to original artifact rows and mapping operations.

## Study identity, release and review

A study in study format 2 has the `sid` `<substance>/<name>`, the location of its folder (for example `caffeine/Harder1988`), and its `name` is the folder name. A study in study format 1 keeps its single-segment `sid` (for example `PKDB01110`) until its folder is migrated. The `sid` column holds both. Released studies additionally store a unique `pkdb_id` (`PKDB` and five digits) and the `release_date`, which is also the study `date`; the two are set together. A released study keeps its `pkdb_id` when it is renamed or corrected.

Studies also store the number of their curation `issue`, the `review_status` (`draft`, `in_review` or `approved`) and the `review` document with the reviewers and review items of `review.json`. The study text search includes the `pkdb_id`. An upload of a released study whose `sid` is not stored yet takes over the study that has its `pkdb_id` (or, for a study format 1 study, that `sid`) and renames it, so no data reset is needed; both identifiers are locked in a fixed order, so concurrent renames and uploads cannot deadlock. The API serves such a study under `/api/v2/studies/{substance}/{name}` and redirects its PKDB identifier there, see [study identifiers](api.md#study-identifiers-and-redirects).

## Subjects and observations

A subject has a study, name, kind, count, and optional parent. An individual has count one, but a group containing one participant remains a group. A group with an unreported sample size has a null count. Individual identity and group hierarchy are retained. Every observation has one subject reference.

`observations` stores scientific identity and context, including the measurement type, substance, subject, method, tissue, time, source, and whether the result was calculated. Characteristics, outputs and interventions share this context: study format 2 gives all three tissue, method, time, time unit, the flags for a time or unit that the publication does not report, and the image of the paper table or figure. Interventions keep the same fields in their own table. `observation_values` stores its numerical representations and units. Reported and normalized values share context when the metadata agrees; their original values, keys, and derivation links remain distinct. Intervention associations are stored once on the shared observation context.

Processing version 9 has no `value` statistic. The value of one subject and the central value of an `unspecified summary` are stored in `mean`: an individual's `mean` is that subject's value and cannot be combined with population statistics or a calculation type, and a group's `mean` is its arithmetic mean unless the calculation type is the built-in vocabulary term `unspecified summary`. The latter marks a central value whose statistic the publication does not state; it cannot claim any other statistic, is not completed, and does not produce derived PK parameters. Mean, median, uncertainty, and missing versus zero retain their scientific meanings.

Statistics are `mean`, `median`, `min`, `max`, `sd`, `se`, `cv`, `gmean`, `gsd`, `gcv` and `count`, plus a digitized `error_bar` whose `error_type` (`sd`, `se` or `gsd`) names the statistic it shows. `cv` and `gcv` are fractions in the model and the API, `gsd` is a dimensionless factor of at least one. Study format 2 tables enter `cv` and `gcv` in percent and the reader divides them by 100. An intervention carries the same statistics, with the dose in `mean`.

Characteristics and outputs use the same subject count defaults and group statistical completion. An explicit measurement count is retained; otherwise group count or one for an individual supplies the default. Unknown group counts remain null. Completion never overwrites a reported value and happens in the normalized representation of group records with a sample mean (or no calculation type): `sd`, `se` and `cv` are derived from each other with `count` and `mean`, `gsd` and `gcv` from each other, and `sd`, `se` or `gsd` from `error_bar` (the distance of the bar from `mean`, or the factor between `error_bar` and `gmean`). Arithmetic and geometric statistics are never derived from each other. Unit conversion scales `mean`, `gmean` and `error_bar` and leaves `gsd`, `gcv` and `cv` unchanged. Reported `sd`, `se` and `cv`, or `gsd` and `gcv`, that contradict each other by more than 2 percent produce the warning `inconsistent_statistics` at the first disagreeing cell, which a review item can acknowledge. The API orders measurement and intervention rows on request by this central value (`central_value`): the mean, else the median, else the geometric mean.

Intervention times are structured. `time` is the time of one administration or a list of at least two administration times, `interval` is the dosing interval, `doses` the number of administrations, `time_end` the end of a continuous administration, and an optional `subject` names the group or individual that the dose statistics describe. Schedule strings are no longer stored. The study format 1 importer parses `0|12|40` into the time list `[0, 12, 40]` and `S0T24R7` (start, interval and number of administrations, `R` counting administrations) into `time` 0, `interval` 24 and `doses` 7; a `|` list that mixes both expands to explicit times, and any other text is the error `invalid_schedule`. Migration `p006studyformat` converts stored schedule text with the same grammar.

```mermaid
erDiagram
    STUDY ||--o{ SUBJECT : contains
    SUBJECT ||--o{ OBSERVATION : describes
    OBSERVATION ||--|{ OBSERVATION_VALUES : represents
    OBSERVATION ||--o{ OBSERVATION_INTERVENTION : references
    STUDY ||--o{ DATASET : contains
    DATASET ||--o{ DATASET : organizes
```

## Datasets without point entities

The `datasets` table stores dataset containers and ordered series/course records. Each series stores an ordered array of observation representation IDs. Scatter rows are flattened in row-major order; dimension metadata defines the width, and a parallel array preserves row identifiers used by existing exports. Optional row source metadata is stored in an ordered JSON array. There are no `timecourse_points`, `subset_points`, or `subset_dimensions` tables.

Numerical observations remain available for scientific calculation and existing output APIs. Normal dataset responses load their referenced observations once and expand arrays in memory. Existing flat analysis/export APIs use a SQL projection of array positions when filtering or pagination requires it; that projection is not a persisted point entity. Multiple datasets can reference the same observation.

Database constraints validate array shape, complete scatter rows, same-study references, duplicate course membership, and valid parent/derivation kinds. Deferred validation allows atomic study replacement. Dataset membership writes and deletion of referenced values require the service's default `READ COMMITTED` isolation; incompatible write isolation is rejected explicitly. Read-only repeatable-read snapshots remain supported. The app never infers pairing from matching values or combines separate curves solely because their labels match.

## Fresh database setup

The migration history starts at the consolidated `p001initial` baseline. The subsequent `p002retirelegacy` migration removes obsolete upload drafts and ineffective reader grants while preserving published data. This baseline requires an empty database; upgrading a database stamped with an older revision is no longer supported. Do not stamp an existing schema with the new revision.

Follow the [local upload guide](local-upload-testing.md) to start the server, create an administrator, import users, and upload the original study folders again. Docker Compose applies the initial migration automatically. For a native installation, set `PKDB_DATABASE_URL` to the empty database and run:

```bash
cd backend
uv run --locked alembic upgrade head
uv run --locked alembic check
```

Use a processing-version-9 client. Re-uploaded studies receive new numeric identifiers; old numeric resource references and saved selections must be recreated. Study SIDs and source keys remain stable. The baseline includes search indexes, scientific integrity triggers, and initial security configuration. No historical ID conversion or point-table migration runs during setup.

## Upgrade to study format 2

Migration `p006studyformat` upgrades a database at `p005vocabsearch`. It adds the statistics `gmean`, `gsd`, `gcv`, `error_bar` and `error_type` to observation values and interventions, the schedule fields `interval`, `doses`, `time_list` and `subject` and the observation context (tissue, method and the not-reported flags) to interventions, and the `pkdb_id`, `release_date`, `issue`, `review_status` and `review` columns to studies, and it extends the study text search to the PKDB identifier. It moves every stored `value` into an empty `mean` (a different `mean` that already exists is kept and the conflict is logged), converts the schedule text of interventions with the grammar of the study format 1 importer, and drops `value` and the schedule text. It stops and lists the intervention ids of schedules it cannot convert instead of dropping them. The downgrade restores `value` and the schedule text where they are derivable.

Processing version 9 changes how studies are prepared (statistics in `mean`, structured schedules, derived geometric and error-bar statistics, the study identifier). Servers with processing version 9 refuse `pkdb` clients of other versions, so install the matching `pkdb` release, and upload every study again after the migration so that all stored studies follow the same rules. Uploads are idempotent and replace each study in place; the study format 2 studies are renamed to `<substance>/<name>` when they are uploaded as described above.

## Verification and performance

Regression checks cover canonical study round-trips, atomic replacement/rollback, group inheritance, API searches, analysis pagination, scatter pairing, source provenance, fresh schema creation and downgrade/recreation, and malformed/cross-study array references. Corpus benchmarking uses isolated schemas and hashes source files before and after uploads.

Measured corpus results are recorded in the [implementation plan](superpowers/plans/2026-09-24-unified-observation-model.md). Timings are local observations, not a guarantee of production latency; the shared context/value join trades additional joins for less duplicated metadata and fewer association rows.
