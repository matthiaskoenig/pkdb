#!/usr/bin/env bash
# Run the PostgreSQL service of a CI job without durable writes, as compose.test.yaml
# does: fsync, synchronous_commit and full_page_writes are off. A service of GitHub
# Actions takes no command line, so ALTER SYSTEM sets them and a reload applies them.
# Only for a disposable test database, whose data a crash of the server may lose.
#
#     scripts/ci_postgres_without_fsync.sh <container of the PostgreSQL service>
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <container of the PostgreSQL service>" >&2
  exit 2
fi
container=$1

# psql in the container, as the user and on the database that the container created
sql() {
  docker exec "$container" sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -qAt "$@"' psql "$@"
}

sql -c "ALTER SYSTEM SET fsync = off" \
  -c "ALTER SYSTEM SET synchronous_commit = off" \
  -c "ALTER SYSTEM SET full_page_writes = off" \
  -c "SELECT pg_reload_conf()" > /dev/null
# the server applies the reload shortly after
query="SELECT current_setting('fsync'), current_setting('synchronous_commit'), current_setting('full_page_writes')"
for _ in 1 2 3 4 5; do
  if [[ "$(sql -c "$query")" == "off|off|off" ]]; then
    exit 0
  fi
  sleep 1
done
echo "$container still writes durably: fsync|synchronous_commit|full_page_writes = $(sql -c "$query")" >&2
exit 1
