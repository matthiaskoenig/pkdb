#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# See container logs on console
# -----------------------------------------------------------------------------
: "${PKDB_DOCKER_COMPOSE_YAML:?The PKDB environment variable must be exported.}"
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML down && docker-compose -f $PKDB_DOCKER_COMPOSE_YAML up