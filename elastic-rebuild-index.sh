#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Rebuild elasticsearch index
# -----------------------------------------------------------------------------
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py search_index --rebuild -f
