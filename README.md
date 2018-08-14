# PKDB - Pharmacokinetics database

<b><a href="https://orcid.org/0000-0002-4588-4925" title="0000-0002-4588-4925"><img src="./docs/images/orcid.png" height="15"/></a> Jan Grzegorzewski</b>
and
<b><a href="https://orcid.org/0000-0003-1725-179X" title="https://orcid.org/0000-0003-1725-179X"><img src="./docs/images/orcid.png" height="15" width="15"/></a> Matthias König</b>

Database and web interface for storing pharmacokinetics information including
- study data (publication data)
- trial design
- subjects information
- interventions
- dosing schemas
- pharmacokinetics parameters 
- timecourse data

<img src="./docs/images/data_extraction.png" width="600"/>
Figure 1: Overview over data extraction.

## Data model
Pharmacokinetics data is a special type of experimental data.
Pharmacokinetics data like clearance, halflife, ... (with units and error measurements) are either directly reported in publications
or can be calculated from time course data.
* the reported value (mean, median) as well as the error terms associated with the values (SD, SE, CV, Range) can vary
* Important information is the number of subjects (n) underlying the measurement, which is required to convert between different error
measurements.

# Setup & Installation
## Requirements
- [Docker](https://docs.docker.com/docker-for-mac/install/)
- Python3.6

## Virtual Environment
Setting up a virtual environment
```
mkvirtualenv pkdb --python=python3.6
(pkdb) pip install -r requirements.txt
```
add your virtual environment to jupyter kernels:
```
(pkdb) ipython kernel install --user --name=pkdb
``` 
# Initialize the project

Start the dev server for local development:
```bash
docker-compose up
```

Create a superuser to login to the admin:
```bash
docker-compose run --rm web ./manage.py createsuperuser
```

# Update after code change
```
# reset migrations
sudo find . -path "*/migrations/*.py" -not -name "__init__.py" -delete && sudo find . -path "*/migrations/*.pyc"  -delete
sudo rm -r media/study/

# rebuild container
docker-compose down
docker-compose up --build
```


# Fill database
From console use the following
```
workon pkdb
(pkdb) pip install -r requirements.txt --upgrade
(pkdb) python ./pkdb_app/data_management/fill_database.py
```


# Connect database pycharm
```
DataSource -> postgres
```
Use port defined in `docker-compose.yml` (5433), database name and password in `docker-compose.yml`

# Local Development
Start the dev server for local development:

```bash
docker-compose up
```
Run a command inside the docker container:

```bash
docker-compose run --rm web [command]
```
Example:

```
 docker-compose run --rm web python manage.py makemigrations
```

----
# Client
check out ./client/README.md.
## Requirements
- node.js
- npm
- vue.js




&copy; 2018 Jan Grzegorzewski & Matthias König.