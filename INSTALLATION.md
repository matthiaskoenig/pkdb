
# Installation
PK-DB is deployed via `docker` and `docker-compose`. 

## Requirements
To setup the development server 
the following minimal requirements must be fulfilled
- `docker`
- `docker-compose`
- `Python3.6`

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
This setups a clean database and clean volumes and starts the containers for `pkdb_backend`, `pkdb_frontend`, `elasticsearch` and `postgres`.
You can check that all the containers are running via
```bash
docker container ls
```
which lists the current containers
```
CONTAINER ID        IMAGE                 COMMAND                  CREATED             STATUS              PORTS                              NAMES
bc7f9204468f        pkdb_backend          "bash -c '/usr/local…"   27 hours ago        Up 18 hours         0.0.0.0:8000->8000/tcp             pkdb_backend_1
17b8d243e956        pkdb_frontend         "/bin/sh -c 'npm run…"   27 hours ago        Up 18 hours         0.0.0.0:8080->8080/tcp             pkdb_frontend_1
7730c6fe2210        elasticsearch:6.8.1   "/usr/local/bin/dock…"   27 hours ago        Up 18 hours         9300/tcp, 0.0.0.0:9123->9200/tcp   pkdb_elasticsearch_1
e880fbb0f349        postgres:11.4         "docker-entrypoint.s…"   27 hours ago        Up 18 hours         0.0.0.0:5433->5432/tcp             pkdb_postgres_1
```
The locally running develop version of PK-DB can now be accessed via the web browser from
- frontend: http://localhost:8080
- backend: http://localhost:8000

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
docker-compose run --rm backend [command]
```
or to run migrations
```bash
docker-compose run --rm backend python manage.py makemigrations
```

### Authentication data
The following examples show how to dump and restore the authentication data.

Dump authentication data
```bash
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py  dumpdata auth  --indent 2 > ./backend/pkdb_app/fixtures/auth.json
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py  dumpdata users  --indent 2 > ./backend/pkdb_app/fixtures/users.json
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py  dumpdata rest_email_auth  --indent 2 > ./backend/pkdb_app/fixtures/rest_email_auth.json
```

Restore authentication data
```bash
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py  loaddata auth pkdb_app/fixtures/auth.json
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py  loaddata users pkdb_app/fixtures/users.json
docker-compose -f $PKDB_DOCKER_COMPOSE_YAML run --rm backend ./manage.py  loaddata rest_email_auth pkdb_app/fixtures/rest_email_auth.json
```
