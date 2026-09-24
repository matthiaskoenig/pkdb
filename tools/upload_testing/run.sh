#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export PKDB_UPLOAD_CORPUS="$(realpath "${1:?Usage: run.sh /path/to/apixaban [evidence-directory]}")"
evidence="$(realpath -m "${2:-/tmp/pkdb-upload-evidence-$(date +%s)}")"
mkdir -p "$evidence"
project="pkdb-upload-test-$(date +%s)-$$"
compose=(docker compose -p "$project" -f "$PWD/tools/upload_testing/compose.yaml")
cleanup() {
  "${compose[@]}" cp backend:/tmp/upload-evidence/. "$evidence/" 2>/dev/null || true
  "${compose[@]}" logs --no-color backend > "$evidence/backend.log" 2>&1 || true
  "${compose[@]}" down --volumes --remove-orphans
}
trap cleanup EXIT
git rev-parse HEAD > "$evidence/server-revision.txt"
git diff --binary HEAD | sha256sum > "$evidence/server-working-diff.sha256"
python3 - <<'PY' > "$evidence/implementation.sha256"
import hashlib
from pathlib import Path

digest = hashlib.sha256()
paths = [p for root in ("python/src", "backend/src", "tools/upload_testing")
         for p in Path(root).rglob("*")
         if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]
for path in sorted(paths):
    content = path.read_bytes()
    digest.update(str(path).encode() + b"\0" + str(len(content)).encode() + b"\0")
    digest.update(content)
print(digest.hexdigest())
PY
git -C "$PKDB_UPLOAD_CORPUS" rev-parse HEAD > "$evidence/source-revision.txt"
"${compose[@]}" up --build --wait --wait-timeout 240
"${compose[@]}" exec -T backend python /app/upload_testing/verify.py
"${compose[@]}" cp backend:/tmp/upload-evidence/. "$evidence/"
printf 'Evidence: %s\n' "$evidence"
