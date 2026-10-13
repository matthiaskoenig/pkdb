# Unreleased

- The paper viewer of the local curation app no longer logs two errors of PDF.js to the console of the browser when a PDF closes while a page of it loads, as when another PDF is chosen quickly (#930).
- Continuous integration runs its test jobs in parallel and skips them for a change of the documentation only: the frontend browser tests run one job per browser and the curation app browser tests on every core, the backend image is built once per run with a layer cache, every backend test copies a template database that is migrated once instead of migrating its own, the test database runs without durable writes, and the five speed tests of the client run apart with `pytest -m slow` (#PR).
