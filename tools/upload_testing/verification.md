# Apixaban upload verification, 2026-09-24

The isolated Docker harness completed successfully against all 30 apixaban studies. The development deployment was not accessed; the disposable PostgreSQL database and attachment files were removed on exit. The source corpus was mounted read-only and its content digest was unchanged after verification.

## Recorded environment

| Item | Value |
| --- | --- |
| Repository base revision | `0eae9dc3366b57b887c160b3b69a47050eb68a36` plus the upload-feedback working changes |
| Source repository revision | `76f5672d9916788ab4bd3c3698f7c1628a5c7bfc` |
| Corpus content SHA-256 | `2ad3fe1458e21cfe4498dbb27cfe08d81ed5d50f11d692843fc0e7e881bba256` |
| Initial implementation content SHA-256 | `c9b820b4f1330d82447c920f7e0d04745c002df3c85e269d5f4e5e3d5553da37` |
| Package/server version | `0.11.0` |
| Processing version | `5` |
| Vocabulary SHA-256 | `47a73e0d76d560cc002304b77efe349f72c5e6c724596f6f50fb3b8f1b0bbc40` |
| Report versions advertised | `1`, `2` |
| Local evidence directory | `/tmp/pkdb-upload-complete` |

The initial implementation digest includes sorted relative paths and contents under `python/src`, `backend/src`, and this harness, including newly added files, excluding bytecode. Terminal formatting and fallback guidance received additional separately tested refinements during verification; the hash records the initial working tree, not a claim that the whole working tree was frozen throughout the run.

## Observed outcomes

| Pass | Attempted | Created | Replaced | Rejected | Unknown/unattempted |
| --- | ---: | ---: | ---: | ---: | ---: |
| Offline validation with synchronized server vocabulary | 30 | 0 | 0 | 6 | 0 |
| Public CLI upload, human output and saved report | 30 | 24 | 0 | 6 | 0 |
| Public CLI upload, JSON Lines and saved report | 30 | 0 | 24 | 6 | 0 |
| Direct negotiated multipart API requests | 30 | 0 | 24 | 6 | 0 |

All 24 locally valid studies were created and then replaced. All six locally invalid studies were also rejected directly by the backend with HTTP 422 and `persistence=not_saved`. The 24/6 split matches the earlier baseline. Each CLI batch exited 1 because of expected invalid studies; the complete harness exited 0. The first upload batch took approximately 46 seconds summed across study outcomes.

Every successful SID was retrieved through the public API. Direct replacement result counts and digests matched the initial created results. Every rejected SID returned HTTP 404, demonstrating absence of partial study persistence in this fresh database. Negotiated responses included matching body/header request IDs. Actual HTTP probes also verified missing credentials (401), missing write scope (403), and unsupported report version (400), all with structured diagnostic envelopes.

## Source diagnostics checked against the real files

| Study | Verified source | Observed value/problem |
| --- | --- | --- |
| Frost2013a | `study.json`, `outputset.outputs[3].image` | Reference contains `Tab2 \|\| Tab3`; expected `Frost2013a_Tab3.png` is absent and the report lists available images |
| Frost2014a | `Tab3!F10` | `AA-induced aggregation` |
| Frost2015 | `Fig4!M735` | `-1.651`; the historical reported row 734 is a comment row |
| Frost2018 | `Fig3!I3` | Unknown method `thrombin generation assay` |
| Frost2018 | `Fig3!R3` | Unit `percent`, independently reported from the method failure |
| Frost2018 | `Fig3!F8` | Unknown measurement `LAG (change relative)` |
| Kreutz2017 | `Fig3!F3` | `ETP ratio` |
| Wang2016 | `Tab3`, header row 2 | `label` is absent; report lists actual headers and explains that no cell exists for this missing column |

The harness independently reads representative returned spreadsheet cells with openpyxl and compares their values to diagnostic `actual` values. The JSON image reference and missing Wang2016 header were checked separately. Wang2016 currently identifies the table and available headers, with guidance to inspect the `col==` mapping; it does not provide an exact JSON path to that mapping.

Testing exposed stale Excel dimensions in Jeong2019 (1,048,576 rows and 1,024 columns) and a comment-row offset in Frost2015. The reader was corrected and regression tests added before the successful run. No source workbook was modified.

## Presentation and scope

Redirected human output showed study stages, confirmed created/replaced results, grouped diagnostics, actual values, expected constraints, and correction guidance. JSON stdout remained parseable JSON Lines; separate batch reports preserved individual diagnostic occurrences. A 60-column pseudo-terminal validation of Frost2014a was also reviewed: spinner cleanup restored the cursor, 18 errors were grouped into two terms with nine cell locations each, and narrow output remained readable.

The complete upload capture predates two final renderer-only refinements: displaying JSON Pointers for JSON source paths, and printing the completed transfer byte count in noninteractive mode. Focused tests cover both refinements. A fresh human validation of Frost2013a confirmed the final renderer displays `/outputset/outputs/3/image` with the expected filename and correction guidance.

This harness exercises real creates, replacements, validation rejections and authentication/scope/report-version faults. Synthetic contract tests separately cover compatibility mismatches, limits, response loss, rollback and interruption; the real corpus run does not inject those faults. No corpus case generated a warning-only successful upload. Raw evidence and reports remain in the local temporary directory and are not committed.
