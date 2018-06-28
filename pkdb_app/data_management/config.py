
import os
import sys

# setup django (add current path to sys.path)
BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))

if BASEPATH not in sys.path:
    sys.path.append(BASEPATH)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flutype_webapp.settings")

import django
django.setup()

DATABASEPATH = os.path.join(BASEPATH, "data")