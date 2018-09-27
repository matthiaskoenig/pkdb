[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1407035.svg)](https://doi.org/10.5281/zenodo.1407035)
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
git clone https://github.com/matthiaskoenig/pkdb.git
cd pkdb
docker-compose up --build
```
To update an existing version use
```bash
docker-compose down
./remove_migrations.sh
docker-compose up --build
```
To run an existing version use
```bash
docker-compose up
```

PKDB can than be accessed via the locally running server at  
http://localhost:8000/api/v1/  

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

## Fill database
The database can be filled via the `fill_database` scripts using curated data folders.
The curated data is currently not made available, but only accessible via the REST API.
```
(pkdb) python ./pkdb_app/data_management/fill_database.py
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


&copy; 2017-2018 Jan Grzegorzewski & Matthias König.