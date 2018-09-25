"""
Production django settings.
"""
import os
from .common import Common

# read .env information
import environ

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)
# reading .env file
environ.Env.read_env()


class Production(Common):
    DEBUG = False

    INSTALLED_APPS = Common.INSTALLED_APPS
    POSTGRES_PASSWORD = os.getenv("PKDB_POSTGRES_PASSWORD")

    # Postgres
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "pkdb",
            "USER": "pkdb_user",
            "HOST": "localhost",
            "PASSWORD": POSTGRES_PASSWORD,
            "PORT": 5432,
        }
    }

    # Site
    # https://docs.djangoproject.com/en/2.0/ref/settings/#allowed-hosts
    ALLOWED_HOSTS = ["*"]
    INSTALLED_APPS += ("gunicorn",)
