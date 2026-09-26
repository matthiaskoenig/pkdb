# Public PK/PD dataset imports

These first-version importers create private, closed-licence studies through the same model as manual curation and OSP imports. A study is identified by **reference + acquisition source**. An imported record is not a manually reviewed record, and matching measurements from different sources are not silently deduplicated.

## Sources and coverage

| Importer | Pinned distribution | Native records | Preserved source context |
|---|---|---|---|
| `frdb` | [NCATS FRDB](https://drugs.ncats.io/downloads-public), 2024-12-30 | Human Cmax, half-life, explicitly identified AUC-to-infinity and AUC-to-time | Every PK row, original citation, source type, dose, population, fraction unbound, uncertainty and other unmapped fields |
| `cvtdb` | [invivoPKfit](https://cran.r-project.org/web/packages/invivoPKfit/index.html) 2.0.2, CvTdb snapshot 2025-08-12 | Original numeric concentration/time observations, across species | All 35,669 original rows, chemical identifiers, experiment/series/subject/document IDs, dose, LOQ, SD, extraction status and curation tags |
| `warfarin` | [nlmixr2data](https://nlmixr2.github.io/nlmixr2data/reference/warfarin.html) 2.0.10, commit `f2cfb01ade88d4d30e66f56b19efce2a2c6e26bd` | 32 individuals, 32 doses, 251 PK and 232 prothrombin-complex-activity observations | All 515 source rows and both historical citations |

FRDB contains experiments, reviews, labels, government documents and patents. Its acquisition-level evidence kind is therefore `unknown`; each row retains its original `pk_source_type`. CvTdb and warfarin are classified as observed upstream data. This is separate from the automatic **import** mechanism and from PK-DB's reported/normalized/calculated representations.

CvTdb is decoded from `cvtdb_original.rda`, not the preprocessed `cvt` table or fitted models. No upstream R code is executed. Documentation row counts can differ from the actual pinned artifacts; import reports count the decoded rows.

## Run and review

Install the optional pure-Python R reader for CvTdb and warfarin:

```bash
pip install 'pkdb[imports]'
pkdb import frdb --creator dataset-import --output /path/to/new-frdb
pkdb import cvtdb --creator dataset-import --output /path/to/new-cvtdb
pkdb import warfarin --creator dataset-import --output /path/to/new-warfarin
# Any importer also accepts: --offline --source /path/to/pinned-artifact
```

The output directory must be new or empty. Use a dedicated data directory outside the documentation build cache (`.cache/`). Downloads and local artifacts must match the pinned SHA-256, including offline runs. Pins live in `python/src/pkdb/importers/datasets/releases.py`.

Each run writes:

- `studies/<stable-source-sid>/study.json` and `reference.json`.
- **`source-records.json` in every study**: original rows, original row IDs, archive member, artifact URL/checksum/version, native-record JSON pointers, input field names, mapping operations and exclusion reasons. Row numbers are one-based data rows, excluding a tabular header. This file becomes a normal study attachment when uploaded.
- `vocabulary.json`: a portable validation vocabulary, including source-qualified analytes and the explicit `unspecified summary` calculation type. Review and reconcile these additions with the server vocabulary; do not replace an established vocabulary wholesale.
- `import-report.json`: study/row/measurement totals and warning counts. Warnings may overlap and are not a count of excluded rows.
- `artifacts/`: the exact verified upstream distribution, including its metadata and notices. Keep this directory with the run; it is not automatically uploaded with individual studies.

The attribution account must exist on the target server. With a processing-version-8 client/server, reviewed vocabulary additions, and `PKDB_API_TOKEN` configured:

```bash
pkdb-server validate /path/to/new-frdb/studies --api-url "$PKDB_API_URL"
pkdb-server upload /path/to/new-frdb/studies --api-url "$PKDB_API_URL"
```

The same commands apply to the other output directories. Normal ingestion validates each study and replaces it atomically. An import conversion creates reviewable folders; it does not publish to a server. Re-imports use stable reference-derived SIDs within a source, so they do not overwrite manual studies. If newly supplied publication aliases change a study's identity, reconcile it before uploading; automatic cross-source merging is not performed.

## Scientific provenance and limits

**Unknown summary statistics stay unknown.** FRDB and CvTdb do not consistently identify a mean, median or individual measurement. Their numeric group outputs use `value` with the explicit `calculation_type="unspecified summary"`, even when N=1. Processing version 8 allows this combination, prohibits attaching mean/SD claims to it, and disables automatic PK derivation for it. Counts that are absent, ranged or qualified remain null. Source SD is preserved without guessing its relationship to a central statistic.

**No censoring or dose-time invention.** ND, NQ, NA, bounds, ranges and incompatible units remain in the original rows with exclusion reasons. They are never replaced by zero or an imputed LOQ. Original CvTdb values and units are used instead of upstream normalized values. Unit spelling changes preserve numerical magnitude; normal PK-DB preparation records subsequent normalization separately. FRDB AUC with unknown integration interval is retained only in the attachment. Untimed or ambiguous dosing context stays in the attachment rather than becoming a dose at time zero.

FRDB molecular weights are used only when positive source values agree for an analyte. Conflicting weights remain in the source rows, generate warnings, and leave native molecular weight unset. No mass-to-molar conversion is inferred from a disputed weight. Source attachments also record the Python, PK-DB and, where applicable, R-reader/pandas versions used for decoding.

**No invented series membership.** This version stores native scalar observations with times where available. It does not infer longitudinal subjects or generate timecourses from matching metadata. FRDB groups are row-specific; CvTdb groups use experiment, source subject-context ID and reported count. Original series IDs remain in the attachment. Warfarin observations at duplicate subject/time/endpoint coordinates remain separate; dose-row `dv=0` placeholders are excluded, while zero measurement observations are retained. Warfarin route/form are unreported in the artifact and remain `NR`; endpoint and unit meanings follow the upstream dataset documentation. PCA is percent prothrombin complex activity, not INR.

**References retain their scope.** FRDB source URIs and CvTdb PMID/DOI aliases identify source documents, which may be secondary sources. CvTdb aliases are consolidated before folder creation and conflicting aliases stop conversion. Warfarin has one compilation reference with `publication_attribution="unresolved"`. Its documentation cites [1963](https://doi.org/10.1172/JCI104839) and [1968](https://doi.org/10.1161/01.cir.38.1.169) publications, but supplies no row-to-paper attribution. Both citations are retained as supporting references; neither is falsely assigned to all 32 subjects. Upstream preparation history is not fully documented. Citation enrichment is not performed during this reproducible import.

**Access is not a licence.** The FRDB distribution did not provide an explicit dataset-specific reuse licence. invivoPKfit declares GPL-3 and nlmixr2data GPL ≥3 for their packages; these declarations do not establish unrestricted rights to every underlying publication. `source_terms` records this distinction. Generated studies stay private and closed until their reuse terms and scientific mapping have been reviewed.

## Weekly checks

The **Public dataset release checks** workflow runs every Monday at **07:43 UTC**, once present on the default branch, and supports manual dispatch. It checks FRDB archive links, the CRAN package version, and the actual warfarin artifact checksum on the upstream main branch because that repository has no tagged releases.

```bash
python3 scripts/check_dataset_releases.py
```

Exit `0` means current, `2` means a changed source needs review, and `1` means availability is unknown because a check failed. All providers are checked even if one fails. The workflow reports findings without importing or publishing data. Review new artifacts, update pins and mappings, validate, and then re-import explicitly. The existing OSP weekly check remains separate.
