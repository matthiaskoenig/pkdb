#!/usr/bin/env bash
########################################################
# Setup database and uploads studies
#   set -a && source .env.local && ./fill_database.sh
########################################################

python backend/pkdb_app/data_management/upload_studies.py
