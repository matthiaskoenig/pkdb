# PKDB - Pharmacokinetics database

<b><a href="https://orcid.org/0000-0002-4588-4925" title="0000-0002-4588-4925"><img src="./docs/images/logos/orcid.png" height="15"/></a> Jan Grzegorzewski</b>
and
<b><a href="https://orcid.org/0000-0003-1725-179X" title="https://orcid.org/0000-0003-1725-179X"><img src="./docs/images/orcid.png" height="15" width="15"/></a> Matthias König</b>

Database for storing pharmacokinetics information.
This includes
- study data (publication data)
- trial design
- subjects information
- interventions
- dosing schemas
- pharmacokinetics parameters 
- timecourse data


<img src="./docs/images/data_extraction.png" />

## pharmacokinetics
Pharmacokinetics data is hereby a subclass of experimental data. 
These are the numerical values which are normally reported in publications.
The form can vary (mean, median) and also the error terms associated with the values (SD, SE, CV, Range). 
In addition the number of subjects is important as well (n), to be able to convert between different error
measurments.

# Prerequisites

- [Docker](https://docs.docker.com/docker-for-mac/install/)  

# Setup & Installation
## Python3.6
### Ubuntu 14.04 and 16.04
```
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install python3.6
sudo apt-get install python3.6-dev

```
### Ubuntu 16.10 and 17.04
```
sudo apt-get update
sudo apt-get install python3.6
sudo apt-get install python3.6-dev

```
## Virtual Env
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

&copy; 2018 Jan Grzegorzewski & Matthias König.