#!/usr/bin/env bash
#
# Rebuild the elasticsearch index.
docker-compose run --rm backend ./manage.py search_index --rebuild -f
