
# Installation
PK-DB is deployed via `docker` and `docker compose`.

## Requirements
To setup the development server
the following minimal requirements must be fulfilled
- `docker`

For elasticsearch the following system settings are required
```
sudo sysctl -w vm.max_map_count=262144
```
To set `vm.max_map_count` persistently change the value in
```
/etc/sysctl.conf
```

## Start development server
To start the local development server
```bash
# clone or pull the latest code
git clone https://github.com/matthiaskoenig/pkdb.git
cd pkdb
git pull

# set environment variables
set -a && source .env.local

# create/rebuild all docker containers
./docker-purge.sh
```
The script setups a clean database and clean volumes and starts the containers for `pkdb_backend`, `pkdb_frontend`, `elasticsearch` and `postgres`.
You can check that all the containers are running via
```bash
docker container ls
```
which lists the current containers
```
CONTAINER ID   IMAGE                 COMMAND                  CREATED             STATUS                  PORTS                                                   NAMES
611a240db6e6   pkdb-backend          "bash -c '/usr/local…"   10 seconds ago      Up Less than a second   0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp             pkdb-backend-1
0cb18ee77b45   pkdb-frontend         "docker-entrypoint.s…"   10 seconds ago      Up Less than a second   0.0.0.0:8081->8080/tcp, [::]:8081->8080/tcp             pkdb-frontend-1
0843b94ec388   elasticsearch:7.9.2   "/tini -- /usr/local…"   About an hour ago   Up About an hour        9300/tcp, 0.0.0.0:9123->9200/tcp, [::]:9123->9200/tcp   pkdb-elasticsearch-1
cc5427445bcd   postgres:13.0         "docker-entrypoint.s…"   About an hour ago   Up About an hour        0.0.0.0:5433->5432/tcp, [::]:5433->5432/tcp             pkdb-postgres-1
```
The locally running develop version of PK-DB can now be accessed via the web browser from
- frontend: http://localhost:8081
- backend: http://localhost:8000 with endpoints at http://localhost:8000/api/v1/

### Fill database
Due to copyright, licensing and privacy issues this repository does not contain any data.
All data is managed via a separate private repository at https://github.com/matthiaskoenig/pkdb_data.
This also includes the curation scripts and curation workflows.

If you are interested in curating data or contributing data please contact us at https://livermetabolism.com.

# Docker
[[^]](https://github.com/matthiaskoenig/pkdb#pk-db---a-pharmacokinetics-database)
In the following typical examples to interact with the PK-DB docker containers are provided.

### Check running containers
To check the running containers use
```bash
watch docker container ls
```

### Interactive container mode
```bash
./docker-interactive.sh
```

### Container logs
To get access to individual container logs use `docker container logs <container>`. For instance to check the
django backend logs use
```bash
docker container logs pkdb_backend_1
```

### Run command in container
To run commands inside the docker container use
```bash
docker compose run --rm backend [command]
```
or to run migrations
```bash
docker compose run --rm backend python manage.py makemigrations
```

### Authentication data
The following examples show how to dump and restore the authentication data.

Dump authentication data
```bash
docker compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py  dumpdata auth  --indent 2 > ./backend/pkdb_app/fixtures/auth.json
docker compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py  dumpdata users  --indent 2 > ./backend/pkdb_app/fixtures/users.json
docker compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py  dumpdata rest_email_auth  --indent 2 > ./backend/pkdb_app/fixtures/rest_email_auth.json
```

Restore authentication data
```bash
docker compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py  loaddata auth pkdb_app/fixtures/auth.json
docker compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py  loaddata users pkdb_app/fixtures/users.json
docker compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py  loaddata rest_email_auth pkdb_app/fixtures/rest_email_auth.json
```
