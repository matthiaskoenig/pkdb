#!/usr/bin/env bash
########################################################
# Updates the docker-compose
########################################################
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

docker-compose down -v
docker stop $(docker ps -a -q)
docker rm $(docker ps -a -q)

sudo ./remove_migrations.sh
docker-compose up --build



