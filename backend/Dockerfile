FROM python:3.6
ENV PYTHONUNBUFFERED 1

# Allows docker to cache installed dependencies between builds
RUN pip install pip setuptools --upgrade
COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Adds application code to the image
COPY . /code
WORKDIR /code

RUN pip install -e .

EXPOSE 8000
CMD newrelic-admin run-program gunicorn --bind 0.0.0.0:$PORT --access-logfile - pkdb_app.wsgi:application