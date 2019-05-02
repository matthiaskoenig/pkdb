# -----------------------------------------------------------------------------
# PK-DB backup
# -----------------------------------------------------------------------------
# TODO: run via cron job
# TODO: check that backup can be restored
#
# usage:
#	./backup-deploy.sh
# -----------------------------------------------------------------------------
: "${PKDB_DOCKER_COMPOSE_YAML:?The PKDB environment variable must be exported.}"

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

echo "-------------------------------"
echo "Backup PKDB docker volumes"
echo "-------------------------------"
cd /var/git/pkdb

# create directory for backup
BACKUP_DIR=/var/backups/pkdb/$(date '+%F')
sudo mkdir -p $BACKUP_DIR
sudo chown -R mkoenig:mkoenig $BACKUP_DIR
echo "Backup to" $BACKUP_DIR


echo *** backup django volumes***
cd $BACKUP_DIR
docker run --rm --volumes-from pkdb_backend_1 -v $BACKUP_DIR:/backup ubuntu tar cvzf /backup/django_media.tar.gz /media
docker run --rm --volumes-from pkdb_backend_1 -v $BACKUP_DIR:/backup ubuntu tar cvzf /backup/django_static.tar.gz /static
docker run --rm --volumes-from pkdb_postgres_1 -v $BACKUP_DIR:/backup ubuntu tar cvzf /backup/postgres_data.tar.gz /var/lib/postgresql/data
docker run --rm --volumes-from pkdb_elasticsearch_1 -v $BACKUP_DIR:/backup ubuntu tar cvzf /backup/elasticsearch_data.tar.gz /usr/share/elasticsearch/data
docker run --rm --volumes-from pkdb_frontend_1 -v $BACKUP_DIR:/backup ubuntu tar cvzf /backup/vue_dist.tar.gz /vue


echo "----------------------------"
echo "Dump PKDB database"
echo "----------------------------"
# sudo -u postgres pg_dump pkdb > $DIR/pkdb_dump.psql
docker exec -u $PKDB_DB_USER pkdb_postgres1 pg_dump -Fc $PKDB_DB_NAME > db.dump

cd $DIR
