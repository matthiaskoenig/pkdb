# Vocabulary definitions, metadata, and conversion

This package contains the authoritative vocabulary definitions, public metadata cache, and bootstrap snapshot converter. It is development input, separate from the application runtime. Edit `definitions/*.py` to maintain allowed terms. Units live in `units.py`, measurement policies in `policies.py`, unresolved curation questions in `audit.py`, and snapshot conversion in `convert.py`.

From the repository root, run:

```bash
uv run --project backend --python 3.14 python scripts/update_vocabulary.py
```

The command refreshes missing or expired metadata and compiles `backend/bootstrap/vocabulary.json` and `provenance.json`. Cache records live directly in `cache/`: ontology, ChEBI, and UniChem records expire after 60 days; `identifiers_registry.json` and `unichem_sources.json` expire after 24 hours. `cache/manifest.json` records retrieval times so Git checkout timestamps cannot extend cache lifetimes. Failed refreshes do not silently reuse expired records.

Use `--refresh-cache` to fetch active vocabulary metadata into an empty staging cache, `--offline` to generate from committed metadata without network access, and `--check` to verify generated files offline without modifying the cache. A refreshed cache is published only after vocabulary validation succeeds. Lookup failures are recorded in provenance; failures that prevent a valid vocabulary leave the existing cache and generated outputs untouched.

The original definitions were recovered from revision `632a8bb2`; the old metadata cache has since been replaced by a complete fresh retrieval. Review source and generated diffs together, including changed chemical properties and cross-references. Generated JSON is not an alternative authoring source and must not be edited manually.

See the [vocabulary guide](../../docs/vocabulary.md) for annotation formats, description conventions, validation, and loading the vocabulary.
