FROM python:3.9-slim

# install uv
COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /bin/uv
ENV UV_SYSTEM_PYTHON=1

# install git
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# copy code
WORKDIR /code
COPY . /code

# install package
RUN uv pip install -e .

EXPOSE 8000
CMD gunicorn --bind 0.0.0.0:$PORT --access-logfile - pkdb_app.wsgi:application
