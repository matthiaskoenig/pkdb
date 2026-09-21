#!/usr/bin/env bash
#
# Apply the repository policies of pkdb: the merge settings of the
# repository and the rulesets in this directory. The script is idempotent, i.e.,
# a ruleset which already exists is updated instead of added a second time, so
# it can be run again after every change of the json files.
#
# The file name of a ruleset has to match the "name" in the json. A ruleset which
# is removed from this directory stays on the repository, delete it with
# `gh api -X DELETE repos/<owner>/<repo>/rulesets/<id>`.
#
# Requires the github cli (https://cli.github.com) authenticated as a user with
# admin permission on the repository:
#
#   gh auth login
#   .github/rulesets/apply.sh [owner/repo]
#
set -euo pipefail

REPO="${1:-matthiaskoenig/pkdb}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "repository settings of ${REPO}"
gh api -X PATCH "repos/${REPO}" \
  -F allow_auto_merge=true \
  -F delete_branch_on_merge=true \
  -F allow_update_branch=true \
  -F allow_squash_merge=true \
  -F allow_rebase_merge=true \
  -F allow_merge_commit=false \
  --silent

for path in "${DIR}"/*.json; do
  name="$(basename "${path}" .json)"
  id="$(gh api "repos/${REPO}/rulesets" --jq "map(select(.name == \"${name}\")) | .[0].id // empty")"
  if [[ -n "${id}" ]]; then
    gh api -X PUT "repos/${REPO}/rulesets/${id}" --input "${path}" --silent
    echo "ruleset ${name} updated (${id})"
  else
    id="$(gh api -X POST "repos/${REPO}/rulesets" --input "${path}" --jq .id)"
    echo "ruleset ${name} created (${id})"
  fi
done
