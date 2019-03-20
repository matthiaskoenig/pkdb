#!/usr/bin/env bash
########################################################
# Setup database and uploads studies
#   set -a && source .env.local && ./fill_database.sh
########################################################
# docker-compose run --rm backend ./manage.py search_index --rebuild -f
docker-compose run --rm backend ./manage.py search_index --create -f
python backend/pkdb_app/data_management/setup_database.py
# python backend/pkdb_app/data_management/upload_studies.py
