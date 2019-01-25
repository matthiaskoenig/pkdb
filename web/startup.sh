#!/bin/sh

# Migrates the database, uploads staticfiles, and runs the production server


https://docs.docker.com/compose/startup-order/
# FIXME: requires database
# python ./manage.py makemigrations
# python ./manage.py migrate
# python ./manage.py createsuperuser2 --username admin --password $DEFAULT_PASSWORD --email koenigmx@hu-berlin.de --noinput

python ./manage.py collectstatic --noinput


/usr/local/bin/gunicorn docker_django.wsgi:application -w 4 -b :8000