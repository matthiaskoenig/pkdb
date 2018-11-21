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
To build the dev server for local development:
```bash
sudo sysctl -w vm.max_map_count=262144
git clone https://github.com/matthiaskoenig/pkdb.git
cd pkdb
./docker_update.sh
```
To update an existing version use
```bash
./docker_update.sh
```
To start an existing version use
```bash
docker-compose up
```

## Fill database
The database can be filled via the `setup_database.py` and `upload_studies.py` scripts using curated data folders.
The curated data is currently not made available, but only accessible via the REST API.

First change in `/pkdb/pkdb_app/.env` the endpoints and passwords to the correct values by setting the environment
variables `PKDB_API_BASE` and `PKDB_DEFAULT_PASSWORD`.

```
(pkdb) ./fill_database.sh
docker-compose run --rm web ./manage.py search_index --rebuild -f
```

## Accessing backend
PKDB can than be accessed via the locally running server at  
`http://localhost:8000/api/v1/`.  

To run commands inside the docker container use
```bash
docker-compose run --rm web [command]
```
For instance create a superuser to login to the admin:
```bash
docker-compose run --rm web ./manage.py createsuperuser
```
or to run migrations
```bash
docker-compose run --rm web python manage.py makemigrations
```

## Python (Virtual Environment)
Setting up a virtual environment to interact with the data base via python
```
mkvirtualenv pkdb --python=python3.6
(pkdb) pip install -r requirements.txt
(pkdb) pip install -e .
```
add your virtual environment to jupyter kernels:
```
(pkdb) ipython kernel install --user --name=pkdb
``` 

## Frontend 
Documentation of the `vue.js` frontend is available in
./pkdb_client/README.md


## Elastic Search 
Elastic Search engine is running on `0.0.0.0:9200` but is also reachable via django views.
General examples can be found here: https://django-elasticsearch-dsl-drf.readthedocs.io/en/0.16.2/basic_usage_examples.html

query examples:
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