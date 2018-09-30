#!/usr/bin/env bash
########################################################
# Updates the docker-compose
########################################################
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

# delete old migrations
docker-compose down
./remove_migrations.sh
docker-compose up --build

# TODO: setup_database
# TODO: upload_studies
