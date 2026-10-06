# Executable API examples

These examples find apixaban studies, retrieve the complete Frost2014 study (`PKDB01110`), select its concentration measurements, query its groups, and export its dataset. They only read server data. Run against a server containing those studies, such as the [local upload setup](local-upload-testing.md) after uploading apixaban. Counts depend on the server's data and your access permissions.

## Run the examples

From a source checkout, set the endpoint and enter a personal API key with the `read` scope. Exports require authentication, including for public studies:

```bash
export PKDB_ENDPOINT=http://localhost:18083
read -r -s -p 'Read API key: ' PKDB_API_KEY
printf '\n'
export PKDB_API_KEY

# Python requests, saved canonical JSON, ZIP, and a compact summary:
uv run --with httpx python tools/api_examples/example.py --output api-example-results

# Equivalent curl requests, saving each response:
bash tools/api_examples/example.sh api-example-curl-results

unset PKDB_API_KEY
```

Both scripts stop on an HTTP failure. The Python script accepts `--endpoint`, `--substance`, and `--study-sid` overrides; the shell script takes the study identifier as an optional second argument (`bash tools/api_examples/example.sh api-example-curl-results PKDB01110`). Its output includes study identifiers from the first page, the canonical study identifier, total matching measurements and groups, and ZIP member names. It saves `study.json`, `dataset.zip`, and `summary.json`; existing files in the output directory are overwritten.

## Understand the requests

| Step | Request | Result |
| --- | --- | --- |
| Find studies | `GET /api/v2/studies?substance=apixaban&page_size=20` | Study summaries and pagination |
| Read one study | `GET /api/v2/studies/PKDB01110` | Complete canonical study, including measurements |
| Select measurements | `GET /api/v2/measurements?study_sid=PKDB01110&measurement_type=concentration` | Concentration measurement rows |
| Query groups | `POST /api/v2/query` with a groups query | Groups belonging to the study |
| Export | `POST /api/v2/exports` with a study selection | ZIP containing tabular data and reuse terms |

List responses contain `items`, `total`, `page`, `page_size`, `next`, and `previous`. The scripts intentionally read a first page while reporting total matches. Retrieve subsequent pages for complete tabular analysis, or use the export. The canonical study endpoint returns the complete study rather than a page.

## Study format 2 studies

A study in study format 2 is identified by its substance and name, such as `caffeine/Harder1988`, instead of `PKDB01110`. Pass it as the study identifier (`--study-sid caffeine/Harder1988` or the second argument of the shell script) and the same requests read it: `GET /api/v2/studies/caffeine/Harder1988` has two path segments, and `GET /api/v2/measurements?study_sid=caffeine/Harder1988` and the groups query take the identifier as a value. The PKDB identifier of a released study redirects to it, so `GET /api/v2/studies/PKDB00198` answers `308` with the `Location` of the two-segment route. `curl --location` and the `pkdb` Python client follow it, but the example scripts do not, so give them the canonical identifier. See [study identifiers and redirects](api.md#study-identifiers-and-redirects).

Measurement rows report their statistics in `mean`, `median`, `min`, `max`, `sd`, `se`, `cv`, `gmean`, `gsd`, `gcv`, `error_bar` and `error_type`, and the value of a single subject or an unspecified summary is in `mean`; there is no `value` field (see [statistics in responses](api.md#statistics-in-responses)).

## Verified fixture output

The backend integration suite executes the Python example against its isolated PostgreSQL fixture and real API routes. That synthetic study uses `TEST1` and substance `drug`, not an apixaban publication. Its expected summary is stored in [`tools/api_examples/expected-fixture.json`](https://github.com/matthiaskoenig/pkdb/blob/develop/tools/api_examples/expected-fixture.json). The test checks the response fields and the actual ZIP member list. This output documents the API contract; it is not a claim about current hosted apixaban counts.

## Understand a rejected upload

Uploads use the separate curation workflow. To inspect every returned issue while keeping reports outside the source folder:

```bash
pkdb upload /path/to/pkdb_data/studies/apixaban --report upload-report.json
```

The [upload report](api.md#detailed-upload-diagnostics) contains the request ID, stage, save outcome, issue codes, offending values, expected rules, and source file/sheet/cell where available. A reported source error should be corrected in the original study files before retrying. Incomplete or truncated reports do not enumerate every defect. A transport failure with an unknown save outcome requires checking the study before another write.

See [Python upload diagnostics](python-client.md#inspect-a-rejected-upload) for programmatic handling and the [read-only MCP guide](mcp.md) for agent access.
