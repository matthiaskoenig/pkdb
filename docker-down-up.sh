#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Brings all containers down and up again
# -----------------------------------------------------------------------------
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML down && docker-compose -f $PKDB_DOCKER_COMPOSE_YAML up --detach