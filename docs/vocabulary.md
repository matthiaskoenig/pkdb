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

Omit `name` when it is identical to the supplied `sid`, and omit empty `annotations` lists. Use compact identifiers when the collection and identifier prefix match, for example `CHEBI:27732` instead of `chebi/CHEBI:27732`. Keep collection-qualified identifiers when their prefixes differ or the accession has no CURIE prefix. For CHMO, use direct BioRegistry URLs such as `https://bioregistry.io/CHMO:0000001`; CHMO is not present in the committed identifiers.org registry.

Write descriptions as complete sentences describing the quantity or category. Include relevant distinctions and references to related terms. Keep spaces between adjacent Python string literals. Generation collapses whitespace and adds missing terminal punctuation; it does not rewrite scientific meaning. Preserve chemical names, formulas, stable SIDs, and curation names even when correcting display text.

Annotations use `pymetadata.core.annotation.RDFAnnotation` and `RDFAnnotationData`. Existing `(BQB.IS, "chebi/CHEBI:27732")` tuples remain supported. PK-DB keeps only its output-field mapping; parsing, validation, provider URLs, and ontology enrichment come from pymetadata. Identical annotations resolve once per process. Unknown registry namespaces remain in the output and are flagged rather than silently discarded.

## Regenerate the JSON files

Install uv and Python 3.14, then run from the repository root:

```bash
uv run --project backend --python 3.14 python scripts/update_vocabulary.py
```

This command installs the development dependencies, refreshes missing or expired public metadata, and updates `backend/bootstrap/vocabulary.json` and `backend/bootstrap/provenance.json`. It does not change `users.json`, study folders, or the database.

All authoring code and metadata now live in `backend/info_nodes`, including `convert.py` and the `cache/` directory. Ontology, ChEBI, and UniChem records expire after 60 days. The identifiers.org registry and UniChem source list expire after 24 hours. Retrieval timestamps are persisted in `cache/manifest.json`; filesystem modification times are not used. Online refresh never silently falls back to expired data.

Use `--refresh-cache` to discard the old cache contents and fetch active vocabulary metadata from scratch into staging. Use `--offline` to generate from the committed cache without network access. `--check` is always offline, allowing CI to verify the exact committed snapshot regardless of metadata age. A new cache is installed only after the vocabulary validates. Missing optional metadata is recorded in provenance; failures in required metadata stop generation. Supply `mass`, `formula`, and `charge` explicitly for substances that cannot be enriched remotely.

The vocabulary dependency uses `pymetadata==0.6.5`, which includes [upstream fix #87](https://github.com/matthiaskoenig/pymetadata/pull/87). This resolves BioRegistry annotations independently of the identifiers.org registry and handles underscore-prefixed SIO/OBI identifiers correctly. FMA queries use its current `http://purl.org/sig/ont/fma/fma` IRI prefix; the old OBO URLs no longer resolve. Refreshes can change labels, synonyms, chemical properties, and cross-references. Verify the resulting metadata and commit cache records and their manifest together with regenerated output.

Invalid units, duplicate SIDs, missing parents, cycles, or invalid scientific properties fail generation before either JSON file is replaced. Review the source and generated diff together, then commit both.

Generation also prints a metadata review count and records sorted `metadata_issues` in `provenance.json`, with a node SID, diagnostic code, and explanation. These warnings include invalid or unresolved annotations, duplicate annotations, ambiguous chemical identities, unknown measurement policy names, and explicit curation questions. Expected lack of OLS support for non-ontology databases is not a warning. Missing optional remote metadata remains listed separately under `uncached_optional_metadata`.

Maintain unresolved curation questions in `info_nodes/audit.py`. Review the current diagnostics in generated provenance before making scientific corrections, then update or remove the corresponding review entries. Auditing reports inconsistencies without changing scientific rules or merging identifiers.

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

The rebuilt image contains the new JSON. Startup applies it to PostgreSQL using `pkdb-server bootstrap /app/bootstrap`. Existing accounts and studies are preserved. Repeat [validation and upload](local-upload-testing.md) to use the new allowed terms.

Bootstrap inserts and updates definitions; it retains database nodes omitted from a later snapshot. Removing a definition from the source is therefore not a database deletion mechanism. Coordinate term retirement and affected studies explicitly.
