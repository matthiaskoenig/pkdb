#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# See container logs on console
# -----------------------------------------------------------------------------
docker-compose -f $DOCKER_COMPOSE_YAML down && docker-compose -f $DOCKER_COMPOSE_YAML up