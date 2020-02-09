#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import os
import sys
from setuptools import setup

HERE = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(HERE, 'stencila'))
from pyla import __version__

with io.open(os.path.join(HERE, 'README.md'), encoding='utf-8') as f:
    long_description = '\n' + f.read()

setup(
    name='stencila-pyla',
    description='Python interpreter for Stencila',
    version=__version__,
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Stencila and contributors',
    author_email='hello@stenci.la',
    python_requires='>=3.6.0',
    url='https://github.com/stencila/pyla',
    packages=['stencila.pyla'],
    install_requires=[
        'astor==0.8.0',
        'stencila-schema==0.37.2'
    ],
    extras_require={},
    include_package_data=True,
    license='Apache-2.0',
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ]
)
