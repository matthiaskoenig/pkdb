#!/usr/bin/env bash
########################################################
# Setup the database
#
# Deletes old database and recreates all data.
########################################################
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

# delete old migrations
./remove_migrations.sh

# clean setup
python manage.py makemigrations
python manage.py migrate
