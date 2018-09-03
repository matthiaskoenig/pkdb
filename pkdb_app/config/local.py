"""
Local django settings.
"""
import os
from .common import Common

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import dj_database_url

POSTGRES_PASSWORD = os.getenv("PKDB_POSTGRES_PASSWORD")


class Local(Common):
    DEBUG = True

    # Testing
    INSTALLED_APPS = Common.INSTALLED_APPS
    INSTALLED_APPS += ("django_nose",)
    TEST_RUNNER = "django_nose.NoseTestSuiteRunner"
    NOSE_ARGS = [
        BASE_DIR,
        "-s",
        "--nologcapture",
        "--with-coverage",
        "--with-progressive",
        "--cover-package=pkdb",
    ]

    # Postgres
    DATABASES = {
        "default": dj_database_url.config(
            # postgres://USER:PASSWORD@HOST:PORT/NAME
            default=f"postgres://postgres:pass@postgres:5432/postgres",
            conn_max_age=int(os.getenv("POSTGRES_CONN_MAX_AGE", 600)),
        )
    }
    """
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'pkdb',
            'USER': 'pkdb_user',
            'HOST': 'localhost',
            'PASSWORD': POSTGRES_PASSWORD,
            'PORT': 5432,
        }
    }
    """

    # Mail
    EMAIL_HOST = "localhost"
    EMAIL_PORT = 1025
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
