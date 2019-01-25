FROM python:3.6
ENV PYTHONUNBUFFERED 1

# Allows docker to cache installed dependencies between builds
COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Adds application code to the image
COPY . /usr/src/app
WORKDIR /usr/src/app
# install pkdb_app
RUN pip install -e .

EXPOSE 8000
