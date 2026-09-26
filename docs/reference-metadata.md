# Literature reference metadata

A study's `reference.json` is a saved bibliographic snapshot. Create or enrich it from a PubMed ID, DOI, or manual citation using the Python client or the local curation interface. Retrieval uses HTTP APIs directly; no Biopython or provider SDK is required.

## Resolve a PubMed ID or DOI

The study directory must contain `study.json`, including its stable `reference` identifier. The resolver preserves that identifier and the reference name. It can create a missing `reference.json`.

```bash
# Review metadata and changed fields. This does not modify the study.
pkdb reference resolve /path/to/Study --pmid 6138080
pkdb reference resolve /path/to/Study --doi 10.1111/j.1365-2125.1983.tb02270.x

# Save the snapshot explicitly after review. The previous lookup is cached.
pkdb reference resolve /path/to/Study --pmid 6138080 --write

# Reuse cached data without any network requests.
pkdb reference resolve /path/to/Study --offline

# Retrieve current provider metadata and review the differences.
pkdb reference resolve /path/to/Study --refresh
```

PMIDs, PubMed URLs, DOIs, and doi.org URLs are accepted. With both identifiers, conflicting provider identities fail. DOI lookups also search PubMed and accept a PMID only when its returned DOI matches exactly. Unavailable optional PubMed enrichment produces a visible warning while retaining the DOI metadata. A citation search never automatically chooses a publication.

To provide minimal JSON input, use `--input input.json` with either:

```json
{"pmid": "6138080"}
```

or:

```json
{"doi": "10.1111/j.1365-2125.1983.tb02270.x"}
```

## Manual references and candidate search

A manual reference requires a title and at least one author or organization. Its publication date is optional. Unpublished or unindexed literature remains usable without an identifier.

```bash
pkdb reference resolve /path/to/Study \
  --title "Internal pharmacokinetic study report" \
  --organization "Research team" --publication-date 2020 --offline --write

# Find up to five candidates; inspect the returned title, authors, year, and DOI.
pkdb reference search "Heizmann midazolam bioavailability 1983"
# Select a candidate by passing its DOI to reference resolve.
```

Use `--author` repeatedly for author display names, or provide structured names in `--input`:

```json
{
  "title": "Internal pharmacokinetic study report",
  "authors": [{"first_name": "Ada", "last_name": "Smith"}],
  "publication_date": "2020-03"
}
```

Unknown dates stay null. `publication_date` preserves year, month, or day precision. `date` is populated only when a full date is available; no first-of-month or first-of-year dates are invented. PubMed indexing completion dates are not publication dates. Structured abstracts retain every section and nested text.

## Local curation

Open a study's **Reference…** dialog. Enter a PMID or DOI, or expand **Manual citation and metadata corrections**. **Search citation** displays candidates that you can select. **Preview reference** shows the metadata and changed fields. **Save reference** writes only the reviewed snapshot; editing an input invalidates the preview.

The source files are checked again before saving. If another editor changed `study.json` or `reference.json`, preview again. Saving participates in the study's selected on-save validation/upload behavior. Offline mode restricts retrieval to cached responses and manual input.

## Corrections, storage, and refresh

The saved reference includes normalized bibliographic fields and `provenance`: original input, curator overrides, last resolved provider fields, provider identifiers, retrieval timestamps, and optional enrichment warnings. Personal authors retain ordered first/last names; corporate authors use `organization`. These fields survive upload, database storage, canonical export, and API reads.

Direct edits to the saved bibliographic fields are detected on the next resolution and preserved as overrides. Values supplied through CLI options or input JSON are also explicit overrides. Legacy references have no provider baseline, so their existing nonempty fields are preserved conservatively. Review those fields when adopting metadata retrieval, particularly old dates. Use `--reset-overrides` (or **Use provider metadata instead of saved corrections**) to preview provider values without retaining those legacy fields; add `--write` only after reviewing the result. Selecting a different identified publication clears overrides belonging to the previous publication while retaining the internal SID.

References remain owned by individual studies. This change does not merge reference records or change study access and replacement rules.

Provider responses are cached under the PK-DB cache directory's `references/` subdirectory. `--cache-dir`, `PKDB_CACHE_DIR`, and platform cache defaults control its location. Successful responses remain available until explicitly refreshed or removed; not-found responses expire after one hour. Temporary network failures do not replace successful cache entries. Requests use bounded retries, timeouts, and process-wide throttling; concurrent lookups share cached responses.

The cache is disposable. Saved references remain usable without it. Ordinary preparation, validation, upload, and server reads never fetch literature metadata or rewrite source files.

The backend migration `p003reference` adds publication-date precision, author organizations, and provenance without rewriting legacy references. Upgrade the backend alongside the client when uploading enriched references.

Provider documentation: [NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25497/), [DOI content negotiation](https://support.datacite.org/docs/what-is-the-best-way-to-make-a-content-negotiation-request-for-any-doi), and [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/).
