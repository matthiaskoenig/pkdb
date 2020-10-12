#!/usr/bin/env python
"""
pkdb_app pip package
"""
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


# parse requirements.txt
required = []

with open('requirements.txt') as f:
    lines = f.read().splitlines()
    for item in lines:
        if item.startswith('#'):
            continue
        elif item.startswith('-e'):
            continue
        else:
            required.append(item)

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
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Cython',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Bio-Informatics'
    ],
    keywords='pharmacokinetics data',
    packages=find_packages(),
    package_data={
        '': ['requirements.txt'],
    },
    include_package_data=True,
    python_requires='>=3.7, <3.8',
    zip_safe=False,
    install_requires=required,
    extras_require={},
    **setup_kwargs)
