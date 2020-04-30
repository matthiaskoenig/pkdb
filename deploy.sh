# -----------------------------------------------------------------------------
# Automatic deployment develop.pk-db.com
# -----------------------------------------------------------------------------
# sudo ./deploy.sh 2>&1 | tee ./deploy.logsudo ./deploy.sh 2>&1 | tee ./deploy.log
# - !necessary to have cached credentials for pulling updates
# FIXME: run in cronjob (sudo cron)
# FIXME: logging of all output for debugging
# FIXME: logging of study uploads and errors for dayly report
#
# -----------------------------------------------------------------------------

echo "-------------------------"
echo "UPDATE PKDB"
echo "-------------------------"
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd $DIR
echo $DIR
# pull latest changes
git pull
# set environment variables
set -a && source .env.production
# deploy
./docker-purge.sh

# create info nodes & upload study (from server locally)
cd ../pkdb_data
git pull

# FIXME: how to set environment variables in shell
set -a && source .env.develop

echo "-------------------------"
echo "UPLOAD DATA"
echo "-------------------------"
# activate environment on server
source $HOME/envs/pkdb_data/bin/activate
pip install -e . --upgrade
upload_nodes
upload_studies





