#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Complete purge of all containers and images !
#
# Execute via setting environment variables
#     set -a && source .env
#     set -a && source .env.local (develop)
#     ./docker-purge.sh
# -----------------------------------------------------------------------------
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
: "${PKDB_DOCKER_COMPOSE_YAML:?The PKDB environment variable must be exported.}"

sudo echo "Purging database and all docker containers, volumes, images ($PKDB_DOCKER_COMPOSE_YAML)?"
#FIXME: add argument to skip question
#read -p "Are you sure [y/N]? " -n 1 -r
#echo    # (optional) move to a new line
#if [[ ! $REPLY =~ ^[Yy]$ ]]
#then
#    exit 1
#fi

# shut down all containers (remove images and volumes)
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML down --volumes --rmi local

# make sure containers are removed (if not running)
docker container rm -f pkdb_frontend_1
docker container rm -f pkdb_backend_1
docker container rm -f pkdb_postgres_1
docker container rm -f pkdb_elasticsearch_1
docker container rm -f pkdb_nginx_1

# make sure images are removed
docker image rm -f pkdb_frontend:latest
docker image rm -f pkdb_backend:latest
docker image rm -f pkdb_postgres:latest
docker image rm -f pkdb_elasticsearch:latest
docker image rm -f pkdb_nginx:latest

# make sure volumes are removed
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

# build and start containers
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML build --no-cache
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML up --detach

echo "***Make migrations & collect static ***"
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend bash -c "/usr/local/bin/python manage.py makemigrations && /usr/local/bin/python manage.py migrate && /usr/local/bin/python manage.py collectstatic --noinput "

echo "*** Setup admin user ***"
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend bash -c "/usr/local/bin/python manage.py createsuperuser2 --username admin --password ${PKDB_DEFAULT_PASSWORD} --email koenigmx@hu-berlin.de --noinput"

echo "*** Build elasticsearch index ***"
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py search_index --rebuild -f

echo "*** Running containers ***"
docker container ls