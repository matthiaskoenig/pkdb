---
search:
  exclude: true
---

# Upload feedback implementation plan

Specification: [Upload feedback design](../specs/2026-09-24-upload-feedback-design.md).

1. Extend shared diagnostics with source coordinates, actual/expected values, guidance, bounded aggregation, and legacy serialization. Cover the observed apixaban failures with focused tests.
2. Add negotiated backend report envelopes and capabilities, preserve legacy responses, and expose request IDs and truthful persistence outcomes. Test API compatibility and error mapping.
3. Add client report adapters and structured progress events. Implement readable terminal output, explicit JSON mode, batch summaries, atomic reports, failure/interruption handling, and focused CLI tests.
4. Exercise actual apixaban validation/upload/replacement in an isolated Docker project, preserving source files and the existing local deployment. Record counts and limitations.
5. Update user documentation and release notes. Run relevant Python tests, lint, types, documentation build, and review the final diff.

## Completion evidence

- Shared diagnostics now include actual/expected values, original source coordinates, correction guidance, vocabulary candidates, related definitions, bounded payloads, and explicit completeness flags. Physical Excel rows are preserved, including comments and empty rows; stale worksheet dimensions no longer cause padding scans.
- Backend report v2 is negotiated through capabilities and `X-PKDB-Report-Version`; legacy REST, MCP, and server CLI report shapes remain compatible. Responses retain request IDs, HTTP semantics, version context, and conservative persistence outcomes.
- The public client supports structured progress events and detailed errors. Terminal output groups repeated issues, reports measured transfer bytes and server waiting time, and provides atomic batch reports, JSON output, fail-fast behavior, interruption handling, and unknown-outcome protection.
- The isolated apixaban harness verified all 30 source studies: 24 created, 24 replaced on the second pass, and six failures reproduced through direct server requests. Confirmed SID/count/digest checks, absence of rejected studies, physical cell/value checks, and unchanged corpus digest passed. No existing development database was modified.
- Backend regression suite: 558 passed. Python client, diagnostics, and presentation suite: 100 passed. Ruff, formatting, backend/client type checks, and Zensical clean build pass. See `tools/upload_testing/README.md` and `tools/upload_testing/verification.md` in the repository for commands and corpus outcomes.

## Deliberate limits

The synchronous API reports measured request transfer progress and elapsed server waiting time, not fabricated server completion percentages. Parser failures that prevent safe continuation explicitly mark the report incomplete; independent scientific validation errors are collected. Some nested source mappings retain the nearest reliable record location rather than inventing a cell. Large issue sets retain bounded diagnostics and truncation flags; users resolve reported issues and rerun. Real network-loss and interruption outcomes are covered through focused fault tests, while the full corpus harness exercises the real happy path and scientific/API rejection paths.

The final renderer received small post-harness improvements to JSON-pointer display and transfer-completion lines. These are covered by focused presentation tests; they do not change source parsing, requests, or persistence.
