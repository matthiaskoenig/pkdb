# REST API

Use `https://beta.pk-db.com` as the base URL for data access and curation. The [Python client](python-client.md) wraps common operations; you can also make HTTP requests directly. The [research API reference](https://beta.pk-db.com/docs) focuses on data and curation; the [complete reference](https://beta.pk-db.com/docs/all) also covers accounts and administration. See [executable examples](api-examples.md) and the separate [read-only MCP interface](mcp.md).

The examples below read the base URL from `PKDB_ENDPOINT` and, where needed, your key from `PKDB_API_KEY`:

```bash
export PKDB_ENDPOINT=https://beta.pk-db.com
```

## Browse studies and measurements

Public browsing does not require an API key:

```bash
curl --fail --get "$PKDB_ENDPOINT/api/v2/studies" \
  --data-urlencode 'substance=apixaban' --data-urlencode 'page_size=20'

curl --fail --get "$PKDB_ENDPOINT/api/v2/measurements" \
  --data-urlencode 'study_sid=STUDY_SID' \
  --data-urlencode 'page=1' --data-urlencode 'page_size=20'
```

Replace `STUDY_SID` with a study identifier returned by the study list, such as `caffeine/Harder1988` (see [study identifiers](#study-identifiers-and-redirects)). Lists and advanced queries return `items`, `total`, `page`, `page_size`, `next`, and `previous`. The last two contain page numbers or null. Pass `next` as `page` until it is null. Study substance filters use vocabulary names; measurement substance/type filters use vocabulary identifiers.

| Endpoint | Use |
| --- | --- |
| `GET /api/v2/studies` | Find studies |
| `GET /api/v2/statistics` | Current database coverage and annual study, substance, and PK metrics |
| `GET /api/v2/measurements` | Select measurement rows |
| `GET /api/v2/studies/{substance}/{name}` | Complete canonical study of a study format 2 study |
| `GET /api/v2/studies/{sid}` | Complete canonical study of a study format 1 study; a PKDB identifier or a former identifier redirects |
| `POST /api/v2/query` | Advanced typed queries, including groups, individuals, interventions, and references |
| `POST /api/v2/exports` | Download a selected dataset |
| `GET /api/v2/vocabulary` | Vocabulary snapshot |
| `GET /api/v2/capabilities` | Processing and report versions |
| `POST /api/v2/studies/{substance}/{name}/validate` | Validate a study format 2 folder |
| `PUT /api/v2/studies/{substance}/{name}` | Create or replace a study format 2 study |
| `POST /api/v2/studies/validate` | Validate a study format 1 source bundle |
| `PUT /api/v2/studies/{sid}` | Create or replace a study format 1 study |

A study substance search matches studies containing relevant data; it does not mean every measurement in each study concerns that substance. Combine substance and measurement-type filters on `/api/v2/measurements` to match both on the same observation. Study-level selections can include broader context than a measurement-level match. See [search scopes](web-interface.md#choose-the-scope-of-your-search) and the API reference before combining filters.

## Study identifiers and redirects

A study in study format 2 is identified by `<substance>/<name>`, the location of its folder, for example `caffeine/Harder1988`. Names repeat across substances, so the identifier takes two path segments in every study route: `/api/v2/studies/caffeine/Harder1988` (and `/publication` below it), `/api/v1/studies/caffeine/Harder1988/`, `/api/v1/pkdata/studies/caffeine/Harder1988/`, and the administrator's `/api/v1/admin/studies/caffeine/Harder1988/access`. Study folders cannot be named `publication` or `validate`, because they would collide with route segments. A study in study format 1 keeps its single identifier, such as `PKDB01110`, and the single-segment routes until it is migrated.

A released study has a PKDB identifier such as `PKDB00198` that it keeps when it is renamed or moved to another substance. When a single-segment study route is given the PKDB identifier of a study that is stored as `<substance>/<name>`, or the former study format 1 identifier of a study that a study format 2 upload took over (such as `Vilsboll2008` for `liraglutide/Vilsboll2008`), and no study is stored under that identifier, the API answers `308 Permanent Redirect` with the same route for the study identifier in `Location`, keeping the suffix and the query string. Only callers who may read the study are redirected; everyone else gets the `404` of an unknown study. The administrator's access routes redirect the same way. An upload is never redirected.

```bash
curl --fail --location "$PKDB_ENDPOINT/api/v2/studies/PKDB00198"
# 308 to /api/v2/studies/caffeine/Harder1988
```

`curl --location` and the [Python client](python-client.md) follow the redirect; the client follows at most five redirects of reads within the origin of its endpoint and never follows the redirect of a write. A study can be renamed later, so do not store the redirect permanently: store the study identifier (`sid`) of the study you receive and its `pkdb_id`.

Study responses carry `pkdb_id`, `release_date`, `issue` (the number of the curation issue in the pkdb_data repository), `review_status` (`draft`, `in_review` or `approved`) and `open_review_items` (the number of unresolved review items). The first four are null and `open_review_items` is 0 for studies without release or review data. The complete canonical study has the same information in `metadata.release`, `metadata.issue` and `metadata.review`. Select studies by PKDB identifier with a `pkdb_id` predicate (`{"field":"pkdb_id","operator":"in","value":["PKDB00198"]}`) in `POST /api/v2/query`, with `pkdb_id__in` on `/api/v1/studies/` (identifiers separated by `__`), or with `studies__pkdb_id__in` in research filters; a study format 1 study counts under its own identifier. The study text search also finds PKDB identifiers.

## Statistics in responses

Measurement, characteristic and intervention rows (and the points of timecourses and scatter data) report `mean`, `median`, `min`, `max`, `sd`, `se`, `cv`, `gmean`, `gsd`, `gcv`, `count`, `error_bar`, `error_type` and `unit`. There is no `value`: the value of a single subject and the central value of an `unspecified summary` (a calculation type for summaries whose statistic the publication does not state) are stored in `mean`, and a `calculation_type` of `unspecified summary` marks the latter. `cv` and `gcv` are fractions in the API (`0.25` is 25 percent), whereas study format 2 tables enter them in percent. `gsd` is a dimensionless factor of at least 1. `error_bar` is the digitized end of an error bar on the value axis in `unit`, and `error_type` (`sd`, `se` or `gsd`) names the statistic it shows. `count` is the number of subjects a row describes: the count that the row states, else the count of its group (1 for an individual, null when the group size is unknown). Pharmacokinetic parameters derived from a timecourse state no count, and an intervention reports the count it states (for dose statistics) or null.

Reported statistics are never overwritten. For group records whose calculation type is empty or `sample mean` (not `unspecified summary`), the normalized representation (`normed` true, in standard units) completes the missing statistics from the reported ones: `sd`, `se` and `cv` from each other with `count` and the magnitude of `mean`, `gsd` and `gcv` from each other, and the statistic named by `error_type` from `error_bar` (`sd` or `se` as the distance of the error bar from `mean`, `gsd` as the factor between `error_bar` and `gmean`). Arithmetic statistics are never derived from geometric ones or the reverse. A unit conversion scales every value that is stated in `unit` (`mean`, `median`, `min`, `max`, `sd`, `se`, `gmean` and `error_bar`) and leaves the dimensionless `cv`, `gsd` and `gcv` and the `count` unchanged. Preparation reports the warning `inconsistent_statistics` when reported `sd`, `se`, `cv` and an `sd` or `se` error bar, or `gsd`, `gcv` and a `gsd` error bar, imply spreads that differ by more than 2 percent and by more than the rounding of their reported digits explains; the [data model](data-model.md) describes the rule. Order measurement and intervention rows by their central value with `ordering=central_value` on the `/api/v1/pkdata/` routes or `sort` in `POST /api/v2/query` (`-central_value` descending): it is the mean, else the median, else the geometric mean, and rows without any of them come last.

Interventions report `time` as a number, or as a list of administration times for an irregular schedule; a regular schedule uses `interval` (the dosing interval) and `doses` (the number of administrations) instead, with `time` the first administration. They also report `time_end`, `time_unit`, `tissue`, `method` and an optional `subject` whose dose statistics they describe. A schedule is not a string any more: format 1 `0|12|40` becomes `time` `[0, 12, 40]` and `S0T24R7` becomes `time` 0, `interval` 24 and `doses` 7. Characteristics carry `tissue`, `method`, `time` and `time_unit` like measurements.

## Database statistics

`GET /api/v2/statistics` returns one consistent, permission-filtered overview. Anonymous requests include public studies; authenticated requests additionally include studies the caller can access.

```bash
curl --fail "$PKDB_ENDPOINT/api/v2/statistics"
```

- `counts`: current totals, including `substance_count` (distinct substances with timecourses), `pk_count`, and `pk_calculated_count`.
- `years`: ascending calendar years from the first to the last dated study, with empty years included. Each row has `study_count`, `timecourse_count`, `substance_count`, `pk_count`, `pk_calculated_count`, `cumulative_study_count`, and `cumulative_substance_count`. Cumulative substances are distinct across years, not a sum of yearly counts.
- `undated`: the same annual metrics for studies without a date. These contribute to current totals but not cumulative dated counts; its cumulative fields are zero.
- `substances`: vocabulary `sid`, `name`, and distinct `timecourse_count`, ordered by descending coverage. A course containing several observations for the same substance counts once.
- `parameters`: sparse counts by vocabulary `sid`, `name`, and `year` (null for undated studies), split into `reported` and `calculated` values. Absent combinations have zero counts.
- `date_basis`: `study.date`; `generated_at`: UTC response generation time.

Years use the **study date**, not the reference publication date or upload timestamp. These are the dates of currently accessible studies, not historical database snapshots. PK parameter types follow descendants of `pharmacokinetic-measurement` in the vocabulary. Measurement metrics use normalized records, avoiding duplicate reported/normalized representations; calculated PK values are included in PK totals. Substance coverage requires a normalized observation in a timecourse. The existing `/api/v1/statistics/` count response remains compatible.

## Authenticate requests

Create a personal key in [Account settings](https://beta.pk-db.com/account), then provide it through `PKDB_API_KEY` in your environment. Send it as a Bearer credential:

```bash
curl --fail --header "Authorization: Bearer ${PKDB_API_KEY}" \
  "$PKDB_ENDPOINT/api/v2/studies"
```

Authentication adds access only to studies your account is allowed to read. For key scopes, expiry, and rotation, see [Accounts and API keys](authentication.md).

## Download a dataset

Downloads require authentication, including downloads of public data:

```bash
curl --fail "$PKDB_ENDPOINT/api/v2/exports" \
  --header "Authorization: Bearer ${PKDB_API_KEY}" \
  --header 'Content-Type: application/json' \
  --data '{"queries":{"studies":{"entity":"studies","predicates":[{"field":"sid","value":"STUDY_SID"}]}},"concise":true}' \
  --output dataset.zip
```

Export selection uses the `FilterSpec` schema, retaining `outputs` as its measurement entity key. Unlike list queries, exports are not restricted to one page. The response is a ZIP archive restricted to data your account can access. Preserve the study identifiers, selection criteria, and retrieval date with your analysis. Follow the licences attached to the studies.

## Curate data

Use the [Python client preparation and upload workflow](python-client.md#prepare-validate-and-upload-a-study-folder) to send study folders to `https://beta.pk-db.com`. It prepares and validates the source bundle and checks vocabulary compatibility before upload. A curator account and a key with `studies:write` are required; existing studies can be replaced only when your account has permission.

A study format 2 folder is sent to `PUT /api/v2/studies/{substance}/{name}` (validation only: `POST /api/v2/studies/{substance}/{name}/validate`) as multipart parts `study` and `reference` and one `files` part per further file of the folder. The client sends the exact bytes of `study.json` and `reference.json` as file parts, and the server writes the parts into a temporary `<substance>/<name>` folder and runs the same loader, validator and reader as the client, so both report the same issues. A format 2 folder sent to a single-segment route, or a format 1 bundle sent to a two-segment route, is refused with `study_format_route`, and text instead of file parts for a format 2 folder with `bundle_fields`. The substance and the name must be folder names of at most 255 bytes, and the identifier at most 255 characters (`invalid_study_location`).

An upload of a released study (a `release.pkdb_id` in `study.json`) whose identifier is not stored yet takes over the study that is stored under that PKDB identifier (a study format 1 study has it as its own study identifier) and renames it to `<substance>/<name>`; the result names the former study identifier in `renamed_from`. A PKDB identifier belongs to one study: another study claiming it, or a format 1 upload under the former study identifier of a renamed study, is refused with `duplicate_pkdb_id`. Without such a release, an upload whose identifier is not stored yet takes over the only stored study format 1 study of the same publication and source in the same way, keeps its former identifier for redirects and names it in `renamed_from`. The takeover needs edit rights on that study; otherwise, and when the PKDB identifier and the publication identify different studies, the upload is refused with a conflict (409, `publication_conflict` in upload reports) that names the other study only to its readers. A study of the same publication and source with a two-segment identifier is never taken over (409), and a format 1 upload under the former identifier of a taken over study is refused (409). Uploads stay idempotent, and the renamed study is replaced like any other replaced study.

## Handle errors

Upload permission rejections return HTTP 403 with an actionable code: `missing_scope`, `upload_role_required`, `study_write_forbidden`, `licence_change_forbidden`, or `creator_change_forbidden`. Standard responses include `detail` and `suggestion`; negotiated upload reports include the code, message, and suggestions in `report.issues`. These messages do not reveal existing private-study metadata. Rate limits use HTTP 429 and `Retry-After`; negotiated rate/capacity reports also expose the header value in issue `context.retry_after`.

Inspect the HTTP status and response body. Validation failures include structured issues where available. `401` indicates an authentication problem; `403` indicates insufficient access; `409` can indicate incompatible vocabulary or processing versions. Study format 2 raised the processing version to 9: a client that sends another processing version is refused (`processing_version_mismatch`), and every study stored with version 8 must be uploaded again with a matching client. Authenticated callers are not rate limited. Anonymous callers receiving `429` should respect `Retry-After`. Do not automatically retry an upload with an uncertain outcome: inspect the study first.


## Advanced queries and compatibility

`POST /api/v2/query` accepts an entity and typed predicates. For example, `{"entity":"groups","predicates":[{"field":"study_sid","operator":"eq","value":"PKDB01110"}],"page":1,"page_size":100}` selects groups in one study. Predicates combine with AND. The public `measurements` entity accepts the historical `outputs` alias. Consult the reference schemas for supported fields and operators.

The frontend retains compatibility reads under `/api/v1/`. New integrations should use v2. Legacy account/admin aliases and JSON-suffix read routes are disabled by default; `PKDB_LEGACY_API_ENABLED=true` enables those remaining compatibility routes. Legacy study/reference drafts, file-handle staging (including `/api/v2/files`), and `/api/v1/update_index/` have been retired permanently. Upload a complete bundle through `PUT /api/v2/studies/{sid}` (study format 1) or `PUT /api/v2/studies/{substance}/{name}` (study format 2) instead.

MCP exposes read operations only. Use REST or the Python client for validation, upload, and replacement.

## Detailed upload diagnostics

The capabilities response advertises supported `upload_report_versions`. Send `X-PKDB-Report-Version: 2` with `POST /api/v2/studies/validate`, `PUT /api/v2/studies/{sid}` or their two-segment variants for `<substance>/<name>` to receive a versioned report envelope. Requests without the header retain the legacy response shape. The current Python client negotiates this automatically.

The envelope contains `report_version`, `request_id`, `operation`, `status`, `stage`, `study`, `persistence`, `summary`, `report`, `result`, and `versions`. The successful replacement payload remains available under `result` and includes `url`, the study page on the public website origin configured by `PKDB_BROWSER_ORIGIN`; HTTP status codes keep their normal meanings. `X-Request-ID` is also returned as a response header for upload and validation requests.

Each report issue includes a stable `code`, severity, message, and available source location. Detailed diagnostics add `category`, `stage`, `field`, `actual`, `expected`, `context`, related sources, and correction suggestions where known. Spreadsheet coordinates refer to physical Excel rows and cells, including skipped comments or blank rows. JSON locations use key/index paths. An absent `actual` means the value is unavailable; an explicit null is an actual null value.

Reports include error/warning counts, returned/omitted issue counts, `truncated`, `complete`, and `stopped_reason`. Counts cover discovered issues; when validation is incomplete they are lower bounds. No caller should assume an incomplete report lists every defect. Source issues are bounded to protect response size, and untrusted diagnostic values are sanitized.

`persistence` distinguishes validation without writing (`not_attempted`), rejected writes (`not_saved`), confirmed creation/replacement (`created`/`replaced`), and uncertain outcomes (`unknown`). A transport failure can prevent the client from knowing whether a save committed. Preserve the request ID, inspect the study, and avoid automatic write retries. Internal errors provide a safe summary and correlation ID rather than a server traceback.
