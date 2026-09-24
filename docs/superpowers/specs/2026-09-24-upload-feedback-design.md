---
search:
  exclude: true
---

# Study upload progress and actionable validation reports

Date: 2026-09-24. Status: Implemented locally and verified with authenticated apixaban uploads. This document records the design; implementation results and deliberate limits are recorded in the [implementation plan](../plans/2026-09-24-upload-feedback.md).

## 1. Objective

Make preparing, validating, and uploading studies understandable without reading raw JSON or backend code. For every failure, identify what went wrong, where the curator should look, what rule applies, and what action can resolve it. The backend JSON response is the authoritative diagnostic contract. The terminal interface presents that information without inventing diagnoses or scientific corrections.

Scope includes the public `pkdb` package, shared validation schemas and source provenance, backend validation/upload endpoints, batch reporting, documentation, and integration tests. No automatic source edits, implicit vocabulary changes, automatic upload retries, parallel uploads, or asynchronous server job system are required for the first release.

## 2. Current behavior and evidence

`python/src/pkdb/cli.py` prints one JSON object per study after processing completes. `Client.upload()` reparses and validates source files, checks server capabilities and limits, transfers a multipart bundle, and waits synchronously for the result. The backend exposes `POST /api/v2/studies/validate` and `PUT /api/v2/studies/{sid}`. Successful uploads return `ReplacementResult` with SID, created/replaced state, digest, counts, and warnings.

`ValidationIssue` currently contains `code`, `severity`, `message`, and an optional source location. `SourceLocation` supports file, sheet, row, column, and a logical path. Scientific validation errors return HTTP 422 with report fields at the top level. Other errors frequently return only `detail`. Both shared validation models and the current client parser reject unknown report fields, so richer responses require explicit compatibility handling.

On 2026-09-24, local offline validation of `/home/mkoenig/git/pkdb_data/studies/apixaban` using the checkout's bundled vocabulary discovered 30 studies: 24 passed and six failed. Output occupied approximately 52 KB. This is a local validation baseline, not evidence of successful uploads or of compatibility with the running server's vocabulary. The local server was healthy, but no `PKDB_API_KEY` was available to this session.

| Study | Observed representative failure | Required diagnostic improvement |
| --- | --- | --- |
| Frost2013a | `unknown_image`: No image file for Tab3; source absent | Locate the source reference and show the expected attachment and available relevant filenames |
| Frost2014a | `unknown_measurement`: AA-induced aggregation; Tab3, row 10 and others | Identify the measurement column, group repeated occurrences, and provide verified vocabulary candidates where appropriate |
| Frost2015 | `negative_value`: mean must be nonnegative for concentration; Fig4, row 734 | Show the actual value, mean cell, measurement type, and applicable rule |
| Frost2018 | Unknown thrombin generation assay; percent has no normalized unit for ETP (change relative) | Report method and unit issues separately with their respective cells and valid constraints |
| Kreutz2017 | `unknown_measurement`: ETP ratio; Fig3, row 3 and others | Locate all affected rows and distinguish missing vocabulary from a spelling mismatch |
| Wang2016 | `unknown_column`: label; Tab3, row 3 | Point to the header cell, identify the table schema, and list permitted headers |

Do not change these source studies merely to obtain a green test result. Corpus corrections are separate work.

## 3. Diagnostic contract

Define a versioned `UploadReport` envelope containing a shared `ValidationReport`. Use the same issue schema for local preparation, server validation, API errors, successful-upload warnings, saved CLI reports, and Python exceptions. Keep transport context in the envelope rather than duplicating it on every issue.

### Envelope fields

| Field | Meaning |
| --- | --- |
| `report_version` | Integer schema version, initially 2 for the new contract |
| `request_id` | Server-generated correlation identifier, also returned in `X-Request-ID`; null for local-only validation |
| `operation` | `prepare`, `validate`, or `upload` |
| `status` | `succeeded`, `failed`, or `unknown`; unknown is a client-side result when the server outcome cannot be established |
| `stage` | Stage where processing finished or failed |
| `study` | Known SID and name; nullable when source parsing has not established identity |
| `persistence` | `not_attempted`, `not_saved`, `created`, `replaced`, or `unknown` |
| `summary` | Short human-readable result, without embedded raw payloads |
| `report` | Issues, counts, completeness, and truncation metadata |
| `result` | Existing successful replacement payload, or null |
| `versions` | Available client/server processing versions and vocabulary hashes; include expected and actual versions for mismatches |

Server validation responses use `not_attempted`; a rejected upload uses `not_saved` only when no commit occurred. A confirmed commit uses `created` or `replaced`. Connection loss after sending a request must produce `unknown` on the client, never “not uploaded.” A database replacement remains atomic: failures before commit preserve the previous study and attachments. Serialization or connection failure after commit must not falsely claim rollback.

### Issue fields

Retain `code`, `severity`, `message`, and `source`. Add:

- `category`: parsing, schema, vocabulary, scientific, reference, permission, compatibility, limit, transport, or internal.
- `stage`: discover, read, parse, validate, compatibility, transfer, server_validation, or save.
- `field`: logical field name such as `mean` or `measurement_type`.
- `actual`: bounded JSON value, preserving its original type; omit when unavailable or inappropriate to disclose. Distinguish omitted from an actual null.
- `expected`: typed constraints such as a minimum, allowed values, expected identifier, expected dimensions, or maximum file size. Avoid unrestricted prose as the only representation of a rule.
- `context`: bounded, allowlisted scientific context such as table type, row identifier, measurement type, substance, unit, and related entity IDs.
- `related_sources`: labeled locations for the originating definition, duplicate record, referenced entity, or conflicting value.
- `suggestions`: structured actions with a stable action kind, explanation, and optional verified candidate values or a safe CLI command. Suggestions are advisory, never automatically applied.
- `documentation_url`: optional maintained documentation anchor for the error class.

Error codes are stable machine identifiers. Messages must be readable without understanding code names. A central registry defines each code's meaning, required context, HTTP mapping, and guidance. Preserve existing codes where their meaning is unchanged. Unknown future codes still render their message and source correctly.

### Source locations

Use bundle-relative filenames only. Spreadsheet locations identify the actual sheet, one-based physical row, Excel column letter, optional cell address, and original header text. Add optional `cell` and `header` fields while retaining existing source fields. JSON locations use a path whose string members are object keys and integer members are zero-based array indices. Never infer an Excel row from a filtered dataframe index.

Retain provenance through parsing, normalization, derived calculations, and reference resolution. For a derived-value failure, point to the input cells and explain the derivation. For duplicate IDs, identify both definitions. For missing references, point to the referring cell or JSON field. If exact provenance is unavailable, report the most precise known location and explain the limitation; do not manufacture a cell.

### Illustrative HTTP 422 response

This is a synthetic example of the proposed shape, not the measured numeric value or column from Frost2015.

```json
{
  "report_version": 2,
  "request_id": "example-request-id",
  "operation": "upload",
  "status": "failed",
  "stage": "server_validation",
  "study": {"sid": "EXAMPLE001", "name": "ExampleStudy"},
  "persistence": "not_saved",
  "summary": "Study was not saved: 1 validation error.",
  "report": {
    "issues": [{
      "code": "negative_value",
      "severity": "error",
      "category": "scientific",
      "stage": "server_validation",
      "message": "Concentration mean must be greater than or equal to zero; received -0.12 ng/ml.",
      "source": {
        "file": "ExampleStudy.xlsx",
        "sheet": "Fig4",
        "row": 734,
        "column": "H",
        "cell": "H734",
        "header": "mean",
        "path": []
      },
      "field": "mean",
      "actual": -0.12,
      "expected": {"minimum": 0},
      "context": {"measurement_type": "concentration", "unit": "ng/ml"},
      "related_sources": [],
      "suggestions": [{
        "kind": "inspect_source",
        "message": "Check the recorded mean and measurement type against the publication. If this is a change measurement, verify that the appropriate change term was intended. Do not replace the value automatically."
      }]
    }],
    "error_count": 1,
    "warning_count": 0,
    "returned_issue_count": 1,
    "omitted_issue_count": 0,
    "truncated": false,
    "complete": true,
    "stopped_reason": null
  },
  "result": null,
  "versions": null
}
```

## 4. Collection, limits, and useful guidance

Collect independent errors across readable rows and files rather than stopping at the first recoverable issue. Do not continue dependent scientific calculations after their prerequisites fail. Avoid cascades such as reporting dozens of unit failures caused solely by an unknown measurement. Independent failures, such as an unknown method and incompatible unit, remain separate.

Order issues deterministically by file, sheet, row, column, and code. API issues preserve individual source occurrences; terminal grouping is presentation only. Initial limits are 1,000 returned issues, a 2 MiB serialized response budget, 512 characters for individual displayed input strings, and 10 candidate suggestions. File sizes, row counts, and validation time retain explicit server-side resource budgets.

`error_count` and `warning_count` count all discovered occurrences, not groups. `omitted_issue_count` counts discovered issues excluded from the response. If validation stops before examining all input, set `complete=false` and explain `stopped_reason`; counts are then lower bounds, not claims about unseen input. `truncated=true` means diagnostic content was omitted. A saved client report must retain these flags and must not claim it contains diagnostics the server did not return. Users resolve reported problems and rerun; phase one does not require a report-storage service.

Guidance must be specific and scientifically conservative:

- Unknown vocabulary: show the supplied term and vocabulary context. Offer bounded candidates only from the active vocabulary and label them as suggestions, not equivalent scientific concepts.
- Invalid units: show supplied unit, parsed dimensions when available, expected dimensions, and supported units for the measurement.
- Missing attachment: identify the referring source, expected filename or matching rule, and relevant available names, including case mismatches.
- Invalid header: locate the header cell and show required/permitted columns for that table type.
- Reference failures: show missing or duplicate IDs and related locations, restricted to information the actor may access.
- Compatibility failures: show expected/actual versions and the appropriate vocabulary-sync or package-update instruction.
- Permission failures: state the action or scope required when safe, without disclosing private study existence or account details.
- Size limits: report actual size/count and the permitted maximum.
- Internal failures: return a request ID and a safe summary; keep tracebacks and server paths in operator logs.

Preserve HTTP semantics: validation/schema errors 422, malformed HTTP requests 400, missing credentials 401, forbidden operations 403, state/compatibility conflicts 409, size limits 413, throttling 429, and unexpected failures 500. The detailed report supplements status codes rather than returning HTTP 200 for failures. Preserve `WWW-Authenticate` and `Retry-After` where applicable. Gateways or proxies may return non-JSON errors; clients must handle those safely too.

Never echo credentials, authorization headers, session cookies, complete submitted documents, or arbitrary spreadsheet rows. Redact before formatting or saving reports. Render untrusted messages as literal terminal text, escape markup, remove control sequences, and validate clickable URLs.

## 5. API compatibility and Python client

Advertise `upload_report_versions: [1, 2]` through capabilities. New clients request `X-PKDB-Report-Version: 2` on validation/upload calls; absence of this header preserves the exact legacy response shape, including successful warning objects. Add the header to browser CORS allowances and expose `X-Request-ID`. Unsupported explicit versions receive a documented structured 400 error. This permits client-first or server-first rollout without silently dropping diagnostics.

New clients normalize legacy top-level reports and new envelopes into a common internal model. They must not reject an otherwise usable report because a future response contains additional optional fields. Keep server-side output validation strict. Test the response adapter separately from the domain models. Preserve existing `ClientError.status_code` and `ClientError.report`; add request ID, stage, and persistence context without forcing Python callers to parse terminal text. Keep the successful `Client.upload()` result API compatible.

One report builder maps known exceptions to structured reports. Add provenance and context at the point a failure is detected, not by parsing exception strings in the CLI. Unexpected exceptions receive request IDs and operator logs with stack traces. Server diagnostics remain useful with curl or any third-party client, independently of the Rich-style terminal rendering.

## 6. Terminal interaction

Interactive terminals default to a readable progress interface. Redirected stdout defaults to the existing JSON Lines format; `--format human|json` overrides detection. Human mode without a TTY uses stable plain lines, not animation. Respect `NO_COLOR`, terminal width, and Unicode limitations. `--verbose` reveals additional diagnostic context; it never reveals secrets. JSON mode has no decorative text or escape sequences on stdout.

Before the batch, show endpoint, source folder, study count, and preparation/version checks. Only show authentication or write-permission checks as passed when the server has actually verified them; reachability or a successful public capabilities request is insufficient. If no suitable non-mutating permission probe exists, defer confirmation to the write response and label it accordingly. Cache batch-invariant preflight checks but retain server-side authorization and compatibility checks on every upload.

Per study, show read/parse, local validation, compatibility checks, source transfer, waiting for server validation/save, and confirmed result. Overall progress counts terminal study outcomes and explicitly labels that count as processed, not successful. Transfer progress measures request bytes consumed by the transport, including the multipart body, and does not imply server acceptance. The synchronous endpoint cannot provide real server completion percentages; show a spinner and elapsed time until its response arrives.

Completed studies leave concise created/replaced/failed lines with SID, elapsed time, warnings, and a study link when confirmed. Never print a success indicator before a confirmed save. Errors expand into source, actual value, applicable rule, and next steps. Group repeated occurrences and show at most five representative issues per study by default, with the total and report location clearly visible. Reports available through `--verbose` or files retain every returned issue.

Continue after study-specific validation failures by default. `--fail-fast` stops after the first failure. Abort the batch for shared authentication or compatibility failures and mark remaining studies unattempted. A lost response marks the active study outcome unknown and stops the batch; do not retry a write automatically. Ctrl-C stops scheduling new studies, writes the partial report, and distinguishes unsent requests from uncertain in-flight writes. Clean up progress rendering in all exit paths.

Final summary: discovered, attempted, created, replaced, failed, unknown, unattempted, warnings, elapsed time, and report path. Categories must reconcile to discovered studies. Exit 0 only if all requested studies succeeded; exit 1 for any failure/unknown outcome or report-writing failure, 2 for invalid CLI usage, and 130 for user interruption. Warnings alone do not cause failure.

## 7. Saved batch report and progress events

Add `--report PATH` for a versioned batch JSON report containing command, endpoint, source root, timestamps, tool/rule versions, summary counts, and one normalized result per study. Include each returned API diagnostic and completeness flags. Write atomically after each terminal study outcome and on interruption. Reject report paths inside any input study directory so output cannot change the source bundle. Preserve the existing single-study `--output` semantics. Do not write a default report file without telling the user or silently overwrite an existing report; require an explicit overwrite option when necessary.

Use structured progress callbacks/events in preparation and the client, with no printing from library code. Events identify study, stage, start/completion, monotonic elapsed time, byte counters when measurable, and final outcome. A terminal renderer and a machine-output renderer consume the same results. Batch reporting remains independent of terminal rendering failures. Do not duplicate scientific validation in the renderer or remove the client's source-change verification merely to speed up progress display.

## 8. Validation and acceptance

Implement contract tests for both negotiated report versions, legacy and new servers, structured warnings on success, future optional fields, non-JSON errors, and preserved HTTP headers/statuses. Test real spreadsheet and JSON provenance, zero/null/type handling, duplicated definitions, unit rules, missing files, multiple independent errors, deterministic ordering, bounded output, incomplete validation, and secret/control-character sanitization.

Use an isolated local Docker test project with a fresh database and attachment volume. Provision a test administrator, import attribution accounts, and obtain a scoped key through supported authentication helpers. Mount apixaban source read-only. Do not reset or write to the user's running development database as part of automated testing. Record the server/client revision, source revision or digest, and vocabulary hash with results.

Run all 30 apixaban studies through the actual package and backend. First reproduce local validation with the selected server vocabulary; report any change from the 24/6 baseline rather than hard-coding that split as universal truth. Upload valid studies, verify persisted SIDs and counts through the API, then repeat uploads to exercise replacement. Invalid studies must produce actionable reports without partial persistence. Exercise server-side rejection directly as well, because local rejection alone does not test backend reports. For the six observed failures, verify source coordinates and relevant context against the files; where a defect is fixed upstream, use a small synthetic regression fixture to retain coverage.

Use disposable fixtures or fault injection for authentication failure, missing scope, stale vocabulary, upload limit, timeout/connection loss, rollback, and interruption. Never insert faults into the real source corpus. Test interactive human output, narrow/plain terminals, piped JSON, warning-only success, partial report preservation, and mixed batch outcomes. Timings and request IDs must not make snapshot tests brittle.

Acceptance requires that a curator can identify the offending source location, understand the violated rule, and choose the next action from the JSON response alone; that the CLI makes the same information easier to read; and that reported persistence/progress never overstates what the client knows. Record actual apixaban upload outcomes and remaining limitations before claiming end-to-end completion.

## 9. Delivery sequence

1. Define versioned report schemas, issue registry, compatibility adapters, and contract fixtures.
2. Improve source provenance and diagnostics for the six observed apixaban failure classes; unify backend error mapping and report negotiation.
3. Add structured client/preparation progress events, terminal presentation, and durable batch reports.
4. Run isolated real apixaban uploads and replacement/failure scenarios; review readable output and raw JSON together.
5. Update Python client and local-upload documentation with output modes, report interpretation, exit codes, and troubleshooting; publish coordinated client/server compatibility guidance.

Implementation choices that do not alter this contract can be resolved during development. Any proposal to weaken scientific validation, silently repair source data, or claim server percentage progress without server evidence requires a separate design decision.
