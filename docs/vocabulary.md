# Update allowed terms

`backend/pkdb_data/info_nodes/definitions/` is the authoritative vocabulary source. Edit these Python definitions to add allowed measurements, categorical choices, substances, tissues, methods, administration routes, forms, and calculation types. The backend reads generated JSON; do not edit `backend/bootstrap/vocabulary.json` or `provenance.json` manually.

## Edit a definition

Choose the relevant module, such as `anthropometry.py`, `measurement.py`, `substance.py`, or `method.py`. Preserve existing stable SIDs. Add the definition to the module's existing list. For example, inside `ANTHROPOMETRY_NODES`:

```python
MeasurementType(
    sid="response-category",
    description="Response category recorded by the study.",
    parents=["physiological measurement"],
    dtype=DType.CATEGORICAL,
),
Choice(
    sid="response-category-responder",
    name="responder",
    description="The subject responded to treatment.",
    parents=["response-category"],
),
```

Parents may use existing names or SIDs; generation normalizes them into SIDs. Boolean and categorical measurements receive the existing automatic Y/N and NR choices as appropriate. Units are defined in `info_nodes/units.py`. Measurement rules requiring time or allowing negative values live in `info_nodes/policies.py`.

## Regenerate the JSON files

Install uv and Python 3.14, then run from the repository root:

```bash
uv run --project backend --python 3.14 python scripts/update_vocabulary.py
```

This single command installs the development dependencies and updates `backend/bootstrap/vocabulary.json` and `backend/bootstrap/provenance.json`. It does not change `users.json`, study folders, the database, or source caches.

Generation uses the committed ontology, ChEBI, UniChem, and identifiers.org caches without network requests. Existing cached annotation details, synonyms, molecular properties, and cross-references are preserved. For a new substance without cached chemical metadata, supply `mass`, `formula`, and `charge` explicitly in its `Substance(...)` definition. Optional uncached enrichment requests are recorded in provenance; the script does not silently fetch or invent metadata.

Invalid units, duplicate SIDs, missing parents, cycles, or invalid scientific properties fail generation before either JSON file is replaced. Review the source and generated diff together, then commit both.

To check that generated files match the sources without writing them:

```bash
uv run --project backend --python 3.14 python scripts/update_vocabulary.py --check
```

CI runs this check. Output is deterministic, including the vocabulary version and input hashes. `--output /path/to/directory` can generate files for inspection elsewhere.

## Load the updated vocabulary locally

```bash
docker compose up --build --wait
```

The rebuilt image contains the new JSON. Startup applies it to PostgreSQL using `pkdb bootstrap /app/bootstrap`. Existing accounts and studies are preserved. Repeat [validation and upload](local-upload-testing.md) to use the new allowed terms.

Bootstrap inserts and updates definitions; it retains database nodes omitted from a later snapshot. Removing a definition from the source is therefore not a database deletion mechanism. Coordinate term retirement and affected studies explicitly.
