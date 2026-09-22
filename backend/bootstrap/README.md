# Offline vocabulary snapshot

`vocabulary.json` contains 2,147 nodes exported from the existing local
`backend/pkdb_data` definitions and metadata cache. Stable SIDs, hierarchy edges,
choices, units, molecular masses, synonyms, annotations and cross-references are
retained. One repeated parent edge is collapsed, matching the legacy many-to-many
relation. Source study files and the untracked source package are not modified.

`provenance.json` records input hashes and 11 uncached optional ontology requests.
Those enrichments were unavailable; definitions and available cached metadata
remain in the snapshot. This is not a claim that all external metadata is current.

Compose loads this snapshot automatically with `pkdb bootstrap /app/bootstrap`.
The committed `users.json` is empty. To prepare accounts referenced by a study,
run `pkdb bootstrap-study PATH` against the local database. New accounts have login
disabled; existing roles, passwords, and activation remain unchanged.

The original exporter depended on the retired backend and has been removed. The
snapshot and provenance remain the reproducible input to current bootstrap runs.
