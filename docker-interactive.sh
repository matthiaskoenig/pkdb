#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# See container logs on console
# -----------------------------------------------------------------------------
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML down && docker-compose -f $PKDB_DOCKER_COMPOSE_YAML up