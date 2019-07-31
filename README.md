[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1406979.svg)](https://doi.org/10.5281/zenodo.1406979)
[![License (LGPL version 3)](https://img.shields.io/badge/license-LGPLv3.0-blue.svg?style=flat-square)](http://opensource.org/licenses/LGPL-3.0)

<b><a href="https://orcid.org/0000-0002-4588-4925" title="0000-0002-4588-4925"><img src="./docs/images/orcid.png" height="15"/></a> Jan Grzegorzewski</b>
and
<b><a href="https://orcid.org/0000-0003-1725-179X" title="https://orcid.org/0000-0003-1725-179X"><img src="./docs/images/orcid.png" height="15" width="15"/></a> Matthias König</b>

# PK-DB - a pharmacokinetics database

* [Overview](https://github.com/matthiaskoenig/pkdb#overview)
* [How to cite](https://github.com/matthiaskoenig/pkdb#how-to-cite)
* [License](https://github.com/matthiaskoenig/pkdb#license)
* [Funding](https://github.com/matthiaskoenig/pkdb#funding)
* [Installation](https://github.com/matthiaskoenig/pkdb#installation)
* [REST API](https://github.com/matthiaskoenig/pkdb#rest-api)
* [Docker interaction](https://github.com/matthiaskoenig/pkdb#docker-interaction)

## Overview
[[^]](https://github.com/matthiaskoenig/pkdb#pk-db---a-pharmacokinetics-database)
[PK-DB](https://pk-db.com) is a database and web interface for pharmacokinetics data and information from clinical trials 
as well as pre-clinical research. PK-DB allows to curate pharmacokinetics data integrated with the 
corresponding meta-information 
- characteristics of studied patient collectives and individuals (age, bodyweight, smoking status, ...) 
- applied interventions (e.g., dosing, substance, route of application)
- measured pharmacokinetics time courses and pharmacokinetics parameters (e.g., clearance, half-life, ...). 

Important features are 
- the representation of experimental errors and variation
- the representation and normalisation of units
- annotation of information to biological ontologies
- calculation of pharmacokinetics information from time courses (apparent clearance, half-life, ...)
- a workflow for collaborative data curation
- strong validation rules on data, and simple access via a REST API

PK-DB is available at https://pk-db.com

## License
[[^]](https://github.com/matthiaskoenig/pkdb#pk-db---a-pharmacokinetics-database)
PK-DB code and documentation is licensed as
* Source Code: [LGPLv3](http://opensource.org/licenses/LGPL-3.0)
* Documentation: [CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/)

## Funding
[[^]](https://github.com/matthiaskoenig/pkdb#pk-db---a-pharmacokinetics-database)
Jan Grzegorzewski and Matthias König are supported by the Federal Ministry of Education and Research (BMBF, Germany)
within the research network Systems Medicine of the Liver ([LiSyM](http://www.lisym.org/), grant number 031L0054).

## How to cite
[[^]](https://github.com/matthiaskoenig/pkdb#pk-db---a-pharmacokinetics-database)
If you use PK-DB or data from PK-DB cite 

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1406979.svg)](https://doi.org/10.5281/zenodo.1406979)

## Installation
[[^]](https://github.com/matthiaskoenig/pkdb#pk-db---a-pharmacokinetics-database)
PK-DB is deployed via `docker` and `docker-compose`. 

### Requirements
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
### Start development server
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


## REST API
[[^]](https://github.com/matthiaskoenig/pkdb#pk-db---a-pharmacokinetics-database)
PKDB provides a REST API which allows simple interaction with the database and easy access of data.
An overview over the REST endpoints is provided at [`http://localhost:8000/api/v1/`](http://localhost:8000/api/v1/).

### Query examples
The REST API supports elastisearch queries, with syntax examples  
available [here](https://django-elasticsearch-dsl-drf.readthedocs.io/en/latest/basic_usage_examples.html)
* http://localhost:8000/api/v1/comments_elastic/?user_lastname=K%C3%B6nig
* http://localhost:8000/api/v1/characteristica_elastic/?group_pk=5&final=true
* http://localhost:8000/api/v1/characteristica_elastic/?search=group_name:female&final=true
* http://localhost:8000/api/v1/substances_elastic/?search:name=cod
* http://localhost:8000/api/v1/substances_elastic/?search=cod 
* http://localhost:8000/api/v1/substances_elastic/?ids=1__2__3 
* http://localhost:8000/api/v1/substances_elastic/?ids=1__2__3&ordering=-name
* http://localhost:8000/api/v1/substances_elastic/?name=caffeine&name=acetaminophen

### Suggestion example
In addition suggestion queries are possible
* http://localhost:8000/api/v1/substances_elastic/suggest/?search:name=cod

## Docker interaction
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

&copy; 2017-2019 Jan Grzegorzewski & Matthias König; https://livermetabolism.com.
