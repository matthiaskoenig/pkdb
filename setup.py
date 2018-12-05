#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
sbmlutils pip package
"""
from __future__ import absolute_import, print_function

import io
import re
import os
from setuptools import find_packages
from setuptools import setup

setup_kwargs = {}


def read(*names, **kwargs):
    """ Read file info in correct encoding. """
    return io.open(
        os.path.join(os.path.dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8')
    ).read()


# version from file
verstrline = read('pkdb_app/_version.py')
mo = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", verstrline, re.M)
if mo:
    verstr = mo.group(1)
    setup_kwargs['version'] = verstr
else:
    raise RuntimeError("Unable to find version string")

# description from markdown
long_description = read('README.md')
setup_kwargs['long_description'] = long_description

setup(
    name='pkdb_app',
    description='PK-DB backend',
    url='https://github.com/matthiaskoenig/pkdb',
    author='Jan Grzegorzewski and Matthias König',
    author_email='konigmatt@googlemail.com',
    license='LGPLv3',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Cython',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Bio-Informatics'
    ],
    keywords='pharmacokinetics data',
    packages=find_packages(),
    # package_dir={'': ''},
    package_data={
      '': ['requirements.txt'],
    },
    include_package_data=True,
    zip_safe=False,
    # List run-time dependencies here.  These will be installed by pip when
    install_requires=[
        "pip>=18.1",

        # Core
        "pytz==2018.4",
        "Django==2.1.4",
        "gunicorn==19.8.1",
        "newrelic==3.2.2.94",

        # For the persistence stores
        "psycopg2-binary==2.7.4",
        "dj-database-url==0.5.0",

        # Model Tools
        "django-model-utils==3.1.2",
        "django_unique_upload==0.2.1",
        "django-environ>=0.4.5",
        "django-allauth>=0.37.1",
        "django-bootstrap3>=11.0.0",

        # Rest API
        "djangorestframework==3.8.2",
        "Markdown==2.6.11",
        "django-filter==2.0",
        "django-rest-swagger>=2.2.0",
        "django-cors-headers==2.4.0",
        "coreapi>=2.3.3",

        # Developer Tools
        "ipdb==0.11",
        "ipython==6.4.0",
        "mkdocs==0.17.4",
        "flake8==3.5.0",

        # Testing
        "mock==2.0.0",
        "factory-boy==2.11.1",
        "django-nose==1.4.5",
        "nose-progressive==1.5.1",
        "coverage==4.5.1",
        "pytest-django",
        
        # Static and Media Storage
        "django-storages==1.6.6",
        "boto3==1.7.39",

        "biopython>=1.72",
        "ipykernel>=5.0.0",
        "pandas>=0.23.4",
        "numpy>=1.15.4",
        "scipy>=1.1.0",
        "matplotlib>=3.0.2",

        "jsonschema>=2.6.0",
        "django-extra-fields>=1.0.0",
        "PyPDF2>=1.26.0",
        "watchdog>=0.9.0",
        "requests>=2.19.1",
        "coloredlogs>=10.0",
    ],
    extras_require={},
    **setup_kwargs)
