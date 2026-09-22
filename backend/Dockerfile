# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.14
FROM python:3.14-slim-bookworm@sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56 AS python-3.14
FROM ghcr.io/astral-sh/uv:0.12.5@sha256:e85be844203885286c60ffad8a858d48afb6c5a5c237ca0e67f12e74b8f174b1 AS uv
FROM python-${PYTHON_VERSION} AS base

FROM base AS build
COPY --from=uv /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_PYTHON=/usr/local/bin/python UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv uv build --wheel && uv pip install --python /opt/venv/bin/python --no-deps dist/*.whl

FROM base AS runtime
ENV PATH=/opt/venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PKDB_FILE_ROOT=/data/files
RUN groupadd --gid 10001 pkdb && useradd --uid 10001 --gid pkdb --create-home pkdb && mkdir -p /app /data/files && chown pkdb:pkdb /app /data/files
COPY --from=build /opt/venv /opt/venv
WORKDIR /app
COPY alembic.ini ./
COPY alembic ./alembic
COPY bootstrap ./bootstrap
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3)"
CMD ["uvicorn", "pkdb.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
