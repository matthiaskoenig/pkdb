# Isolated frontend acceptance harness

Build `frontend/dist` with the pinned toolchain, install matching Playwright browser binaries and system dependencies, then run `npm run test:e2e` from `frontend/`. `run.sh` removes and recreates only the explicitly named `pkdb-frontend-test` project, waits for PostgreSQL/backend/Nginx readiness, runs all configured browser projects against the production artifact and removes that test project on exit. Its Compose path is absolute so cleanup remains correct after changing into `frontend/`.

`serve.py` refuses any database other than `pkdb_frontend_test`, any database username other than `pkdb_frontend_test`, any host other than the Compose service `db`, or a missing explicit fixture flag. Validation precedes migrations/bootstrap. Storage and PostgreSQL data are disposable tmpfs mounts; the harness never connects to a deployment database.

The artificial source bundle is shared with `backend/tests/api/test_frontend_search_contract.py`. Source ingestion uses the ordinary service and curator principal. Test-only SQL publishes the artificial study and adds explicit subset relationships. The complete vocabulary normalizes 2.125 mg/l to 0.002125 `gram / liter`; browser assertions use those authoritative values. API contract tests use a small controlled vocabulary and assert their corresponding mg/l output.

Per-browser reader accounts avoid interfering with the backend's real login throttles. Administrators use the same password login as other users. No real mail credentials are configured. Traces are off; account screenshots are off to avoid capturing show-once secrets. Scientific failure screenshots and reports remain available.
