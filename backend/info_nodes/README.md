# Vocabulary authoring

Edit `definitions/*.py` to maintain the allowed PK-DB terms. Units live in `units.py`, scientific measurement policies in `policies.py`, and unresolved curation questions in `audit.py`.

From the repository root, run:

```bash
uv run --project backend --python 3.14 python scripts/update_vocabulary.py
```

The command compiles definitions and offline caches into `backend/bootstrap/vocabulary.json` and `provenance.json`. Review metadata diagnostics in the provenance alongside the generated diff. Do not edit generated JSON manually.

See the [vocabulary guide](../../docs/vocabulary.md) for annotation formats, description conventions, validation, and loading the vocabulary.
