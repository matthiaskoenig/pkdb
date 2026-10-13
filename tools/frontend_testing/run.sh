#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
# Fixed, distinct project and database; never operate on the default stack.
compose=(docker compose -p pkdb-frontend-test -f "$PWD/compose.frontend-test.yaml")
# CI names the backend image that it built once for the run in PKDB_TEST_IMAGE;
# without it the backend is built from this checkout.
if [[ -n "${PKDB_TEST_IMAGE:-}" ]]; then
  # With --no-build, compose would try to pull a missing image from a registry.
  if ! docker image inspect "$PKDB_TEST_IMAGE" > /dev/null 2>&1; then
    echo "The backend image $PKDB_TEST_IMAGE of PKDB_TEST_IMAGE does not exist." \
      "Build or load it first, or unset PKDB_TEST_IMAGE to build the backend from this checkout." >&2
    exit 1
  fi
  build=--no-build
else
  build=--build
fi
cleanup() { "${compose[@]}" down --volumes --remove-orphans; }
trap cleanup EXIT
# Start from a fresh disposable fixture, including account throttle state.
cleanup
"${compose[@]}" up "$build" --wait --wait-timeout 240
cd frontend
# The arguments go to Playwright, for example --project=chromium for one browser.
npx playwright test "$@"
