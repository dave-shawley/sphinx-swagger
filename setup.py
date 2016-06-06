#!/usr/bin/env python

import os.path

import setuptools

import sphinxswagger


def read_requirements(name):
    requirements = []
    with open(os.path.join('requires', name)) as req_file:
        for line in req_file:
            if '#' in line:
                line = line[:line.index('#')]
            line = line.strip()
            if line.startswith('-r'):
                requirements.extend(read_requirements(line[2:].strip()))
            elif line and not line.startswith('-'):
                requirements.append(line)
    return requirements


setuptools.setup(
    name='sphinx-swagger',
    version=sphinxswagger.__version__,
    url='https://github.com/dave-shawley/sphinx-swagger',
    description='Generate swagger definitions from sphinx docs',
    long_description='\n'+open('README.rst').read(),
    author='Dave Shawley',
    author_email='daveshawley+python@gmail.com',
    packages=['sphinxswagger'],
    install_requires=read_requirements('installation.txt'),
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Framework :: Sphinx :: Extension',
    ],
)
