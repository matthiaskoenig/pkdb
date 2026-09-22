# Update allowed terms

`backend/info_nodes/definitions/` is the authoritative vocabulary source. Edit these Python definitions to add allowed measurements, categorical choices, substances, tissues, methods, administration routes, forms, and calculation types. The backend reads generated JSON; do not edit `backend/bootstrap/vocabulary.json` or `provenance.json` manually.

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

Write descriptions as complete sentences describing the quantity or category. Include relevant distinctions and references to related terms. Keep spaces between adjacent Python string literals. Generation collapses whitespace and adds missing terminal punctuation; it does not rewrite scientific meaning. Preserve chemical names, formulas, stable SIDs, and curation names even when correcting display text.

Annotations use `pymetadata.core.annotation.RDFAnnotation` and `RDFAnnotationData`. Existing `(BQB.IS, "chebi/CHEBI:27732")` tuples remain supported. PK-DB keeps only its output-field mapping; parsing, validation, provider URLs, and ontology enrichment come from pymetadata. Identical annotations resolve once per process. Unknown registry namespaces remain in the output and are flagged rather than silently discarded.

## Regenerate the JSON files

Install uv and Python 3.14, then run from the repository root:

```bash
uv run --project backend --python 3.14 python scripts/update_vocabulary.py
```

This single command installs the development dependencies and updates `backend/bootstrap/vocabulary.json` and `backend/bootstrap/provenance.json`. It does not change `users.json`, study folders, the database, or source caches.

Generation uses the committed ontology, ChEBI, UniChem, and identifiers.org caches without network requests. Existing cached annotation details, synonyms, molecular properties, and cross-references are preserved. For a new substance without cached chemical metadata, supply `mass`, `formula`, and `charge` explicitly in its `Substance(...)` definition. Optional uncached enrichment requests are recorded in provenance; the script does not silently fetch or invent metadata.

The vocabulary dependency uses `pymetadata==0.6.5`, which includes [upstream fix #87](https://github.com/matthiaskoenig/pymetadata/pull/87). This resolves BioRegistry annotations independently of the identifiers.org registry and handles underscore-prefixed SIO/OBI identifiers correctly. Missing FoodOn, OBI, PR, SCDO, and SIO records were retrieved from the EBI OLS4 term API, checked against their requested IRIs, and added to the source cache. The macroalbuminuria annotation uses `SCDO:1000201` (High Level Albuminuria), whose definition matches the authored description; the previous `SCDO:10002014` did not resolve. Refresh ontology metadata explicitly outside the compiler, verify each response's identity, and commit the cache records together with regenerated output.

Invalid units, duplicate SIDs, missing parents, cycles, or invalid scientific properties fail generation before either JSON file is replaced. Review the source and generated diff together, then commit both.

Generation also prints a metadata review count and records sorted `metadata_issues` in `provenance.json`, with a node SID, diagnostic code, and explanation. These warnings include invalid or unresolved annotations, duplicate annotations, ambiguous chemical identities, unknown measurement policy names, and explicit curation questions. Expected lack of OLS support for non-ontology databases is not a warning. Missing optional remote metadata remains listed separately under `uncached_optional_metadata`.

Current curation questions include the mixed-race annotation, angiotensinogen description, intrinsic-clearance definition, AUC-ratio units, stereoisomer annotations, and overlapping substance concepts. Two negative-value policy names do not match measurements, including a concatenated pair of systolic-pressure names. These are flagged without changing existing scientific rules or merging identifiers. Review the diagnostic in the generated provenance before making a scientific correction, then update or remove its entry in `info_nodes/audit.py`.

The compiler validates and indexes the completed graph once. Serialization uses indexed children and cached, unique descendant choices, preserving definition order. Rebuild `NodeIndex` after editing node relationships. Ordinary lists still support fresh child lookup. `collect_nodes()` copies authored definitions before enrichment, so repeated collection does not accumulate metadata.

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
