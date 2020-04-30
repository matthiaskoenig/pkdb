# -----------------------------------------------------------------------------
# Automatic deployment develop.pk-db.com
# -----------------------------------------------------------------------------
# sudo source deploy.sh
# - !necessary to have cached git credentials for pulling updates
# - !virtualenv must be updated manually

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
# TODO backup

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
$HOME/envs/pkdb_data/bin/upload_nodes
$HOME/envs/pkdb_data/bin/upload_studies





