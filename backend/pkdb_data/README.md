# Vocabulary authoring sources

This package is the authoritative source of allowed PK-DB terms. It is development
input, separate from the application runtime. It contains no Django application or
study uploader.

Edit `info_nodes/definitions/*.py`, with units in `info_nodes/units.py` and scientific
policies in `info_nodes/policies.py`. From the repository root, run:

```bash
uv run --project backend --python 3.14 python scripts/update_vocabulary.py
```

See [the vocabulary guide](../../docs/vocabulary.md) for examples and loading the
result into the local Docker stack.

Definitions and ontology/chemical caches were recovered from commit `632a8bb2`.
The identifiers.org registry is the complete cached registry used for the original
snapshot. Generation copies caches into temporary storage and blocks network access.
These inputs preserve all 2,147 original nodes, including cached enrichment and the
previously recorded optional metadata gaps. The generated JSON is not an alternative
authoring source. Do not change scientific policy while performing mechanical updates.
