# -----------------------------------------------------------------------------
# Automatic deployment develop.pk-db.com
# -----------------------------------------------------------------------------
# - !necessary to have cached credentials for pulling updates
# FIXME: run in cronjob (sudo cron)
# FIXME: logging of all output for debugging
# FIXME: logging of study uploads and errors for dayly report
#
# -----------------------------------------------------------------------------
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd $DIR
# pull latest changes
git pull
# set environment variables
set -a && source .env.production
# deploy
./docker-purge.sh

# create info nodes & upload study (from server locally)
cd ../pkdb_data
git pull
set -a && source .env.develop
workon pkdb_data
pip install -e . --upgrade
upload_nodes
upload_studies





