#!/bin/sh

# Migrates the database, uploads staticfiles, and runs the production server


# https://docs.docker.com/compose/startup-order/

/usr/local/bin/python /usr/src/app/manage.py collectstatic --noinput 
# /usr/src/app/wait-for-it.sh postgres:5432 --/usr/local/bin/python /usr/src/app/manage.py makemigrations
# /usr/src/app/wait-for-it.sh postgres:5432 --/usr/local/bin/python /usr/src/app/manage.py migrate
# /usr/src/app/wait-for-it.sh postgres:5432 --/usr/local/bin/python createsuperuser2 --username admin --password $DEFAULT_PASSWORD --email koenigmx@hu-berlin.de --noinput

/usr/local/bin/gunicorn pkdb_app.wsgi:application -w 4 -b :8000

