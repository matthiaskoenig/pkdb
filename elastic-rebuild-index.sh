#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Rebuild elasticsearch index
# -----------------------------------------------------------------------------
: "${PKDB_DOCKER_COMPOSE_YAML:?The PKDB environment variable must be exported.}"
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py search_index --rebuild -f
