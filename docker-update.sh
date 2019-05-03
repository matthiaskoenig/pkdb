#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Update docker containers
#
# Execute via
#     set -a && source .env
#     set -a && source .env.local (develop)
#     ./docker-update.sh
# -----------------------------------------------------------------------------
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
: "${PKDB_DOCKER_COMPOSE_YAML:?The PKDB environment variable must be exported.}"

sudo echo "Update docker containers"

# shut down all containers
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML down

# make sure containers are removed (if not running)
docker container rm -f pkdb_setup_root_1 pkdb_migration_1 pkdb_frontend_1 pkdb_backend_1 pkdb_postgres_1 pkdb_elasticsearch_1

# make sure images are removed
docker image rm -f pkdb_frontend:latest
docker image rm -f pkdb_backend:latest
docker image rm -f pkdb_migration:latest
docker image rm -f pkdb_setup_root:latest

# cleanup all dangling images, containers, volumes and networks
docker system prune --force

# build and start containers
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML up --build --detach

echo "*** Running containers ***"
docker container ls