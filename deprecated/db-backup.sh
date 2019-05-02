# -----------------------------------------------------------------------------
# PK-DB database backup
#
# TODO: update for docker
# TODO: compress backup
# TODO: run via cron job
# TODO: differential backup
# TODO: check that backup can be restored
#
# usage:
#	./db_backup.sh
# -----------------------------------------------------------------------------

exit

echo "-------------------------------"
echo "PKDB database backup"
echo "-------------------------------"
cd /var/git/pkdb

# create directory for backup
DIR=/var/backups/pkdb/$(date '+%F')
sudo mkdir -p $DIR
sudo chown -R mkoenig:mkoenig $DIR
echo "Backup to" $DIR

# backup media & static files
sudo cp -R /var/git/pkdb/media $DIR
sudo cp -R /var/git/pkdb/static $DIR

# backup database
echo "---------------"
echo "Dump database"
echo "---------------"
sudo -u postgres pg_dump pkdb > $DIR/pkdb_dump.psql


# TODO: FIXME (use info from below)

#!/usr/bin/env bash
##################################
# Deploy script for vue frontend
##################################
# also necessary to update the nginx script
##################################
echo "-------------------------------"
echo "Build vue frontend"
echo "-------------------------------"
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd $DIR

DEPLOY_DIR=/var/vue/pkdb
sudo mkdir -p $DEPLOY_DIR

# update dependencies
npm install

# build new version
npm run build

# create directory for backup
BACKUP_DIR=/var/backups/pkdb-vue/$(date '+%F')
sudo mkdir -p $BACKUP_DIR
sudo chown -R mkoenig:mkoenig $BACKUP_DIR
echo "Backup to" $BACKUP_DIR

# backup vue dist
tar -cvzf pkdb-vue.tar.gz $DEPLOY_DIR
sudo mv pkdb-vue.tar.gz $BACKUP_DIR

# deploy the next version (via rsync)
# sudo cp -R $DIR/dist/ $DEPLOY_DIR/
sudo rsync -av --delete $DIR/dist/ $DEPLOY_DIR/
