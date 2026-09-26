# OSP observed-data import (#720)

## Design and scope

Import release v1.9 (2026-02-24), commit b171d65ad97ad9eb5e60cdc1a48d550b3c3f9947. Workbook SHA-256: e77e3c99c059f97ea45785508f7b0cbb52382306b8257737c9cd1ac83d83e86b. The release contains 3,079 assessment records, 31,097 profile rows, 1,651 PK-parameter rows, and 635 DDI records. Assessment IDs connect sheets; they are not publications or unique participants.

Use one scientific model and discriminated provenance records: ManualCuration, DataImport, AutomaticCuration. Provenance kind does not replace observation origin (reported/normalized/calculated). Source keys identify a stable provider or curation workflow; release, importer version, commit, asset checksum, upstream dataset IDs, and mapping warnings remain versioned evidence.

Study identity is (publication, source). Publication identifiers have aliases (PMID and DOI), and stable publication identity survives enrichment. Keep source-specific citation snapshots and study access controls: updating OSP must never change a manually curated citation or study. Duplicate source/publication submissions under another SID fail; different sources coexist. Existing manual records receive manual provenance. Do not silently merge conflicting identifiers or duplicate existing studies during migration.

Group all assessments for a publication into one OSP study. Keep assessment groups/individuals separate unless the source explicitly identifies equivalence. Preserve original workbook rows in each generated study's source attachment, with sheet/row/ID coordinates. Normalize only explicit, unambiguous data: no invented sample counts, healthy status, dosing events, statistical meanings, or publication identifiers. Unknown group size becomes nullable. Unsupported/ambiguous values remain in source records and are itemized in an import report rather than silently discarded or guessed. Geometric variability and confidence intervals must not be treated as arithmetic SD or observed ranges.

Generate reproducible study folders accepted by the normal validation/upload pipeline. Preserve upstream reference links and source row metadata. Produce an auditable vocabulary extension for source analytes absent from the bundled vocabulary; use source molecular weights only where explicitly supplied, and do not collapse mixtures/metabolites/stereoisomers into a parent substance.

Default import target: isolated local PostgreSQL schema, pending a different explicit user target. Source files are not changed. Imported access/licence defaults remain private/closed; source availability alone is not a redistribution licence.

## Implementation

1. Inspect pinned source and specification; record identity/mapping decisions and inventory.
2. Add typed provenance, publication identity/aliases, unique source/publication studies, nullable group counts, and additive migration.
3. Build OSP workbook adapter, CLI, pinned download/checksum verification, source row archive, mapping report, and portable vocabulary snapshot.
4. Test representative scientific and identity cases, round trips, legacy compatibility, and repeat import behavior.
5. Convert every assessment and account for every profile, parameter, and DDI row; load generated studies through the normal ingestion service into the isolated database.
6. Verify persisted counts and source/manual coexistence; document generated artifacts, retained limitations, and how to rerun against an explicitly chosen server.

Reverse export to OSP is part of the historical issue text but outside this requested import implementation.

## Outcome

Implemented all six steps. See [operator guide](../../osp-import.md) for mapping decisions, reproducible conversion/upload commands, and completed import counts. The isolated database contains 741 source-qualified studies and 33,103 reported outputs; every source data row is accounted for. The UI displays acquisition kind, source, and release. Publication registration uses locks scoped to aliases and the affected publication, preserving concurrent unrelated imports.
