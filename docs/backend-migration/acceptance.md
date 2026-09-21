# Backend replacement execution evidence

Implementation branch: `backend/fastapi-replacement`.

## Verified foundation evidence

- Legacy test suite: 108 passed on Python 3.9 against isolated PostgreSQL/Elasticsearch.
- Contract evidence tooling: 17 passed; inventory contains 178 route/method pairs.
- Read-only corpus inventory: 1,579 study folders; 1,559 parseable identities,
  20 malformed JSON files, 20 duplicate normalized-ID groups. All 30 apixaban
  folders have parseable identities. Integer IDs preserve legacy string conversion.
- New package: locked installation, runtime tests, type checks and clean-wheel
  scientific imports passed on Python 3.13.1 and 3.14.6.

## Outstanding acceptance gates

Populated-study baseline timings and golden payloads, canonical importer,
scientific parity, PostgreSQL schema/transactions, REST compatibility, MCP,
complete corpus dispositions, container builds, restore/cutover, and final review
are not complete. The legacy backend remains unchanged and is not retired.
