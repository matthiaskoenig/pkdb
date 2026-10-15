#!/usr/bin/env bash
# Render the screenshots of docs/web-interface.md: start the disposable website of the browser
# tests (tools/frontend_testing) with its artificial fixture, run render.mjs against it, and remove
# the website again on exit. Build frontend/dist first, see README.md.
set -euo pipefail
cd "$(dirname "$0")/../.."
# The fixed, distinct project of the browser tests; never the default stack.
compose=(docker compose -p pkdb-frontend-test -f "$PWD/compose.frontend-test.yaml")
cleanup() { "${compose[@]}" down --volumes --remove-orphans; }
trap cleanup EXIT
# Start from a fresh fixture.
cleanup
"${compose[@]}" up --build --wait --wait-timeout 240
node tools/website_docs/render.mjs
