#!/usr/bin/env bash
# Read-only examples. Export writes a local ZIP, not server-side study data.
set -euo pipefail
: "${PKDB_API_KEY:?Set a read-scoped PKDB_API_KEY for dataset export}"
endpoint="${PKDB_ENDPOINT:-http://localhost:18083}"
result_dir="${1:-api-example-results}"
# A study format 1 identifier such as PKDB01110, or <substance>/<name> of a study format 2 study.
study_sid="${2:-PKDB01110}"
mkdir -p "$result_dir"

curl --fail-with-body --silent --show-error --get "$endpoint/api/v2/studies" \
  --header "Authorization: Bearer $PKDB_API_KEY" \
  --data-urlencode 'substance=apixaban' --data-urlencode 'page_size=20' \
  --output "$result_dir/studies.json"

curl --fail-with-body --silent --show-error "$endpoint/api/v2/studies/$study_sid" \
  --header "Authorization: Bearer $PKDB_API_KEY" \
  --output "$result_dir/study.json"

curl --fail-with-body --silent --show-error --get "$endpoint/api/v2/measurements" \
  --header "Authorization: Bearer $PKDB_API_KEY" \
  --data-urlencode "study_sid=$study_sid" \
  --data-urlencode 'measurement_type=concentration' \
  --output "$result_dir/measurements.json"

curl --fail-with-body --silent --show-error "$endpoint/api/v2/query" \
  --header "Authorization: Bearer $PKDB_API_KEY" --header 'Content-Type: application/json' \
  --data "{\"entity\":\"groups\",\"predicates\":[{\"field\":\"study_sid\",\"value\":\"$study_sid\"}]}" \
  --output "$result_dir/groups.json"

curl --fail-with-body --silent --show-error "$endpoint/api/v2/exports" \
  --header "Authorization: Bearer $PKDB_API_KEY" --header 'Content-Type: application/json' \
  --data "{\"queries\":{\"studies\":{\"entity\":\"studies\",\"predicates\":[{\"field\":\"sid\",\"value\":\"$study_sid\"}]}},\"concise\":true}" \
  --output "$result_dir/dataset.zip"
printf 'Saved API responses and dataset.zip in %s\n' "$result_dir"
