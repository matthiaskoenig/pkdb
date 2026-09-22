# Offline vocabulary snapshot

`vocabulary.json` contains 2,147 nodes exported from the existing local
`backend/pkdb_data` definitions and metadata cache. Stable SIDs, hierarchy edges,
choices, units, molecular masses, synonyms, annotations and cross-references are
retained. One repeated parent edge is collapsed, matching the legacy many-to-many
relation. Source study files and the untracked source package are not modified.

`provenance.json` records input hashes and 11 uncached optional ontology requests.
Those enrichments were unavailable; definitions and available cached metadata
remain in the snapshot. This is not a claim that all external metadata is current.

Reproduce from the repository root with a disposable environment:

```bash
uv venv --python 3.13 /tmp/pkdb-vocabulary-export
uv pip install --python /tmp/pkdb-vocabulary-export/bin/python \
  pymetadata==0.6.4 python-slugify==9.1.0 pandas==2.3.3 pint==0.26.1
/tmp/pkdb-vocabulary-export/bin/python -m tools.backend_migration.export_vocabulary \
  --source-backend /path/to/legacy/backend \
  --registry /path/to/cached/identifiers_registry.json \
  --output /tmp/pkdb-bootstrap-export
```

The exporter copies caches to a temporary directory and blocks network connections.
It requires the legacy source package, its cache, and a cached identifier registry.
These export dependencies are not part of the new application's runtime.

Bootstrap also requires an explicit `users.json` alongside `vocabulary.json`:

```json
[{"username": "curator", "role": "curator", "email": "curator@example.org"}]
```

New identities have login disabled. Corpus bootstrap neither creates credentials
nor changes existing roles/passwords. Supply deployment identities explicitly;
no real user list or credentials are committed here.
