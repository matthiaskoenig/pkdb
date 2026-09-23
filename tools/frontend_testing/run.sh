#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
# Fixed, distinct project and database; never operate on the default stack.
compose=(docker compose -p pkdb-frontend-test -f "$PWD/compose.frontend-test.yaml")
cleanup() { "${compose[@]}" down --volumes --remove-orphans; }
trap cleanup EXIT
# Start from a fresh disposable fixture, including account throttle state.
cleanup
"${compose[@]}" up --build --wait --wait-timeout 240
cd frontend
npx playwright test "$@"
