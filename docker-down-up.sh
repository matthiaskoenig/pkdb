#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Brings all containers down and up again
# -----------------------------------------------------------------------------

: "${PKDB_DOCKER_COMPOSE_YAML:?The 'PKDB_*' environment variables must be exported.}"
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML down && docker-compose -f $PKDB_DOCKER_COMPOSE_YAML up --detach