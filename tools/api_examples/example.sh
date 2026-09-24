#!/usr/bin/env bash
# Read-only examples. Export writes a local ZIP, not server-side study data.
set -euo pipefail
: "${PKDB_API_KEY:?Set a read-scoped PKDB_API_KEY for dataset export}"
endpoint="${PKDB_ENDPOINT:-http://localhost:18083}"
result_dir="${1:-api-example-results}"
mkdir -p "$result_dir"

curl --fail-with-body --silent --show-error --get "$endpoint/api/v2/studies" \
  --header "Authorization: Bearer $PKDB_API_KEY" \
  --data-urlencode 'substance=apixaban' --data-urlencode 'page_size=20' \
  --output "$result_dir/studies.json"

curl --fail-with-body --silent --show-error "$endpoint/api/v2/studies/PKDB01110" \
  --header "Authorization: Bearer $PKDB_API_KEY" \
  --output "$result_dir/study.json"

curl --fail-with-body --silent --show-error --get "$endpoint/api/v2/measurements" \
  --header "Authorization: Bearer $PKDB_API_KEY" \
  --data-urlencode 'study_sid=PKDB01110' \
  --data-urlencode 'measurement_type=concentration' \
  --output "$result_dir/measurements.json"

curl --fail-with-body --silent --show-error "$endpoint/api/v2/query" \
  --header "Authorization: Bearer $PKDB_API_KEY" --header 'Content-Type: application/json' \
  --data '{"entity":"groups","predicates":[{"field":"study_sid","value":"PKDB01110"}]}' \
  --output "$result_dir/groups.json"

curl --fail-with-body --silent --show-error "$endpoint/api/v2/exports" \
  --header "Authorization: Bearer $PKDB_API_KEY" --header 'Content-Type: application/json' \
  --data '{"queries":{"studies":{"entity":"studies","predicates":[{"field":"sid","value":"PKDB01110"}]}},"concise":true}' \
  --output "$result_dir/dataset.zip"
printf 'Saved API responses and dataset.zip in %s\n' "$result_dir"
