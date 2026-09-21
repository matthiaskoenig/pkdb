# Installation

PK-DB is deployed via `docker` and `docker compose`; there is no PyPI package. See [Deployment](deployment.md) for the compose stacks, the operational scripts and the `PKDB_*` environment variables in detail.

## Requirements

- [`docker`](https://docs.docker.com/engine/install/) with the `compose` plugin

Elasticsearch needs a higher `vm.max_map_count` than the linux default:

```bash
sudo sysctl -w vm.max_map_count=262144
```

To make this persistent, set `vm.max_map_count` in `/etc/sysctl.conf`.

## Start the development server

```bash
# clone the repository
git clone https://github.com/matthiaskoenig/pkdb.git
cd pkdb

# set the environment variables for the develop stack
set -a && source .env.local

# build and start postgres, elasticsearch, backend and frontend;
# resets the database, the search index and the migrations, see docs/deployment.md
./docker-purge.sh
```

Check that the containers are running:

```bash
docker container ls
```

which lists the current containers, e.g.:

```
NAMES                   IMAGE                 PORTS
pkdb-backend-1          pkdb-backend:latest   0.0.0.0:8000->8000/tcp
pkdb-frontend-1         pkdb-frontend:latest  0.0.0.0:8081->8080/tcp
pkdb-elasticsearch-1    elasticsearch:7.9.2   0.0.0.0:9123->9200/tcp
pkdb-postgres-1         postgres:18.0         0.0.0.0:5433->5432/tcp
```

The develop instance of PK-DB is then reachable at:

- frontend: [http://localhost:8081](http://localhost:8081)
- backend: [http://localhost:8000](http://localhost:8000), with the REST API at [http://localhost:8000/api/v1/](http://localhost:8000/api/v1/)

### Fill the database

Due to copyright, licensing and privacy issues this repository does not contain any data. All data is managed via the separate repository [pkdb_data](https://github.com/matthiaskoenig/pkdb_data), which also holds the curation scripts and curation workflows.

If you are interested in curating data or contributing data please contact us at [https://livermetabolism.com](https://livermetabolism.com).

## Working with the containers

### Interactive mode

```bash
./docker-interactive.sh
```

Restarts the stack in the foreground, i.e. the combined container logs stream to the console.

### Container logs

```bash
docker container logs pkdb-backend-1
```

### Run a command in a container

```bash
docker compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend [command]
```

for example to run the migrations:

```bash
docker compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend python manage.py makemigrations
```

### Authentication data

Dump the authentication fixtures:

```bash
docker compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py dumpdata auth --indent 2 > ./backend/pkdb_app/fixtures/auth.json
docker compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py dumpdata users --indent 2 > ./backend/pkdb_app/fixtures/users.json
docker compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py dumpdata rest_email_auth --indent 2 > ./backend/pkdb_app/fixtures/rest_email_auth.json
```

Restore them:

```bash
docker compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py loaddata auth pkdb_app/fixtures/auth.json
docker compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py loaddata users pkdb_app/fixtures/users.json
docker compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py loaddata rest_email_auth pkdb_app/fixtures/rest_email_auth.json
```

## Contributing to the backend

To work on the backend itself, i.e. without going through the docker image, see [Development](development.md).
