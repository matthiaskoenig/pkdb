# Deployment

PK-DB runs as a set of `docker compose` services: `postgres`, `elasticsearch`, `backend` (Django) and `frontend` (Vue), with `nginx` added in front for production. The compose files are in the repository root; the scripts that operate on them are as well. Every script requires `PKDB_DOCKER_COMPOSE_YAML` to be set, which selects the compose file to act on, and most of the other `PKDB_*` variables (see [Environment variables](#environment-variables)) are set together by sourcing an env file:

```bash
set -a && source .env.local        # develop, see docker-compose-develop.yml
set -a && source .env.production   # production, see docker-compose-production.yml
```

`.env.local` is tracked in the repository. `.env`, `.env.develop`, `.env.production` and `.env.alpha` are gitignored and exist only on the deployment host.

## Develop stack

`docker-compose-develop.yml` defines:

- **`postgres`** - `postgres:18.0`, published on `5433` (container port `5432`), data in the `postgres_data` volume.
- **`elasticsearch`** - `elasticsearch:7.9.2`, single node, published on `9123` (container port `9200`), data in the `elasticsearch_data` volume.
- **`backend`** - built from `./backend`, `./backend` is bind mounted into the container at `/code`, environment from `.env.local`, published on `8000`, started with `python manage.py runserver 0.0.0.0:8000`.
- **`frontend`** - built from `./frontend` with `Dockerfile-develop`, `./frontend` bind mounted into the container, published on `8081` (container port `8080`).

Because `backend` and `frontend` bind mount the checkout, editing a file under `backend/` or `frontend/` changes what the running develop containers serve.

## Production stack

`docker-compose-production.yml` defines the same `postgres` and `elasticsearch` services (environment from `.env.production`, `elasticsearch` given more heap: `-Xms3g -Xmx12g`), plus:

- **`backend`** - built from `./backend`, started with `gunicorn pkdb_app.wsgi:application --log-config gunicorn_logging.conf -w 4 --timeout 900 --bind 0.0.0.0:8000`; also exposes container port `25`, published on `1025`, for outgoing mail.
- **`frontend`** - built from `./frontend` with `Dockerfile-production`; the container itself runs `tail -f /dev/null` (it only builds the static files into the `vue_dist` volume, `nginx` serves them).
- **`nginx`** - `nginx:1.19.2`, published on `8888` (container port `80`), configuration mounted from `nginx/config/conf.d`. It serves `django_static` at `/static`, `django_media` at `/media` and the built frontend (`vue_dist`) at `/`, and proxies `/api` and `/admin` to the `backend` service on its container port `8000`.

`postgres_data`, `elasticsearch_data`, `django_static`, `django_media`, `vue_dist` and `node_modules` are named docker volumes in both compose files, so their data survives a container restart; they are only removed by a script that explicitly asks for it (see below).

## Environment variables

Read from `backend/pkdb_app/settings.py`, the compose files and `.env.local`. Every example below is a placeholder, never a real credential. All are required unless marked optional.

`PKDB_DOCKER_COMPOSE_YAML`
:   Compose file the scripts below act on. Example: `docker-compose-develop.yml`.

`PKDB_DJANGO_CONFIGURATION`
:   Selects the `local` or `production` block in `settings.py`. Example: `local`.

`PKDB_API_BASE`
:   Base URL of the backend; combined with `/api/v1` for `API_URL`, and with `local` also used for the login and redirect URLs. Example: `http://localhost:8000`.

`PKDB_SECRET_KEY`
:   Django `SECRET_KEY`. Example: `change-me`.

`PKDB_ADMIN_PASSWORD`
:   Password of the admin superuser `docker-purge.sh` creates. Example: `change-me`.

`PKDB_DB_NAME`
:   Postgres database name. Example: `pkdb`.

`PKDB_DB_USER`
:   Postgres user. Example: `pkdb`.

`PKDB_DB_PASSWORD`
:   Postgres password. Example: `change-me`.

`PKDB_DB_SERVICE`
:   Postgres host as seen by the backend, the compose service name. Example: `postgres`.

`PKDB_DB_PORT`
:   Postgres port as seen by the backend, the container port (`5432`), not the published `5433`. Example: `5432`.

`PKDB_ELASTICSEARCH_HOST`
:   Optional. `host:port` of elasticsearch, defaults to `elasticsearch:9200` if unset. Example: `elasticsearch:9200`.

`PKDB_EMAIL_HOST_USER`
:   SMTP user, only read when `PKDB_DJANGO_CONFIGURATION` is `production`. Example: `change-me`.

`PKDB_EMAIL_HOST_PASSWORD`
:   SMTP password, only read when `PKDB_DJANGO_CONFIGURATION` is `production`. Example: `change-me`.

## Scripts

All scripts live in the repository root and require `PKDB_DOCKER_COMPOSE_YAML` (and, in practice, the rest of an env file) to already be exported.

### `backup.sh`

Requires `PKDB_DOCKER_COMPOSE_YAML`. Creates `/var/backups/pkdb/<date>/` and archives the `django_media`, `django_static`, `postgres_data`, `elasticsearch_data` and `vue_dist` volumes into it with `docker run --volumes-from ... tar`, then dumps the database with `pg_dump -Fc` into `pkdb.dump` in that directory. It is meant to be run from cron. It does not touch the running stack, only reads from it.

### `deploy.sh`

Pulls the latest `develop`, sources `.env.production`, runs `backup.sh`, then `docker-purge.sh` (see below - this rebuilds the stack and resets the database and search index), then pulls the `pkdb_data` repository next to this checkout and re-runs the upload of the info nodes and the studies. `deploy.sh` carries these known limitations, noted as `FIXME` in the script itself:

- no protection against merge conflicts on `git pull`
- not wired into a cronjob yet, it is run manually
- the output of a deployment is not logged
- errors of the study upload are not logged for a daily report

### `docker-purge.sh`

Destructive: deletes every migration file under `*/migrations/` except `__init__.py`, removes the `media/` and `static/` directories, then `docker compose down --volumes --rmi local`, which removes the containers, the locally built images **and the named volumes** - `postgres_data`, `elasticsearch_data`, `django_media`, `django_static`, `vue_dist` and `node_modules` are all deleted, i.e. the database and the search index are emptied. It also runs `docker system prune --force`, which removes dangling images, containers, networks and build cache beyond this project. It then rebuilds the images with `--no-cache`, runs `makemigrations`, `migrate` and `collectstatic`, creates an admin superuser from `PKDB_ADMIN_PASSWORD`, rebuilds the elasticsearch index, and starts the stack.

### `docker-update.sh`

Destructive to the frontend, not to the database: stops the stack, force-removes the containers and images of all five services and the `node_modules`/`vue_dist` volumes, prunes dangling docker resources, rebuilds the images with `--no-cache` and starts the stack. `postgres_data` and `elasticsearch_data` are not touched.

### `docker-down-up.sh`

`docker compose down && docker compose up --detach` - a restart of the stack. Neither images nor volumes are touched.

### `docker-interactive.sh`

Same restart as `docker-down-up.sh`, but `up` runs in the foreground instead of `--detach`, so the combined container logs stream to the console.

### `elastic-rebuild-index.sh`

`docker compose run --rm backend ./manage.py search_index --rebuild -f` - rebuilds the elasticsearch index for every model from the current postgres data. A commented line shows how to rebuild a single model with `--models`.

## nginx

The production `nginx` service reads its server block from `nginx/config/conf.d/local.conf`. It proxies `/api` and `/admin` to the `backend` service, serves `django_static` at `/static` and `django_media` at `/media`, and serves the built frontend (`vue_dist`) at `/` with a single-page-app fallback to `/index.html`.
