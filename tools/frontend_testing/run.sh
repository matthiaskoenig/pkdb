#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
# Fixed, distinct project and database; never operate on the default stack.
compose=(docker compose -p pkdb-frontend-test -f "$PWD/compose.frontend-test.yaml")
cleanup() { "${compose[@]}" down --volumes --remove-orphans; }
trap cleanup EXIT
# Start from a fresh disposable fixture, including account throttle state.
cleanup
# CI names the backend image that it built once for the run in PKDB_TEST_IMAGE;
# without it the backend is built from this checkout.
if [[ -n "${PKDB_TEST_IMAGE:-}" ]]; then build=--no-build; else build=--build; fi
"${compose[@]}" up "$build" --wait --wait-timeout 240
cd frontend
# The arguments go to Playwright, for example --project=chromium for one browser.
npx playwright test "$@"
