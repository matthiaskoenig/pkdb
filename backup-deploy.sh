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

echo "-------------------------------"
echo "Backup PKDB docker volumes"
echo "-------------------------------"
cd /var/git/pkdb

# create directory for backup
BACKUP_DIR=/var/backups/pkdb/$(date '+%F')
sudo mkdir -p $DIR
sudo chown -R mkoenig:mkoenig $DIR
echo "Backup to" $BACKUP_DIR


echo *** backup django volumes***
# django_media
#docker run -it --rm -v pkdb_django_media:/volume -v /tmp:/backup pkdb_backend \
#    tar -cvzf $BACKUP_DIR/django_media.tar.gz -C /volume ./

docker run --rm --volumes-from pkdb_django_media -v $BACKUP_DIR:/backup ubuntu tar cvzf /backup/django_media.tar.gz /

# django_static
#docker run -it --rm -v pkdb_django_static:/volume -v /tmp:/backup pkdb_backend \
#    tar -cvzf $BACKUP_DIR/django_static.tar.gz -C /volume ./


# elasticsearch_data

# postgres_data

# vue_dist


echo "----------------------------"
echo "Dump PKDB database"
echo "----------------------------"
# FIXME:
# sudo -u postgres pg_dump pkdb > $DIR/pkdb_dump.psql

