#!/usr/bin/env bash
##################################
# script to update develop server
##################################
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
git pull


# backend update
python manage.py collectstatic
sudo service gunicorn_pkdb restart
sudo service gunicorn_pkdb status

# frontend update



