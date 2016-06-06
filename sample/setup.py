#!/usr/bin/env python
#

import setuptools

import sample


setuptools.setup(
    name='sample',
    description='Sample API',
    author='Dave Shawley',
    author_email='daveshawley@gmail.com',
    packages=['sample'],
    install_requires=['tornado>4,<5'],
    package_data={'': ['**/*.json']},
    include_package_data=True,
)
