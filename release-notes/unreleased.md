# Unreleased

- The paper viewer of the local curation app no longer logs two errors of PDF.js to the console of the browser when a PDF closes while a page of it loads, as when another PDF is chosen quickly (#930).
- Continuous integration runs its test jobs in parallel and skips them for a pull request that changes only the documentation: the frontend browser tests run one job per browser and the curation app browser tests on every core, the jobs that start the backend image build it from a layer cache, every backend test copies a template database that is migrated once instead of migrating its own, the test database runs without durable writes, and the five speed tests of the client run apart with `pytest -m slow` (#950).
