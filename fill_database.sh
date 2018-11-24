#!/usr/bin/env bash
########################################################
# Setups database and uploads studies
########################################################
# execute within virtualenv (pkdb)
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

export PKDB_API_BASE="http://0.0.0.0:8000"
export PKDB_DEFAULT_PASSWORD="pkdb"
export PKDB_EMAIL_HOST_USER=""
export PKDB_EMAIL_HOST_PASSWORD=""

python pkdb_app/data_management/setup_database.py
python pkdb_app/data_management/upload_studies.py

docker-compose run --rm web ./manage.py search_index --rebuild -f


