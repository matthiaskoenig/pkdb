#!/usr/bin/env bash
########################################################
# Complete update
# set -a && source .env.local && ./docker_update.sh
########################################################
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
sudo echo "Docker update"

# shut down all containers (remove images and volumes)
# remove images and volumes
docker-compose down --volumes --rmi local

# make sure containers are removed (if not running)
docker container rm -f pkdb_setup_root_1 pkdb_migration_1 pkdb_frontend_1 pkdb_backend_1 pkdb_postgres_1 pkdb_elasticsearch_1 

# make sure images are removed
# FIXME: do via queries
docker image rm -f pkdb_frontend:latest
docker image rm -f pkdb_backend:latest
docker image rm -f pkdb_migration:latest
docker image rm -f pkdb_setup_root:latest

# make sure volumes are removed
# FIXME: do via queries
docker volume rm -f pkdb_django_media
docker volume rm -f pkdb_django_static
docker volume rm -f pkdb_elasticsearch_data
docker volume rm -f pkdb_node_modules
docker volume rm -f pkdb_postgres_data
docker volume rm -f pkdb_vue_dist

# cleanup all dangling images, containers, volumes and networks
docker system prune --force

# remove migrations
cd $DIR
sudo find . -maxdepth 5 -path "*/migrations/*.py" -not -name "__init__.py" -delete
sudo find . -maxdepth 5 -path "*/migrations/*.pyc" -delete


# remove media and static files
sudo rm -rf media
sudo rm -rf static

# start containers
set -a && source .env && docker-compose -f docker-compose-deploy.yml up --detach
