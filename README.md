[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1407035.svg)](https://doi.org/10.5281/zenodo.1406979)
[![Build Status](https://travis-ci.org/matthiaskoenig/pkdb.svg?branch=develop)](https://travis-ci.org/matthiaskoenig/pkdb)

# PKDB - Pharmacokinetics database

<b><a href="https://orcid.org/0000-0002-4588-4925" title="0000-0002-4588-4925"><img src="./docs/images/orcid.png" height="15"/></a> Jan Grzegorzewski</b>
and
<b><a href="https://orcid.org/0000-0003-1725-179X" title="https://orcid.org/0000-0003-1725-179X"><img src="./docs/images/orcid.png" height="15" width="15"/></a> Matthias König</b>

Database and web interface for storing (pharmaco-)kinetics information including
- study data (publication data)
- trial design
- subjects information
- interventions
- dosing schemas
- pharmacokinetics parameters 
- timecourse data

<img src="./docs/images/data_extraction.png" width="600"/>
Figure 1: Overview over data extraction and curation work flow.

# Installation
The database with backend and frontend is available as docker container for local installation.

## Requirements
- [Docker](https://docs.docker.com/docker-for-mac/install/)
- Python3.6

## Build docker container
System settings for elasticsearch:
```
sudo sysctl -w vm.max_map_count=262144
```
To set the value permanently change the value in 
```
/etc/sysctl.conf
```

To build the dev server for local development:
```bash
git clone https://github.com/matthiaskoenig/pkdb.git
cd pkdb
set -a && source .env.local && docker-compose up
```
To update an existing version use
```bash
set -a && source .env.local && docker-compose up --build

To see the running containers use
```
watch docker containters ls
```
To get access to the container logs use `docker container logs`, e.g., to see the
django backend logs use
```
docker container logs pkdb_backend_1 
```

## Fill database
The database can be filled via the `fill_database.sh` script.
```
(pkdb) set -a && source .env.local && ./fill_database.sh
docker-compose run --rm backend ./manage.py search_index --rebuild -f
```

## Accessing backend
PKDB can than be accessed via the locally running server at  
```
http://localhost:8000/api/v1/
```
The API documentation is available via
```
http://localhost:1234/api
```

To run commands inside the docker container use
```bash
docker-compose run --rm backend [command]
```
or to run migrations
```bash
docker-compose run --rm backend python manage.py makemigrations
```

## Python (Virtual Environment)
Setting up a virtual environment to interact with the data base via python
```
cd backend
mkvirtualenv pkdb --python=python3.6
(pkdb) pip install -r requirements.txt
(pkdb) pip install -e .
```
add your virtual environment to jupyter kernels:
```
(pkdb) ipython kernel install --user --name=pkdb
``` 

## Vue Frontend 
Documentation of the `vue.js` frontend is available in
./pkdb_client/README.md
The frontend is running on
```
localhost

## Elastic Search 
Elastic Search engine is running on `localhost:9200` but is also reachable via django views.
General examples can be found here: https://django-elasticsearch-dsl-drf.readthedocs.io/en/0.16.2/basic_usage_examples.html

Query examples:
```
http://localhost:8000/api/v1/comments_elastic/?user_lastname=K%C3%B6nig
http://localhost:8000/api/v1/characteristica_elastic/?group_pk=5&final=true
http://localhost:8000/api/v1/characteristica_elastic/?search=group_name:female&final=true
http://localhost:8000/api/v1/substances_elastic/?search:name=cod
http://localhost:8000/api/v1/substances_elastic/?search=cod 
http://localhost:8000/api/v1/substances_elastic/?ids=1__2__3 
http://localhost:8000/api/v1/substances_elastic/?ids=1__2__3&ordering=-name
http://localhost:8000/api/v1/substances_elastic/?name=caffeine&name=acetaminophen
```

Suggest example:
```
http://localhost:8000/api/v1/substances_elastic/suggest/?search:name=cod
```

rebuild index:
```
docker-compose run --rm web ./manage.py search_index --rebuild -f
```
 
## Read 
&copy; 2017-2018 Jan Grzegorzewski & Matthias König.