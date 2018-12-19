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
#docker-compose run --rm web ./manage.py search_index --delete -f
#docker-compose run --rm web ./manage.py search_index --create -f
python pkdb_app/data_management/upload_studies.py



