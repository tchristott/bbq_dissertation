# -*- coding: utf-8 -*-

# Learn more: https://github.com/tchristott/bbq2/setup.py

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='BBQ2',
    version='0.1.0',
    description='Data analysis package for biophysical and biochemical assays',
    long_description=readme,
    author='Thomas Christott',
    author_email='thomas.christott@cmd.ox.ac.uk',
    url='https://github.com/tchristott/bbq2',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)