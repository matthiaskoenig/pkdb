"""
Shared django settings.
"""
import os
from os.path import join

import dj_database_url
from distutils.util import strtobool

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ------------------------------------------------------------------------------------------------------------------
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET_KEY']

# SECURITY WARNING: keep the secret key used in production secret!
DEFAULT_PASSWORD = os.environ['DEFAULT_PASSWORD']

API_BASE = os.environ['API_BASE']
API_URL = API_BASE + "/api/v1"
# ------------------------------------------------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = (

    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',

    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
)

INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.sites",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Authentication
    'bootstrap3',  # optional module for making bootstrap forms easier

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.github',
    #'allauth.socialaccount.providers.google',

    # Third party apps
    "rest_framework",  # utilities for rest apis
    "rest_framework.authtoken",  # token authentication
    "django_filters",  # for filtering rest endpoints
    "rest_framework_swagger",
    "corsheaders",

    #Elastic Search
    # Django Elasticsearch integration
    'django_elasticsearch_dsl',

    # Django REST framework Elasticsearch integration (this package)
    'django_elasticsearch_dsl_drf',

    # Your apps
    "pkdb_app.users",
    "pkdb_app.studies",
    "pkdb_app.categorials",
    "pkdb_app.subjects",
    "pkdb_app.substances",
    "pkdb_app.interventions",
    "pkdb_app.outputs",
    "pkdb_app.comments",
)

SITE_ID = 1
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_MIN_LENGTH = 3
ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS = False


SOCIALACCOUNT_PROVIDERS = {
    'github': {
        'SCOPE': ['email'],
        'METHOD': 'oauth2',
    },
    # 'google':
    #     { 'SCOPE': ['profile', 'email'],
    #       'AUTH_PARAMS': {'access_type': 'online'}
    #     },

}

# https://docs.djangoproject.com/en/2.0/topics/http/middleware/
MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)

CORS_ORIGIN_ALLOW_ALL = True
# CORS_ORIGIN_WHITELIST = (
#     "0.0.0.0:8080",
#     "localhost:8080",
#     "frontend:8080",
# )
INTERNAL_IPS = ("172.18.0.1",)

ALLOWED_HOSTS = ["*"]
ROOT_URLCONF = "pkdb_app.urls"

WSGI_APPLICATION = "pkdb_app.wsgi.application"

# Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

ADMINS = (
    ("mkoenig", "konigmatt@googlemail.com"),
    ("janekg89", "janekg89@hotmail.de"),
)

# General
APPEND_SLASH = False
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"
# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False
USE_L10N = True
USE_TZ = True
LOGIN_REDIRECT_URL = "/"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/


STATIC_ROOT = '/static'
# STATIC_ROOT = os.path.normpath(join(BASE_DIR, "static"))
STATICFILES_DIRS = [join(BASE_DIR, "pkdb_app", "static")]
STATIC_URL = "/static/"
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

# Media files
MEDIA_ROOT = '/media/'  # join(BASE_DIR, "media")
MEDIA_URL = "/media/"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": STATICFILES_DIRS + [os.path.join(BASE_DIR, "pkdb_app", "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [

                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

# Custom user app
AUTH_USER_MODEL = "users.User"


# Password Validation
# https://docs.djangoproject.com/en/2.0/topics/auth/passwords/#module-django.contrib.auth.password_validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[%(server_time)s] %(message)s",
        },
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"
        },
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "filters": {"require_debug_true": {"()": "django.utils.log.RequireDebugTrue"}},
    "handlers": {
        "django.server": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "django.server",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "propagate": True},
        "django.server": {
            "handlers": ["django.server"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["mail_admins", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.db.backends": {"handlers": ["console"], "level": "INFO"},
    },
}

# Django Rest Framework
REST_FRAMEWORK = {
    #'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    "DEFAULT_PAGINATION_CLASS": "pkdb_app.pagination.CustomPagination",
    "PAGE_SIZE": int(os.getenv("DJANGO_PAGINATION_LIMIT", 20)),
    'PAGINATE_BY': 10,  # Default to 10
    'PAGINATE_BY_PARAM': 'page_size',  # Allow client to override, using `?page_size=xxx`.
    'MAX_PAGINATE_BY': 100,
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z",
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
}
LOGIN_URL = "rest_framework:login"
LOGOUT_URL = "rest_framework:logout"

SWAGGER_SETTINGS = {
    "LOGIN_URL": "rest_framework:login",
    "LOGOUT_URL": "rest_framework:logout",
    "USE_SESSION_AUTH": True,
    "DOC_EXPANSION": "list",
    "APIS_SORTER": "alpha",
    "SECURITY_DEFINITIONS": {"basic": {"type": "basic"}},
}

# Postgres
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ['DB_NAME'],
        "USER": os.environ['DB_USER'],
        "HOST": os.environ['DB_SERVICE'],
        "PASSWORD": os.environ['DB_PASSWORD'],
        "PORT": os.environ['DB_PORT'],
    }
}

DJANGO_CONFIGURATION = os.environ['DJANGO_CONFIGURATION']
# ------------------------------
# LOCAL
# ------------------------------
if DJANGO_CONFIGURATION == 'local':
    DEBUG = True
    LOGIN_URL = "http://172.30.10.11:8080/#/account"
    LOGIN_REDIRECT_URL = "http://172.30.10.11:8080/#/account"
    ACCOUNT_LOGOUT_REDIRECT_URL = "http://172.30.10.11:8080/#/account"

    # Mail
    EMAIL_HOST = "localhost"
    EMAIL_PORT = 1025
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

    # Elastic Search
    ELASTICSEARCH_DSL = {
        'default': {
            'hosts': 'elasticsearch:9200'
        },
    }

# -------------------------------------------------
# Production
# -------------------------------------------------
elif DJANGO_CONFIGURATION == 'production':
    DEBUG = False
    LOGIN_URL = "/#/account"
    LOGIN_REDIRECT_URL = "/#/account"
    ACCOUNT_LOGOUT_REDIRECT_URL = "/#/account"
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # Mail
    # Mail is sent using the SMTP host and port specified in the EMAIL_HOST and EMAIL_PORT settings.
    # The EMAIL_HOST_USER and EMAIL_HOST_PASSWORD settings, if set, are used to authenticate to the SMTP server,
    # and the EMAIL_USE_TLS and EMAIL_USE_SSL settings control whether a secure connection is used.
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    SERVER_EMAIL = "mail@pk-db.com"
    DEFAULT_FROM_EMAIL = 'pk-db.com <mail@pk-db.com>'
    EMAIL_HOST = "mailhost.cms.hu-berlin.de"
    EMAIL_PORT = 25
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.environ['EMAIL_HOST_USER']
    EMAIL_HOST_PASSWORD = os.environ['EMAIL_HOST_PASSWORD']

    if not EMAIL_HOST_USER:
        raise ValueError("EMAIL_HOST_USER could not be read, export the 'EMAIL_HOST_USER' environment variable.")
    if not EMAIL_HOST_PASSWORD:
        raise ValueError("EMAIL_HOST_PASSWORD could not be read, export the 'EMAIL_HOST_PASSWORD' environment variable.")

    # Elastic Search
    ELASTICSEARCH_DSL = {
        'default': {
            'hosts': 'localhost:9200'
        },
    }

    from django.core.mail import send_mail
    send_mail('Test mail production',
              'Here is the message.',
              'from@example.com',
              ['konigmatt@googlemail.com'],
              fail_silently=False)

    # Site
    # https://docs.djangoproject.com/en/2.0/ref/settings/#allowed-hosts
    INSTALLED_APPS += ("gunicorn",)
else:
    raise ValueError(f"Unsupported DJANGO_CONFIGURATION: {DJANGO_CONFIGURATION}")
