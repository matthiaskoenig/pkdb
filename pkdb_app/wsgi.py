"""
WSGI config for viral project.
It exposes the WSGI callable as a module-level variable named ``application``.
For more information on this file, see
https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/gunicorn/
"""
import os

# read .env information
import environ

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)
# reading .env file
environ.Env.read_env()

print("-"*80)
print(env)
print(env)
print(os.environ.items())
print("-"*80)


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pkdb_app.config")
os.environ.setdefault("DJANGO_CONFIGURATION", "Production")

from configurations.wsgi import get_wsgi_application  # noqa

application = get_wsgi_application()
