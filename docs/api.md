# REST API

Use `https://alpha.pk-db.com` as the base URL for data access and curation. The [Python client](python-client.md) wraps common operations; you can also make HTTP requests directly. The [research API reference](https://alpha.pk-db.com/docs) focuses on data and curation; the [complete reference](https://alpha.pk-db.com/docs/all) also covers accounts and administration. See [executable examples](api-examples.md) and the separate [read-only MCP interface](mcp.md).

## Browse studies and measurements

Public browsing does not require an API key:

```bash
curl --fail --get 'https://alpha.pk-db.com/api/v2/studies' \
  --data-urlencode 'substance=apixaban' --data-urlencode 'page_size=20'

curl --fail --get 'https://alpha.pk-db.com/api/v2/measurements' \
  --data-urlencode 'study_sid=STUDY_SID' \
  --data-urlencode 'page=1' --data-urlencode 'page_size=20'
```

Replace `STUDY_SID` with a study identifier returned by the study list. Lists and advanced queries return `items`, `total`, `page`, `page_size`, `next`, and `previous`. The last two contain page numbers or null. Pass `next` as `page` until it is null. Study substance filters use vocabulary names; measurement substance/type filters use vocabulary identifiers.

| Endpoint | Use |
| --- | --- |
| `GET /api/v2/studies` | Find studies |
| `GET /api/v2/statistics` | Current database coverage and annual study, substance, and PK metrics |
| `GET /api/v2/measurements` | Select measurement rows |
| `GET /api/v2/studies/{sid}` | Complete canonical study |
| `POST /api/v2/query` | Advanced typed queries, including groups, individuals, interventions, and references |
| `POST /api/v2/exports` | Download a selected dataset |
| `GET /api/v2/vocabulary` | Vocabulary snapshot |
| `GET /api/v2/capabilities` | Processing and report versions |
| `POST /api/v2/studies/validate` | Validate source bundles |
| `PUT /api/v2/studies/{sid}` | Create or replace a study |

A study substance search matches studies containing relevant data; it does not mean every measurement in each study concerns that substance. Combine substance and measurement-type filters on `/api/v2/measurements` to match both on the same observation. Study-level selections can include broader context than a measurement-level match. See [search scopes](web-interface.md#choose-the-scope-of-your-search) and the API reference before combining filters.

## Database statistics

`GET /api/v2/statistics` returns one consistent, permission-filtered overview. Anonymous requests include public studies; authenticated requests additionally include studies the caller can access.

```bash
curl --fail 'https://alpha.pk-db.com/api/v2/statistics'
```

- `counts`: current totals, including `substance_count` (distinct substances with timecourses), `pk_count`, and `pk_calculated_count`.
- `years`: ascending calendar years from the first to the last dated study, with empty years included. Each row has `study_count`, `timecourse_count`, `substance_count`, `pk_count`, `pk_calculated_count`, `cumulative_study_count`, and `cumulative_substance_count`. Cumulative substances are distinct across years, not a sum of yearly counts.
- `undated`: the same annual metrics for studies without a date. These contribute to current totals but not cumulative dated counts; its cumulative fields are zero.
- `substances`: vocabulary `sid`, `name`, and distinct `timecourse_count`, ordered by descending coverage. A course containing several observations for the same substance counts once.
- `parameters`: sparse counts by vocabulary `sid`, `name`, and `year` (null for undated studies), split into `reported` and `calculated` values. Absent combinations have zero counts.
- `date_basis`: `study.date`; `generated_at`: UTC response generation time.

Years use the **study date**, not the reference publication date or upload timestamp. These are the dates of currently accessible studies, not historical database snapshots. PK parameter types follow descendants of `pharmacokinetic-measurement` in the vocabulary. Measurement metrics use normalized records, avoiding duplicate reported/normalized representations; calculated PK values are included in PK totals. Substance coverage requires a normalized observation in a timecourse. The existing `/api/v1/statistics/` count response remains compatible.

## Authenticate requests

Create a personal key in [Account settings](https://alpha.pk-db.com/account), then provide it through `PKDB_API_KEY` in your environment. Send it as a Bearer credential:

```bash
curl --fail --header "Authorization: Bearer ${PKDB_API_KEY}" \
  'https://alpha.pk-db.com/api/v2/studies'
```

Authentication adds access only to studies your account is allowed to read. For key scopes, expiry, and rotation, see [Accounts and API keys](authentication.md).

## Download a dataset

Downloads require authentication, including downloads of public data:

```bash
curl --fail 'https://alpha.pk-db.com/api/v2/exports' \
  --header "Authorization: Bearer ${PKDB_API_KEY}" \
  --header 'Content-Type: application/json' \
  --data '{"queries":{"studies":{"entity":"studies","predicates":[{"field":"sid","value":"STUDY_SID"}]}},"concise":true}' \
  --output dataset.zip
```

Export selection uses the `FilterSpec` schema, retaining `outputs` as its measurement entity key. Unlike list queries, exports are not restricted to one page. The response is a ZIP archive restricted to data your account can access. Preserve the study identifiers, selection criteria, and retrieval date with your analysis. Follow the licences attached to the studies.

## Curate data

Use the [Python client preparation and upload workflow](python-client.md#prepare-validate-and-upload-a-study-folder) to send study folders to `https://alpha.pk-db.com`. It prepares and validates the source bundle and checks vocabulary compatibility before upload. A curator account and a key with `studies:write` are required; existing studies can be replaced only when your account has permission.

## Handle errors

Inspect the HTTP status and response body. Validation failures include structured issues where available. `401` indicates an authentication problem; `403` indicates insufficient access; `409` can indicate incompatible vocabulary or processing versions. Authenticated callers are not rate limited. Anonymous callers receiving `429` should respect `Retry-After`. Do not automatically retry an upload with an uncertain outcome: inspect the study first.


## Advanced queries and compatibility

`POST /api/v2/query` accepts an entity and typed predicates. For example, `{"entity":"groups","predicates":[{"field":"study_sid","operator":"eq","value":"PKDB01110"}],"page":1,"page_size":100}` selects groups in one study. Predicates combine with AND. The public `measurements` entity accepts the historical `outputs` alias. Consult the reference schemas for supported fields and operators.

The frontend retains compatibility reads under `/api/v1/`. New integrations should use v2. Legacy account/admin aliases and JSON-suffix read routes are disabled by default; `PKDB_LEGACY_API_ENABLED=true` enables those remaining compatibility routes. Legacy study/reference drafts, file-handle staging (including `/api/v2/files`), and `/api/v1/update_index/` have been retired permanently. Upload a complete bundle through `PUT /api/v2/studies/{sid}` instead.

MCP exposes read operations only. Use REST or the Python client for validation, upload, and replacement.

## Detailed upload diagnostics

The capabilities response advertises supported `upload_report_versions`. Send `X-PKDB-Report-Version: 2` with `POST /api/v2/studies/validate` or `PUT /api/v2/studies/{sid}` to receive a versioned report envelope. Requests without the header retain the legacy response shape. The current Python client negotiates this automatically.

The envelope contains `report_version`, `request_id`, `operation`, `status`, `stage`, `study`, `persistence`, `summary`, `report`, `result`, and `versions`. The successful replacement payload remains available under `result`; HTTP status codes keep their normal meanings. `X-Request-ID` is also returned as a response header for upload and validation requests.

Each report issue includes a stable `code`, severity, message, and available source location. Detailed diagnostics add `category`, `stage`, `field`, `actual`, `expected`, `context`, related sources, and correction suggestions where known. Spreadsheet coordinates refer to physical Excel rows and cells, including skipped comments or blank rows. JSON locations use key/index paths. An absent `actual` means the value is unavailable; an explicit null is an actual null value.

Reports include error/warning counts, returned/omitted issue counts, `truncated`, `complete`, and `stopped_reason`. Counts cover discovered issues; when validation is incomplete they are lower bounds. No caller should assume an incomplete report lists every defect. Source issues are bounded to protect response size, and untrusted diagnostic values are sanitized.

`persistence` distinguishes validation without writing (`not_attempted`), rejected writes (`not_saved`), confirmed creation/replacement (`created`/`replaced`), and uncertain outcomes (`unknown`). A transport failure can prevent the client from knowing whether a save committed. Preserve the request ID, inspect the study, and avoid automatic write retries. Internal errors provide a safe summary and correlation ID rather than a server traceback.
