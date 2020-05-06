# -----------------------------------------------------------------------------
# PK-DB backup
# -----------------------------------------------------------------------------
# TODO: check that backup can be restored (restore script)
#
#  crontab -e
#    55 23 * * * /var/git/pkdb/backup.sh
#
# usage:
#	./backup-deploy.sh
# -----------------------------------------------------------------------------
: "${PKDB_DOCKER_COMPOSE_YAML:?The PKDB environment variable must be exported.}"

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

echo "-------------------------------"
echo "Create backup directory"
echo "-------------------------------"

# create directory for backup
BACKUP_DIR=/var/backups/pkdb/$(date '+%F')
# sudo mkdir -p $BACKUP_DIR
# sudo chown -R mkoenig:mkoenig $BACKUP_DIR
echo "Backup to" $BACKUP_DIR
cd $BACKUP_DIR

echo "-------------------------------"
echo "Backup PKDB docker volumes"
echo "-------------------------------"

echo "*** django_media ***"
docker run --rm --volumes-from pkdb_backend_1 -v $BACKUP_DIR:/backup ubuntu tar cvzf /backup/django_media.tar.gz /media

echo "*** django_static ***"
docker run --rm --volumes-from pkdb_backend_1 -v $BACKUP_DIR:/backup ubuntu tar cvzf /backup/django_static.tar.gz /static

echo "*** postgres_data ***"
docker run --rm --volumes-from pkdb_postgres_1 -v $BACKUP_DIR:/backup ubuntu tar cvzf /backup/postgres_data.tar.gz /var/lib/postgresql/data

echo "*** elasticsearch_data ***"
docker run --rm --volumes-from pkdb_elasticsearch_1 -v $BACKUP_DIR:/backup ubuntu tar cvzf /backup/elasticsearch_data.tar.gz /usr/share/elasticsearch/data

echo "*** vue_dist ***"
docker run --rm --volumes-from pkdb_frontend_1 -v $BACKUP_DIR:/backup ubuntu tar cvzf /backup/vue_dist.tar.gz /vue


echo "----------------------------"
echo "Dump PKDB database"
echo "----------------------------"
docker exec -u $PKDB_DB_USER pkdb_postgres_1 pg_dump -Fc $PKDB_DB_NAME > pkdb.dump
if [ -e $BACKUP_DIR/pkdb.dump ]
then
    echo "SUCCESS $BACKUP_DIR/pkdb.dump"
else
    echo "! FAILURE $BACKUP_DIR/pkdb.dump !"
fi