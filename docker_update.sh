#!/usr/bin/env bash
########################################################
# Updates the docker-compose
########################################################
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )


docker-compose down
sudo ./remove_migrations.sh
docker-compose up --build

# export PKDB_API_BASE="http://0.0.0.0:8000"
# export PKDB_DEFAULT_PASSWORD="pkdb"
# python pkdb_app/data_management/setup_database.py
# python pkdb_app/data_management/upload_studies.py



